import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import dependencies
from app.generator import Generator
from app.embedding_client import EmbeddingClient
from app.chroma_client import ChromaClient
from app.thread_store import ThreadStore
from app.agent import Agent
from app.settings_store import SettingsStore

load_dotenv(override=True)


STORAGE_RAW_DIR = os.getenv("STORAGE_RAW_DIR", "./storage/raw")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma")
MODELS_FOLDER = "./models"

# Чанкинг/ретрив
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
DEFAULT_TOP_K = int(os.getenv("TOP_K", "4"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

# llama.cpp base urls
LLAMACPP_CHAT_BASE = os.getenv("LLAMACPP_CHAT_BASE", "http://127.0.0.1:11434").replace("localhost", "127.0.0.1")
LLAMACPP_EMBED_BASE = os.getenv("LLAMACPP_EMBED_BASE", "http://127.0.0.1:11435").replace("localhost", "127.0.0.1")

LLAMACPP_TIMEOUT_S = float(os.getenv("LLAMACPP_TIMEOUT_S", "300"))
LLAMACPP_MAX_RETRIES = int(os.getenv("LLAMACPP_MAX_RETRIES", "3"))

# Директории
os.makedirs("./storage", exist_ok=True)
os.makedirs("./storage/threads", exist_ok=True)
os.makedirs("./storage/dev", exist_ok=True)
os.makedirs(STORAGE_RAW_DIR, exist_ok=True)
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
LAUNCH_CONFIG_DIR = "./app/launch_configs"

# Initialize global dependencies
llm_client = Generator(LLAMACPP_CHAT_BASE)
embed_client = EmbeddingClient(LLAMACPP_EMBED_BASE)
chroma_client = ChromaClient(embed_client, CHROMA_PERSIST_DIR)
thread_store = ThreadStore()
settings_store = SettingsStore()
initial_settings = settings_store.get_settings()
agent = Agent(llm_client, chroma_client, thread_store, language=initial_settings.get("language", "Russian"))

# Import controllers after dependencies are initialized
from app.controllers.server_controller import router as server_router
from app.controllers.document_controller import get_document_router
from app.controllers.thread_controller import get_thread_router
from app.controllers.settings_controller import get_settings_router
from app.controllers.util_controller import get_util_router

document_router = get_document_router(llm_client, embed_client, chroma_client, thread_store, agent)
thread_router = get_thread_router(llm_client, embed_client, chroma_client, thread_store, agent)
settings_router = get_settings_router(llm_client, embed_client, chroma_client, thread_store, settings_store, agent)
util_router = get_util_router(llm_client, embed_client)

app = FastAPI(title="RAGgie BOY", version="0.0.1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include controllers
app.include_router(server_router, prefix="/api/servers", tags=["servers"])
app.include_router(document_router, prefix="/api/documents", tags=["documents"])
app.include_router(thread_router, prefix="/api/threads", tags=["threads"])
app.include_router(settings_router, prefix="/api", tags=["settings"])
app.include_router(util_router, prefix="/api", tags=["utils"])
