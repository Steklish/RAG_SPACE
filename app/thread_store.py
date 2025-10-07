import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.schemas import Thread

class ThreadStore:
    def __init__(self, storage_path: str = "storage/threads"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path, exist_ok=True)

    def _get_thread_path(self, thread_id: str) -> str:
        return os.path.join(self.storage_path, f"{thread_id}.json")

    def create_thread(self, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Thread:
        thread_id = str(uuid.uuid4())
        if name is None:
            name = f"Thread {thread_id[:8]}"
        
        thread = Thread(
            id=thread_id,
            name=name,
            created_at=datetime.utcnow(),
            history=[],
            metadata=metadata or {}, 
            document_ids=[]
        )
        self.save_thread(thread)
        return thread

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        thread_path = self._get_thread_path(thread_id)
        if not os.path.exists(thread_path):
            return None
        
        with open(thread_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Thread.parse_obj(data)

    def get_thread_details(self, thread_id: str) -> Optional[Thread]:
        return self.get_thread(thread_id)

    def save_thread(self, thread: Thread):
        thread_path = self._get_thread_path(thread.id)
        with open(thread_path, 'w', encoding='utf-8') as f:
            json.dump(thread.model_dump(), f, indent=2, default=str, ensure_ascii=False)

    def update_metadata(self, thread_id: str, metadata: Dict[str, Any]):
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread with id {thread_id} not found.")
            
        thread.metadata.update(metadata)
        self.save_thread(thread)

    def rename_thread(self, thread_id: str, new_name: str):
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread with id {thread_id} not found.")
        
        thread.name = new_name
        self.save_thread(thread)

    def get_all_threads(self) -> List[Dict[str, Any]]:
        threads = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                thread_id = filename[:-5]
                thread_data = self.get_thread(thread_id)
                if thread_data:
                    threads.append({
                        "id": thread_data.id,
                        "name": thread_data.name,
                        "created_at": thread_data.created_at.isoformat(),
                        "message_count": len(thread_data.history),
                        "document_count": len(thread_data.document_ids),
                        "metadata": thread_data.metadata
                    })
        # Sort threads by creation date, newest first
        threads.sort(key=lambda x: x.get("created_at"), reverse=True)
        return threads
    def add_document_to_thread(self, thread_id: str, document_id: str):
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread with id {thread_id} not found.")
        
        if document_id not in thread.document_ids:
            thread.document_ids.append(document_id)
            self.save_thread(thread)

    def remove_document_from_thread(self, thread_id: str, document_id: str):
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread with id {thread_id} not found.")
        
        if document_id in thread.document_ids:
            thread.document_ids.remove(document_id)
            self.save_thread(thread)

    def delete_message(self, thread_id: str, message_index: int):
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread with id {thread_id} not found.")
        
        if 0 <= message_index < len(thread.history):
            thread.history.pop(message_index)
            self.save_thread(thread)
        else:
            raise IndexError("Message index out of range.")
