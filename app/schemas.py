from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

StatusType = Literal["completed", "error"]


class Document(BaseModel):
    id: str
    name: str
    type: str
    size: int
    uploadedAt: datetime
    status: StatusType
    chunks: int
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentMetadata(BaseModel):
    id: str
    name: str
    type: str
    size: int
    uploadedAt: datetime
    status: StatusType
    chunks: int
    metadata: Optional[Dict[str, Any]] = None
    
class ConversationThread(BaseModel):
    """
    Represents a conversation thread between a user and the RAG model.
    """
    id: str = Field(description="Unique identifier for the conversation thread.")
    name : str= Field(..., description="Name of the conversation thread.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the thread was created.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the thread was last updated.")
    messages: List["str"] = Field(default_factory=list, description="List of messages in the chat.")

    
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

class IntentAnalysis(BaseModel):
    """
    Represents the intent analysis of a user query.
    """
    intent: str = Field(description="The identified intent of the user's query based on the previous conversation context.")
    need_for_retrieval: bool = Field(description="Whether retrieval of documents is necessary to answer the query.")
    
class ResponseWithRetrieval(BaseModel):
    """
    Represents a response that includes both the generated answer and the relevant retrieved chunks.
    """
    answer: str = Field(description="The generated answer to the user's query.")
    any_more_info_needed: Optional[str] = Field(None, description="Any additional information or context if not enough to fulfill user query.")
    
class ResponseWithoutRetrieval(BaseModel):
    """
    Represents a response that includes only the generated answer without any retrieved chunks.
    """
    answer: str = Field(description="The generated answer to the user's query.")
    
class Thread(BaseModel):
    id: str
    name: str
    created_at: datetime
    history: List[str]
    document_ids: List[str]
    metadata: Dict[str, Any]
    
    
class UserMessage(BaseModel):
    content: str

class ThreadName(BaseModel):
    name: str

    
class DocumentId(BaseModel):
    document_id: str

class ChunkQuery(BaseModel):
    text: str
    top_k: int = 5

class ChunkQueryResult(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    distance: float