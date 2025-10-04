import requests
from typing import List

from colors import SUCCESS_COLOR, Colors

class EmbeddingClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initializes the EmbeddingClient.

        :param base_url: The base URL of the llama.cpp server.
        """
        self.base_url = base_url
        print(f"{SUCCESS_COLOR}Embedding Server instantiated successfully.{Colors.RESET}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generates an embedding for the given text.

        :param text: The text to embed.
        :return: A list of floats representing the embedding.
        """
        try:
            response = requests.post(
                f"{self.base_url}/embedding",
                json={"content": text},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            data = response.json()
            try:
                # The server returns a list containing a dictionary, 
                # with the embedding nested inside a list.
                return data[0]['embedding'][0]
            except (IndexError, KeyError, TypeError) as e:
                print(f"Failed to parse embedding from server response: {e}")
                print(f"Received data: {data}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while communicating with the embedding server: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    client = EmbeddingClient(base_url="http://127.0.0.1:8000")
    
    # --- Text to embed ---
    text_to_embed = "This is a test sentence for the embedding client."
    
    print(f"Embedding the text: '{text_to_embed}'")
    
    # --- Generate embedding ---
    embedding = client.embed_text(text_to_embed)
    
    # --- Print results ---
    if embedding:
        print(f"Successfully generated embedding of dimension: {len(embedding)}")
        # print("Embedding vector (first 10 values):", embedding[:10]) 
    else:
        print("Failed to generate embedding.")