import os
from fastapi import APIRouter
from app.generator import Generator
from app.embedding_client import EmbeddingClient
from app.utils.helpers import safe_json
from app.main import MODELS_FOLDER

def get_util_router(llm_client, embed_client):
    router = APIRouter()

    # Use provided dependencies
    _llm_client = llm_client
    _embed_client = embed_client

    @router.get("/status")
    async def get_status():
        return safe_json({"status": "ready"})

    @router.get("/chat_model")
    def get_chat_model_handler():
        return safe_json(_llm_client.get_model_info())

    @router.get("/embedding_model")
    def get_embedding_model_handler():
        return safe_json({"model": _embed_client._get_model_from_server()})

    @router.get("/get_loaded_models")
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

    @router.get("/chat_model_info")
    def get_chat_model():
        return safe_json(
            {"model": _llm_client.get_model_info()}
        )
        
    @router.get("/embed_model_info")
    def get_embed_model():
        return safe_json(
            {"model": _embed_client._get_model_from_server()}
        )

    return router