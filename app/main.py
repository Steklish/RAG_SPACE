import os
import uuid
from dotenv import load_dotenv

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, AsyncIterable
import json
import asyncio

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.chroma_client import ChromaClient
from app.local_generator import LocalGenerator
from app.embedding_client import EmbeddingClient
from app.schemas import *
from app.ingest import extract_text_from_file, normalize_text, chunk_text

load_dotenv(override=True)


STORAGE_RAW_DIR = os.getenv("STORAGE_RAW_DIR", "./storage/raw")
STORAGE_TEXT_DIR = os.getenv("STORAGE_TEXT_DIR", "./storage/text")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma")
DOCS_INDEX_PATH = "./storage/docs_index.jsonl"
MODELS_FOLDER = "./models"

# Чанкинг/ретрив
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
DEFAULT_TOP_K = int(os.getenv("TOP_K", "4"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

# llama.cpp base urls
LLAMACPP_CHAT_BASE = os.getenv("LLAMACPP_CHAT_BASE", "http://127.0.0.1:11434").replace("localhost", "127.0.0.1")
LLAMACPP_EMBED_BASE = os.getenv("LLAMACPP_EMBED_BASE", "http://127.0.0.1:11435").replace("localhost", "127.0.0.1")

LLAMACPP_TIMEOUT_S = float(os.getenv("LLAMACPP_TIMEOUT_S", "300"))
LLAMACPP_MAX_RETRIES = int(os.getenv("LLAMACPP_MAX_RETRIES", "3"))

# Директории
os.makedirs("./storage", exist_ok=True)
os.makedirs(STORAGE_RAW_DIR, exist_ok=True)
os.makedirs(STORAGE_TEXT_DIR, exist_ok=True)
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)


app = FastAPI(title="RAGgie BOY", version="0.0.1")

llm_client = LocalGenerator(LLAMACPP_CHAT_BASE)
embed_client = EmbeddingClient(LLAMACPP_EMBED_BASE)
chroma_client = ChromaClient(CHROMA_PERSIST_DIR)


@app.get("/api/get_loaded_models")
def get_loaded_models():
    """
    This endpoint returns a list of all files in the `MODELS_FOLDER`.
    """
    try:
        # Check if the directory exists
        if not os.path.isdir(MODELS_FOLDER):
            # Assuming safe_json can handle error responses as well.
            return safe_json({"error": "Models directory not found"}), 404

        # Get all entries in the directory and filter for files
        files = [f for f in os.listdir(MODELS_FOLDER) if os.path.isfile(os.path.join(MODELS_FOLDER, f))]
        return safe_json({"models": files})
    except Exception as e:
        return safe_json({"error": str(e)}), 500

@app.get("/api/chat_model_info")
def get_chat_model():
    return safe_json(
        {"model" : llm_client.get_model_info}
    )
    
@app.get("/api/embed_model_info")
def get_embed_model():
    return safe_json(
        {"model" : embed_client._get_model_from_server}
    )
    



@app.post("/api/documents", response_model=List[Document])
async def upload_documents(files: List[UploadFile] = File(...)):
    created: List[Dict[str, Any]] = []

    for up in files:
        # создаём все пути и времена заранее — чтобы даже при ошибке сохранить запись в индексе
        doc_id = str(uuid.uuid4())
        filename = up.filename or f"file_{doc_id}"
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        raw_path = os.path.join(STORAGE_RAW_DIR, f"{doc_id}.{ext}")
        txt_path = os.path.join(STORAGE_TEXT_DIR, f"{doc_id}.txt")
        uploaded_at = datetime.utcnow().isoformat()

        def _finish(status: str, chunks: int, err: str | None = None):
            meta = {
                "id": doc_id,
                "name": filename,
                "type": up.content_type or f"application/{ext}",
                "size": os.path.getsize(raw_path) if os.path.exists(raw_path) else 0,
                "uploadedAt": uploaded_at,
                "status": status,
                "chunks": int(chunks),
                "content_path": txt_path if os.path.exists(txt_path) else None,
                "metadata": ({"error": err} if err else None),
            }
            created.append({
                **{k: meta[k] for k in ["id","name","type","size","uploadedAt","status","chunks"]},
                "content": None,
                "metadata": meta["metadata"],
            })

        try:
            # 1) потоковая запись RAW (по 1 МБ, без загрузки в память)
            with open(raw_path, "wb") as f:
                while True:
                    chunk = await up.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

            # 2) извлечение и нормализация текста
            try:
                text = extract_text_from_file(raw_path, up.content_type)
                text = normalize_text(text)
            except Exception as e:
                _finish("error", 0, f"extract_text: {e}")
                continue

            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception as e:
                _finish("error", 0, f"write_txt: {e}")
                continue

            # 3) чанкинг (на предложения + окна)
            try:
                chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            except Exception as e:
                _finish("error", 0, f"chunk_text: {e}")
                continue

            if not chunks:
                _finish("error", 0, "no_chunks_after_ingest")
                continue

            # 4) эмбеддинг (внутри embed_texts — адаптивный батч + усечение по EMBED_MAX_CHARS)
            try:
                embeddings = embed_client.embed_texts(chunks)
                if not embeddings or len(embeddings) != len(chunks):
                    raise ValueError(f"embeddings_mismatch: chunks={len(chunks)} != embeddings={len(embeddings) if embeddings else 0}")
            except Exception as e:
                _finish("error", 0, f"embed_texts: {e}")
                continue

            # 5) запись в Chroma
            metadoc = {
                "doc_id": doc_id,
                "name": filename,
                "type": up.content_type or f"application/{ext}",
                "size": os.path.getsize(raw_path),
                "uploadedAt": uploaded_at,
            }
            try:
                chroma_client.store_chunks(chunks, embeddings, [metadoc]*len(chunks))
            except Exception as e:
                _finish("error", 0, f"chroma_upsert: {e}")
                continue

            # 6) успех
            _finish("completed", len(chunks), None)

        except Exception as e:
            _finish("error", 0, f"fatal: {e}")

    return safe_json(created)



# =========================
# UTILS
# =========================
def safe_json(payload: Any, status_code: int = 200) -> Response:
    """
    Возвращает строго валидный JSON (без NaN/Infinity), чтобы jq и строгие клиенты не падали.
    """
    return Response(
        content=json.dumps(payload, ensure_ascii=False, allow_nan=False),
        media_type="application/json",
        status_code=status_code,
    )
