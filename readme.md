# Run chat model (example)
```shell
llama-server.exe --model D:\Duty\RR\models\gemma-3-1B-it-QAT-Q4_0.gguf --n_gpu_layers 999 --port 8080  --ctx-size 12000
```

Run embedding model (example)
```shell
llama-server --host 0.0.0.0 --port 11435 --model ..\..\..\RagFlow\models\embeddinggemma-300m-qat-Q8_0.gguf --embedding -c 2048 
```

# RAG AI Application

This project is a simple Retrieval-Augmented Generation (RAG) application that uses a local LLM server, ChromaDB for vector storage, a FastAPI backend, and a React-based user interface.

## Core Components

The application is divided into a Python backend responsible for the AI logic and a React frontend for user interaction.

### Backend (`app/`)

-   **`main.py`**: A FastAPI server that exposes endpoints for uploading documents, managing chat threads, and interacting with the AI agent.
-   **`agent.py`**: Contains the `Agent` class, which orchestrates the user intent detection, document retrieval, and response generation logic.
-   **`chroma_client.py`**: A client for ChromaDB that manages two collections: one for text chunks (`rag_collection`) and another for document metadata (`documents_metadata`). It also handles file ingestion, including text extraction and chunking.
-   **`embedding_client.py`**: A client for generating text embeddings using a local embedding model server.
-   **`local_generator.py`**: A client for generating text responses from a local chat model server.
-   **`thread_store.py`**: Manages conversation threads by storing and retrieving them from the local filesystem.
-   **`schemas.py`**: Defines the Pydantic models used for data validation and structuring throughout the backend.

### Frontend (`UI/`)

-   A React application built with Vite.
-   Uses Material-UI for components and styling.
-   Features a tabbed interface for "Chat" and "Settings".
-   Includes resizable panels for a flexible user layout.

## How It Works

1.  **Document Ingestion**: Users can upload documents through the UI. The backend saves the file, extracts its text, splits it into chunks, generates embeddings for each chunk, and stores them in ChromaDB. Document metadata is stored in a separate collection.
2.  **Chat Interaction**: When a user sends a message, the `Agent` first determines the user's intent and whether information retrieval is necessary.
3.  **Retrieval**: If retrieval is needed, the `Agent` uses the `ChromaClient` to search for relevant text chunks from the indexed documents.
4.  **Generation**: The retrieved chunks and conversation history are passed to the `LocalGenerator`, which uses the local LLM to generate a response.
5.  **Conversation Management**: The `ThreadStore` keeps track of the conversation history for each chat session.

## Running the Application

To run this application, you need to start the local model servers, the FastAPI backend, and the React frontend.

### 1. Run Model Servers

You need two separate `llama-server` instances: one for the chat model and one for the embedding model.

**Run Chat Model (Example):**
```shell
llama-server.exe --model D:\Duty\RR\models\gemma-3-1B-it-QAT-Q4_0.gguf --n_gpu_layers 999 --port 11434 --ctx-size 12000
```

**Run Embedding Model (Example):**
```shell
llama-server --host 0.0.0.0 --port 11435 --model ..\..\..\RagFlow\models\embeddinggemma-300m-qat-Q8_0.gguf --embedding -c 2048
```
*Note: Adjust the model paths and parameters as needed.*

### 2. Run the Backend Server

Navigate to the project's root directory and run the FastAPI application using `uvicorn`.

```shell
cd D:\Duty\RR
uvicorn app.main:app --reload
```
The backend will be available at `http://127.0.0.1:8000`.

### 3. Run the Frontend UI

In a separate terminal, navigate to the `UI` directory, install the dependencies, and start the Vite development server.

```shell
cd D:\Duty\RR\UI
npm install
npm run dev
```
The user interface will be available at `http://localhost:5173` (or another port if 5173 is in use).
