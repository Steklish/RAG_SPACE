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
        # print(type(embeddings).__name__)
        # print(embeddings)
        ids = [str(uuid.uuid4()) for _ in chunks]
        self.collection.add(
            embeddings=embeddings, # type: ignore
            documents=chunks,
            metadatas=metadatas, # type: ignore
            ids=ids
        )
        # print("stored chunks")
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
        self.add_document(doc_id, file_name, metadoc)
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


    def search_documents(self, query_text: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Searches for documents based on a query text.
        """
        query_embedding = self.embedding_client.embed_text(query_text)
        if not query_embedding:
            return []
            
        results = self.documents_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )
        
        formatted_results = []
        if results and results['ids'] and len(results['ids']) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                doc = self.get_document(doc_id)
                if doc:
                    formatted_results.append({
                        "id": doc_id,
                        "text": results['documents'][0][i], # type: ignore
                        "metadata": {**results['metadatas'][0][i], "name": doc['name']}, # type: ignore
                        "distance": results['distances'][0][i] # type: ignore
                    })
        
        return formatted_results

    def _get_collections(self):
        return [c.name for c in self.client.list_collections()]

    def delete_document(self, doc_id: str):
        """
        Deletes a document and all its associated chunks from the collections.
        """
        # Delete the document metadata
        self.documents_collection.delete(ids=[doc_id])

        # Delete all chunks associated with the document
        chunk_ids_to_delete = []
        results = self.collection.get(where={"doc_id": doc_id})
        if results and results['ids']:
            chunk_ids_to_delete.extend(results['ids'])
        
        if chunk_ids_to_delete:
            self.delete_chunks(chunk_ids_to_delete)

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Retrieves all documents from the documents_collection.
        """
        print(self._get_collections())
        documents = self.documents_collection.get()
        # Reconstruct the document format
        results = []
        if documents:
            for i, doc_id in enumerate(documents['ids']):
                metadata = documents['metadatas'][i] # type: ignore
                results.append({
                    "id": doc_id,
                    "name": metadata.get("name"),
                    "type": metadata.get("type"),
                    "size": metadata.get("size"),
                    "uploadedAt": metadata.get("uploadedAt"),
                    "status": "completed",  # Assuming all stored docs are complete
                    "chunks": 0, # This would require querying the other collection, maybe not needed for just a list
                })
        return results

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single document from the documents_collection by its ID.
        """
        document = self.documents_collection.get(ids=[doc_id])
        if document and document['ids']:
            metadata = document['metadatas'][0] # type: ignore
            return {
                "id": document['ids'][0],
                "name": metadata.get("name"),
                "type": metadata.get("type"),
                "size": metadata.get("size"),
                "uploadedAt": metadata.get("uploadedAt"),
                "status": "completed",
                "chunks": 0,
            }
        return None

    def get_document_by_name(self, doc_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single document from the documents_collection by its name.
        """
        documents = self.documents_collection.get(where={"name": doc_name})
        if documents and documents['ids']:
            metadata = documents['metadatas'][0] # type: ignore
            return {
                "id": documents['ids'][0],
                "name": metadata.get("name"),
                "type": metadata.get("type"),
                "size": metadata.get("size"),
                "uploadedAt": metadata.get("uploadedAt"),
                "status": "completed",
                "chunks": 0,
            }
        return None

    def search_chunks(self, query_text: str, top_k: int = 5, doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Searches for chunks based on a query text, with an optional filter for document IDs.
        """
        query_embedding = self.embedding_client.embed_text(query_text)
        if not query_embedding:
            return []
        
        # More explicit way to define the where_clause
        where_filter = None
        if doc_ids:
            where_filter = {"doc_id": {"$in": doc_ids}}
        print("Searching docs with filters", where_filter   )
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter # type: ignore
        )
        
        formatted_results = []
        if results and results['ids'] and len(results['ids']) > 0:
            for i, chunk_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "id": chunk_id,
                    "text": results['documents'][0][i], # type: ignore
                    "metadata": results['metadatas'][0][i], # type: ignore
                    "distance": results['distances'][0][i] # type: ignore
                })
        
        return formatted_results