import chromadb
from typing import List, Dict, Any

class ChromaClient:
    def __init__(self, path: str = "chroma_db", collection_name: str = "rag_collection"):
        """
        Initializes the ChromaClient for persistent storage.

        :param path: The directory path for ChromaDB's persistent storage.
        :param collection_name: The name of the collection to use.
        """
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def store_chunks(self, chunks: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """
        Stores chunked data, embeddings, and metadata in ChromaDB.

        :param chunks: A list of text chunks.
        :param embeddings: A list of embeddings corresponding to the chunks.
        :param metadatas: A list of metadata dictionaries for each chunk.
        """
        ids = [str(i) for i in range(len(chunks))]
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query_embedding: List[float], top_k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
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
        return self.client.list_collections()

if __name__ == "__main__":
    # Example Usage
    
    # 1. Initialize ChromaClient
    chroma_client = ChromaClient(path="chroma_storage", collection_name="my_rag_collection")

    # 2. List collections
    print(f"Available collections: {chroma_client.list_collections()}")

    # 3. Prepare some sample data
    sample_chunks = [
        "The sky is blue.",
        "The grass is green.",
        "The sun is bright.",
        "The moon is white."
    ]
    # Dummy embeddings (replace with actual embeddings in a real scenario)
    sample_embeddings = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.4, 0.3, 0.2, 0.1],
        [0.8, 0.7, 0.6, 0.5]
    ]
    sample_metadatas = [
        {"source": "nature_facts.txt", "topic": "sky"},
        {"source": "nature_facts.txt", "topic": "plants"},
        {"source": "nature_facts.txt", "topic": "sun"},
        {"source": "space_facts.txt", "topic": "moon"}
    ]

    # 4. Store the data
    chroma_client.store_chunks(sample_chunks, sample_embeddings, sample_metadatas)
    print("\nStored sample data in ChromaDB.")

    # 5. Get collection count
    print(f"Number of items in collection: {chroma_client.get_collection_count()}")

    # 6. Prepare a query
    query_embedding = [0.1, 0.2, 0.3, 0.5] # A query embedding similar to "The sky is blue."

    # 7. Perform a search without filters
    search_results = chroma_client.search(query_embedding, top_k=2)
    print("\nSearch results (without filters):")
    print(search_results)

    # 8. Perform a search with a filter
    search_results_filtered = chroma_client.search(query_embedding, top_k=2, filters={"source": "space_facts.txt"})
    print("\nSearch results (with filter for source='space_facts.txt'):")
    print(search_results_filtered)

    # 9. Update a chunk
    chroma_client.update_chunk(
        chunk_id="0",
        chunk="The sky is a beautiful blue.",
        embedding=[0.1, 0.2, 0.3, 0.45],
        metadata={"source": "nature_facts.txt", "topic": "sky", "author": "John Doe"}
    )
    print("\nUpdated chunk with ID 0.")

    # 10. Perform a search after update
    search_results_after_update = chroma_client.search(query_embedding, top_k=2)
    print("\nSearch results (after update):")
    print(search_results_after_update)

    # 11. Delete a chunk
    chroma_client.delete_chunks(chunk_ids=["1"])
    print("\nDeleted chunk with ID 1.")

    # 12. Get collection count after deletion
    print(f"Number of items in collection after deletion: {chroma_client.get_collection_count()}")

    # 13. Delete the collection
    chroma_client.delete_collection()
    print("\nDeleted the collection.")
