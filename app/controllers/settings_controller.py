import os
import json
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.generator import Generator
from app.embedding_client import EmbeddingClient
from app.chroma_client import ChromaClient
from app.server_launcher import ServerLauncher
from app.settings_store import SettingsStore
from app.agent import Agent
from app.thread_store import ThreadStore
from app.utils.helpers import safe_json
from app.main import LAUNCH_CONFIG_DIR

def get_settings_router(llm_client, embed_client, chroma_client, thread_store, settings_store, agent):
    router = APIRouter()

    # Use provided dependencies
    _llm_client = llm_client
    _embed_client = embed_client
    _chroma_client = chroma_client
    _thread_store = thread_store
    _settings_store = settings_store
    _agent = agent
    _server_launcher = ServerLauncher()

    @router.get("/")
    def get_settings():
        """
        Provides a consolidated endpoint for all settings.
        """
        stored_settings = _settings_store.get_settings()
        settings = {
            "chat_model": {"model": _llm_client.get_model_info()},
            "embedding_model": {"model": _embed_client._get_model_from_server()},
            "server_configs": _server_launcher.get_available_configs(),
            "active_configs": _server_launcher.get_active_configs(),
            "launch_configs": [f for f in os.listdir(LAUNCH_CONFIG_DIR) if f.endswith('.json')],
            "language": stored_settings.get("language", "Russian")
        }
        return safe_json(settings)

    @router.get("/server_urls")
    def get_server_urls():
        """
        Provides the base URLs for the chat and embedding servers.
        """
        return safe_json({
            "chat_base_url": _agent.generator._backend_type,
            "embed_base_url": os.getenv("LLAMACPP_EMBED_BASE", "http://127.0.0.1:11435").replace("localhost", "127.0.0.1")
        })

    @router.put("/")
    def update_settings(settings: Dict[str, Any]):
        current_settings = _settings_store.get_settings()
        if "language" in settings:
            _agent.language = settings["language"]
        current_settings.update(settings)
        _settings_store.save_settings(current_settings)
        return safe_json({"status": "success", "settings": current_settings})

    @router.get("/launch_configs")
    def get_launch_configs():
        configs = [f for f in os.listdir(LAUNCH_CONFIG_DIR) if f.endswith('.json')]
        return safe_json(configs)

    @router.get("/launch_configs/{config_name}")
    def get_launch_config(config_name: str):
        config_path = os.path.join(LAUNCH_CONFIG_DIR, config_name)
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Config not found")
        with open(config_path, 'r') as f:
            return safe_json(json.load(f))

    @router.post("/launch_configs/{config_name}")
    async def update_launch_config(config_name: str, config: Dict[str, Any]):
        config_path = os.path.join(LAUNCH_CONFIG_DIR, config_name)
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Config not found")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return safe_json({"status": "success", "message": f"Config {config_name} updated."})

    return router