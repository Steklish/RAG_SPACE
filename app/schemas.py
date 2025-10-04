from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Document(BaseModel):
    """
    Represents a single document to be processed and stored.
    """
    content: str = Field(description="The full content of the document.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the document, e.g., source, author.")

class Chunk(BaseModel):
    """
    Represents a chunk of a document to be stored in the vector database.
    """
    text: str = Field(description="The text content of the chunk.")
    embedding: List[float] = Field(description="The vector embedding of the chunk's text.")
    metadata: Dict[str, Any] = Field(description="Metadata associated with the chunk, inherited from the parent document.")
    document_id: Optional[str] = Field(None, description="The ID of the document this chunk belongs to.")

class Query(BaseModel):
    """
    Represents a user query.
    """
    text: str = Field(description="The user's query text.")
    top_k: int = Field(5, description="The number of relevant chunks to retrieve.")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters to apply during the search.")

class Answer(BaseModel):
    """
    Represents the final answer provided by the RAG model.
    """
    text: str = Field(description="The generated answer to the user's query.")
    source_chunks: List[Chunk] = Field(description="The list of source chunks used to generate the answer.")
    
