from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Any, Dict
from app.chroma_client import ChromaClient
from app.embedding_client import EmbeddingClient
from app.schemas import ChunkQuery, ChunkQueryResult, Document
from app.utils.helpers import safe_json
from app.main import STORAGE_RAW_DIR, CHROMA_PERSIST_DIR

def get_document_router(llm_client, embed_client, chroma_client, thread_store, agent):
    router = APIRouter()
    
    # Set up dependencies
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
    
    # Use provided dependencies
    _embed_client = embed_client
    _chroma_client = chroma_client

    @router.post("/", response_model=List[Document])
    async def upload_documents(files: List[UploadFile] = File(...)):
        created: List[Dict[str, Any]] = []

        for up in files:
            filename = up.filename or f"file_{uuid.uuid4()}"
            existing_doc = _chroma_client.get_document_by_name(filename)
            
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

                _chroma_client.delete_document(existing_doc["id"])
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
                chunk_count = _chroma_client.ingest_file(
                    doc_id, raw_path, filename, up.content_type or f"application/{ext}", uploaded_at, CHUNK_SIZE, CHUNK_OVERLAP
                )
                _finish("completed", chunk_count, None)

            except Exception as e:
                _finish("error", 0, f"fatal: {e}")

        return safe_json(created)

    @router.get("/", response_model=List[Document])
    def get_documents():
        """
        Retrieves a list of all available documents.
        """
        documents = _chroma_client.get_all_documents()
        return safe_json(documents)

    @router.get("/{doc_id}", response_model=Document)
    def get_document(doc_id: str):
        """
        Retrieves a single document by its ID.
        """
        document = _chroma_client.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return safe_json(document)

    @router.delete("/{doc_id}")
    def delete_document(doc_id: str):
        """
        Deletes a document by its ID.
        """
        document = _chroma_client.get_document(doc_id)
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
        _chroma_client.delete_document(doc_id)
        
        return safe_json({"status": "success", "message": f"Document {doc_id} deleted."})

    @router.post("/chunks", response_model=List[ChunkQueryResult])
    def query_chunks(query: ChunkQuery):
        """
        Retrieves n chunks based on a text query.
        """
        results = _chroma_client.search_chunks(query.text, query.top_k)
        return safe_json(results)

    return router