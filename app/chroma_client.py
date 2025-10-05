import os
import uuid
import chromadb
from chromadb.api.types import QueryResult
from typing import List, Dict, Any, Optional, Sequence

from app.embedding_client import EmbeddingClient
from app.ingest import extract_text_from_file, normalize_text, chunk_text


class ChromaClient:
    def __init__(self, embedding_client: EmbeddingClient, path: str = os.getenv("CHROMA_PERSIST_DIR", "chroma_db"), collection_name: str = "rag_collection"):
        """
        Initializes the ChromaClient for persistent storage.

        :param embedding_client: An instance of EmbeddingClient.
        :param path: The directory path for ChromaDB's persistent storage.
        :param collection_name: The name of the collection to use.
        """
        self.embedding_client = embedding_client
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.documents_collection = self.client.get_or_create_collection(name="documents_metadata")

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

    def ingest_file(self, doc_id: str, raw_path: str, file_name: str, file_type: str, uploaded_at: str, chunk_size: int, chunk_overlap: int) -> int:
        """
        Handles the ingestion process for a single file.
        """
        text = extract_text_from_file(raw_path, file_type)
        text = normalize_text(text)

        txt_path = os.path.join(os.path.dirname(raw_path).replace("raw", "text"), f"{doc_id}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        chunks = chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            raise ValueError("No chunks were created from the document.")

        embeddings = self.embedding_client.embed_texts(chunks)
        if not embeddings or len(embeddings) != len(chunks):
            raise ValueError(f"Embeddings mismatch: chunks={len(chunks)} != embeddings={len(embeddings) if embeddings else 0}")

        metadoc = {
            "doc_id": doc_id,
            "name": file_name,
            "type": file_type,
            "size": os.path.getsize(raw_path),
            "uploadedAt": uploaded_at,
        }
        self.store_chunks(chunks, embeddings, [metadoc] * len(chunks))
        return len(chunks)

    def add_document(self, doc_id: str, doc_name_for_embedding: str, metadata: Dict[str, Any]):
        """
        Adds a single document's metadata to the collection.
        The document's name is used to generate the embedding for searching.
        """
        embedding = self.embedding_client.embed_text(doc_name_for_embedding)
        if embedding:
            self.documents_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[doc_name_for_embedding], # Store the name as the document content
                metadatas=[metadata]
            )

    def search_documents(self, query_text: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Searches for documents based on a query text.
        """
        query_embedding = self.embedding_client.embed_text(query_text)
        if filters:
            results = self.documents_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters
            )
        else:
            results = self.documents_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        return results


    def delete_document(self, doc_id: str):
        """
        Deletes a document from the collection by its ID.
        """
        self.documents_collection.delete(ids=[doc_id])
