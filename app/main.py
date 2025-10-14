import os
import uuid
import hashlib
from dotenv import load_dotenv

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, AsyncIterable
import json
import asyncio

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.agent import Agent
from app.chroma_client import ChromaClient
from app.generator import Generator
from app.embedding_client import EmbeddingClient
from app.schemas import *
from app.thread_store import ThreadStore
from app.server_launcher import ServerLauncher
from app.settings_store import SettingsStore

load_dotenv(override=True)


STORAGE_RAW_DIR = os.getenv("STORAGE_RAW_DIR", "./storage/raw")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma")
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
os.makedirs("./storage/threads", exist_ok=True)
os.makedirs("./storage/dev", exist_ok=True)
os.makedirs(STORAGE_RAW_DIR, exist_ok=True)
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
LAUNCH_CONFIG_DIR = "./app/launch_configs"


app = FastAPI(title="RAGgie BOY", version="0.0.1")

server_launcher = ServerLauncher()
model_status = "ready"

@app.get("/api/status")
async def get_status():
    return safe_json({"status": model_status})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = Generator(LLAMACPP_CHAT_BASE)
embed_client = EmbeddingClient(LLAMACPP_EMBED_BASE)
chroma_client = ChromaClient(embed_client, CHROMA_PERSIST_DIR)
thread_store = ThreadStore()
settings_store = SettingsStore()
initial_settings = settings_store.get_settings()
agent = Agent(llm_client, chroma_client, thread_store, language=initial_settings.get("language", "Russian"))



@app.get("/api/servers/configs")
def get_server_configs():
    return safe_json(server_launcher.get_available_configs())

@app.post("/api/servers/start")
def start_servers(req: ServerStartRequest):
    server_launcher.start_server(req.server_type, req.config_name)
    return safe_json({"status": "success", "message": f"{req.server_type} server started."})

@app.post("/api/servers/stop")
def stop_servers(req: ServerStopRequest):
    server_launcher.stop_server(req.server_type)
    return safe_json({"status": "success", "message": f"{req.server_type} server stopped."})

@app.post("/api/servers/update_config")
def update_server_config(req: ServerUpdateConfig):
    server_launcher.update_config(req.server_type, req.config_name, req.config_index)
    return safe_json({"status": "success", "message": f"{req.server_type} server config updated and restarted."})

@app.get("/api/servers/status")
def get_server_status():
    return safe_json(server_launcher.get_server_status())

@app.get("/api/servers/active_configs")
def get_active_configs():
    return safe_json(server_launcher.get_active_configs())

@app.get("/api/chat_model")
def get_chat_model_handler():
    return safe_json(llm_client.get_model_info())

@app.get("/api/embedding_model")
def get_embedding_model_handler():
    return safe_json({"model": embed_client._get_model_from_server()})

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
        filename = up.filename or f"file_{uuid.uuid4()}"
        existing_doc = chroma_client.get_document_by_name(filename)
        
        temp_path = os.path.join(STORAGE_RAW_DIR, f"temp_{uuid.uuid4()}")
        with open(temp_path, "wb") as f:
            content = await up.read()
            f.write(content)

        if existing_doc:
            ext = os.path.splitext(existing_doc["name"])[1].lower().lstrip(".")
            existing_raw_path = os.path.join(STORAGE_RAW_DIR, f"{existing_doc['id']}.{ext}")
            
            with open(existing_raw_path, "rb") as f:
                existing_content = f.read()

            if hashlib.sha256(content).hexdigest() == hashlib.sha256(existing_content).hexdigest():
                os.remove(temp_path)
                continue  # Skip to the next file

            chroma_client.delete_document(existing_doc["id"])
            os.remove(existing_raw_path)

        doc_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        raw_path = os.path.join(STORAGE_RAW_DIR, f"{doc_id}.{ext}")
        os.rename(temp_path, raw_path)
        
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
                "metadata": ({"error": err} if err else None),
            }
            created.append({
                **{k: meta[k] for k in ["id","name","type","size","uploadedAt","status","chunks"]},
                "content": None,
                "metadata": meta["metadata"],
            })

        try:
            chunk_count = chroma_client.ingest_file(
                doc_id, raw_path, filename, up.content_type or f"application/{ext}", uploaded_at, CHUNK_SIZE, CHUNK_OVERLAP
            )
            _finish("completed", chunk_count, None)

        except Exception as e:
            _finish("error", 0, f"fatal: {e}")

    return safe_json(created)

@app.get("/api/documents", response_model=List[Document])
def get_documents():
    """
    Retrieves a list of all available documents.
    """
    documents = chroma_client.get_all_documents()
    return safe_json(documents)

@app.get("/api/documents/{doc_id}", response_model=DocumentMetadata)
def get_document(doc_id: str):
    """
    Retrieves a single document by its ID.
    """
    document = chroma_client.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return safe_json(document)

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    """
    Deletes a document by its ID.
    """
    document = chroma_client.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Construct the path to the raw file and delete it
    try:
        ext = os.path.splitext(document["name"])[1].lower().lstrip(".")
        raw_path = os.path.join(STORAGE_RAW_DIR, f"{doc_id}.{ext}")
        if os.path.exists(raw_path):
            os.remove(raw_path)
    except Exception as e:
        # Log the error but proceed to delete from Chroma
        print(f"Error deleting raw file {raw_path}: {e}")

    # Delete from ChromaDB
    chroma_client.delete_document(doc_id)
    
    return safe_json({"status": "success", "message": f"Document {doc_id} deleted."})

@app.post("/api/query/chunks", response_model=List[ChunkQueryResult])
def query_chunks(query: ChunkQuery):
    """
    Retrieves n chunks based on a text query.
    """
    results = chroma_client.search_chunks(query.text, query.top_k)
    return safe_json(results)

# =========================
# THREADS
# =========================

@app.get("/api/threads")
def get_threads():
    return safe_json(thread_store.get_all_threads())

@app.post("/api/threads")
def create_thread(name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    thread = thread_store.create_thread(name, metadata)
    return safe_json(thread.dict())

@app.get("/api/threads/{thread_id}")
def get_thread(thread_id: str):
    thread = thread_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return safe_json(thread.dict())

@app.get("/api/threads/{thread_id}/details")
def get_thread_details(thread_id: str):
    thread = thread_store.get_thread_details(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return safe_json(thread.dict())

@app.put("/api/threads/{thread_id}/metadata")
async def update_thread_metadata(thread_id: str, metadata: Dict[str, Any]):
    try:
        thread_store.update_metadata(thread_id, metadata)
        return safe_json({"status": "success"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.put("/api/threads/{thread_id}/rename")
def rename_thread(thread_id: str, new_name: ThreadName):
    try:
        thread_store.rename_thread(thread_id, new_name.name)
        return safe_json({"status": "success"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/threads/{thread_id}/chat")
async def chat_in_thread(thread_id: str, message: UserMessageRequest):
    if message.use_db_explorer:
        stream_func = agent.query_with_db_explorer
    else:
        stream_func = agent.user_query
    try:
        def stream_generator():
            for chunk in stream_func(message.content, thread_id):
                # Log the chunk before sending it
                print(f"Sending chunk: {chunk}")
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/threads/{thread_id}/documents")
async def add_document_to_thread_endpoint(thread_id: str, doc: DocumentId):
    try:
        thread_store.add_document_to_thread(thread_id, doc.document_id)
        return safe_json({"status": "success"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/threads/{thread_id}/documents/{document_id}")
async def remove_document_from_thread_endpoint(thread_id: str, document_id: str):
    try:
        thread_store.remove_document_from_thread(thread_id, document_id)
        return safe_json({"status": "success"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/threads/{thread_id}/messages/{message_index}")
async def delete_message_from_thread(thread_id: str, message_index: int):
    try:
        thread_store.delete_message(thread_id, message_index)
        return safe_json({"status": "success"})
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=404, detail=str(e))


# =========================
# SETTINGS
# =========================

@app.get("/api/settings")
def get_settings():
    """
    Provides a consolidated endpoint for all settings.
    """
    stored_settings = settings_store.get_settings()
    settings = {
        "chat_model": {"model": llm_client._get_model_from_server()},
        "embedding_model": {"model": embed_client._get_model_from_server()},
        "server_configs": server_launcher.get_available_configs(),
        "active_configs": server_launcher.get_active_configs(),
        "launch_configs": [f for f in os.listdir(LAUNCH_CONFIG_DIR) if f.endswith('.json')],
        "language": stored_settings.get("language", "Russian")
    }
    return safe_json(settings)

@app.get("/api/server_urls")
def get_server_urls():
    """
    Provides the base URLs for the chat and embedding servers.
    """
    return safe_json({
        "chat_base_url": agent.generator._backend_type,
        "embed_base_url": LLAMACPP_EMBED_BASE
    })

@app.put("/api/settings")
def update_settings(settings: Dict[str, Any]):
    current_settings = settings_store.get_settings()
    if "language" in settings:
        agent.language = settings["language"]
    current_settings.update(settings)
    settings_store.save_settings(current_settings)
    return safe_json({"status": "success", "settings": current_settings})

@app.get("/api/launch_configs")
def get_launch_configs():
    configs = [f for f in os.listdir(LAUNCH_CONFIG_DIR) if f.endswith('.json')]
    return safe_json(configs)

@app.get("/api/launch_configs/{config_name}")
def get_launch_config(config_name: str):
    config_path = os.path.join(LAUNCH_CONFIG_DIR, config_name)
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Config not found")
    with open(config_path, 'r') as f:
        return safe_json(json.load(f))

@app.post("/api/launch_configs/{config_name}")
async def update_launch_config(config_name: str, config: Dict[str, Any]):
    config_path = os.path.join(LAUNCH_CONFIG_DIR, config_name)
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Config not found")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    return safe_json({"status": "success", "message": f"Config {config_name} updated."})


# =========================
# UTILS
# =========================
def safe_json(payload: Any, status_code: int = 200) -> Response:
    """
    Возвращает строго валидный JSON (без NaN/Infinity), чтобы jq и строгие клиенты не падали.
    """
    return Response(
        content=json.dumps(payload, ensure_ascii=False, allow_nan=False, default=str),
        media_type="application/json",
        status_code=status_code,
    )
