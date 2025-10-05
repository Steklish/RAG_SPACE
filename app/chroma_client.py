import os
import uuid
import chromadb
from chromadb.api.types import QueryResult
from typing import List, Dict, Any, Optional, Sequence

class ChromaClient:
    def __init__(self, path: str = os.getenv("CHROMA_PERSIST_DIR", "chroma_db"), collection_name: str = "rag_collection"):
        """
        Initializes the ChromaClient for persistent storage.

        :param path: The directory path for ChromaDB's persistent storage.
        :param collection_name: The name of the collection to use.
        """
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def store_chunks(self, chunks: List[str], embeddings: Sequence[List[float]], metadatas: Sequence[Dict[str, Any]]) -> List[str]:
        """
        Stores chunked data, embeddings, and metadata in ChromaDB using unique IDs.

        :param chunks: A list of text chunks.
        :param embeddings: A list of embeddings corresponding to the chunks.
        :param metadatas: A list of metadata dictionaries for each chunk.
        :return: A list of the generated unique IDs for the stored chunks.
        """
        ids = [str(uuid.uuid4()) for _ in chunks]
        self.collection.add(
            embeddings=embeddings, # type: ignore
            documents=chunks,
            metadatas=metadatas, # type: ignore
            ids=ids
        )
        return ids

    def search(self, query_embedding: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Performs a similarity search in ChromaDB with optional filtering.

        :param query_embedding: The embedding of the query text.
        :param top_k: The number of top results to retrieve.
        :param filters: A dictionary of metadata filters to apply.
        :return: A list of search results.
        """
        if filters:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        return results

    def delete_collection(self):
        """Deletes the entire collection."""
        self.client.delete_collection(name=self.collection.name)

    def get_collection_count(self) -> int:
        """
        Returns the number of items in the collection.

        :return: The number of items in the collection.
        """
        return self.collection.count()

    def update_chunk(self, chunk_id: str, chunk: str, embedding: List[float], metadata: Dict[str, Any]):
        """
        Updates an existing chunk in the collection.

        :param chunk_id: The ID of the chunk to update.
        :param chunk: The new text chunk.
        :param embedding: The new embedding for the chunk.
        :param metadata: The new metadata for the chunk.
        """
        self.collection.update(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[metadata]
        )

    def delete_chunks(self, chunk_ids: List[str]):
        """
        Deletes chunks from the collection by their IDs.

        :param chunk_ids: A list of chunk IDs to delete.
        """
        self.collection.delete(ids=chunk_ids)

    def list_collections(self) -> List[str]:
        """
        Lists all collections in the database.

        :return: A list of collection names.
        """
        return [c.name for c in self.client.list_collections()]

