from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
from app.thread_store import ThreadStore
from app.agent import Agent
from app.generator import Generator
from app.chroma_client import ChromaClient
from app.schemas import UserMessageRequest, ThreadName, DocumentId
from app.utils.helpers import safe_json
import json

def get_thread_router(llm_client, embed_client, chroma_client, thread_store, agent):
    router = APIRouter()

    # Use provided dependencies
    _llm_client = llm_client
    _chroma_client = chroma_client
    _thread_store = thread_store
    _agent = agent

    @router.get("/")
    def get_threads():
        return safe_json(_thread_store.get_all_threads())

    @router.post("/")
    def create_thread(name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        thread = _thread_store.create_thread(name, metadata)
        return safe_json(thread.dict())

    @router.get("/{thread_id}")
    def get_thread_endpoint(thread_id: str):
        thread = _thread_store.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return safe_json(thread.dict())

    @router.get("/{thread_id}/details")
    def get_thread_details(thread_id: str):
        thread = _thread_store.get_thread_details(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return safe_json(thread.dict())

    @router.put("/{thread_id}/metadata")
    async def update_thread_metadata(thread_id: str, metadata: Dict[str, Any]):
        try:
            _thread_store.update_metadata(thread_id, metadata)
            return safe_json({"status": "success"})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.put("/{thread_id}/rename")
    def rename_thread(thread_id: str, new_name: ThreadName):
        try:
            _thread_store.rename_thread(thread_id, new_name.name)
            return safe_json({"status": "success"})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/{thread_id}/chat")
    async def chat_in_thread(thread_id: str, message: UserMessageRequest):
        if message.use_db_explorer:
            stream_func = _agent.query_with_db_explorer
        else:
            stream_func = _agent.user_query
        try:
            def stream_generator():
                for chunk in stream_func(message.content, thread_id):
                    # Log the chunk before sending it
                    print(f"Sending chunk: {chunk}")
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk}, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/{thread_id}/documents")
    async def add_document_to_thread_endpoint(thread_id: str, doc: DocumentId):
        try:
            _thread_store.add_document_to_thread(thread_id, doc.document_id)
            return safe_json({"status": "success"})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete("/{thread_id}/documents/{document_id}")
    async def remove_document_from_thread_endpoint(thread_id: str, document_id: str):
        try:
            _thread_store.remove_document_from_thread(thread_id, document_id)
            return safe_json({"status": "success"})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete("/{thread_id}/messages/{message_index}")
    async def delete_message_from_thread(thread_id: str, message_index: int):
        try:
            _thread_store.delete_message(thread_id, message_index)
            return safe_json({"status": "success"})
        except (ValueError, IndexError) as e:
            raise HTTPException(status_code=404, detail=str(e))

    return router