from datetime import datetime
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

StatusType = Literal["completed", "error"]

MODEL_ROLE = os.getenv("MODEL_ROLE", "model")

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
    enhanced_query: str = Field(description="The context-enrichen, rewritten query with a lot of details.")
    need_for_retrieval: bool = Field(description="Whether retrieval of documents is necessary to answer the query.")
    
class ResponseWithRetrieval(BaseModel):
    """
    Represents a response that includes both the generated answer and a request for additional information if necessary.
    """
    answer: str = Field(description="The generated answer to the user's query. (MarkDown is suppoted)")
    any_more_info_needed: Optional[str] = Field(None, description="Any additional information in context of documents if not enough to fulfill user query.")
    
class ResponseWithoutRetrieval(BaseModel):
    """
    Represents a response that includes only the generated answer without any retrieved chunks.
    """
    answer: str = Field(description="The generated answer to the user's query.")
    
from typing import Union

class UserMessage(BaseModel):
    sender: Literal["user"]
    content: str

class RetrievedDocument(BaseModel):
    id: str
    name: str

class AgentMessage(BaseModel):
    sender: Literal["agent"]
    content: str
    retrieved_docs: Optional[List[RetrievedDocument]] = None
    follow_up: Optional[bool] = None

Message = Union[UserMessage, AgentMessage]

class Thread(BaseModel):
    id: str
    name: str
    created_at: datetime
    history: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any]
    document_ids: List[str] = []
    
    
class UserMessageRequest(BaseModel):
    content: str
    use_db_explorer: bool = False

class ThreadName(BaseModel):
    name: str

class LanguageRequest(BaseModel):
    language: str

    
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

class AgentResponse(BaseModel):
    answer: str
    retrieved_docs: Optional[List[RetrievedDocument]] = None
    follow_up: Optional[bool] = None
    
    
class ServerStartRequest(BaseModel):
    server_type: str
    config_name: str

class ServerStopRequest(BaseModel):
    server_type: str

class ServerUpdateConfig(BaseModel):
    server_type: str
    config_name: str
    config_index: int
    
class UserLamaMessage(BaseModel):
    role : str = Field(default="user", description="User role")
    content : str = Field(description="User message content")
    
class SystemLamaMessage(BaseModel):
    role : str = Field(default="system", description="System role")
    content : str = Field(description="System message content")

class ModelLamaMessage(BaseModel):
    role : str = Field(default=MODEL_ROLE, description="Model role")
    content : str = Field(description="Model message content")
    
class LLamaMessageHistory(BaseModel):
    messages: List[Union[UserLamaMessage, SystemLamaMessage, ModelLamaMessage]] = Field(description="List of messages in the conversation history")
    def to_dict(self) -> List[Dict[str, str]]:
        
        return [{"role" : message.role, "content" : message.content} for message in self.messages]
    

class DataBaseQueryList(BaseModel):
    sql_queries: List[str] = Field(description="The list of SQL queries to be executed on the database. Avoid using `UNION` in sql queries.")
    
class DataBaseIntentAnalysis(BaseModel):
    enhanced_query: str = Field(description="The context-enrichen, rewritten query with a lot of details.")
    need_for_sql: bool = Field(description="Whether SQL query is necessary to answer the query.")
    
class ResponseWithDatabase(BaseModel):
    """
    Represents a response that includes both the generated answer and a request for additional information if necessary.
    """
    answer: str = Field(description="The generated answer to the user's query. (MarkDown is suppoted)")
    any_more_info_needed: Optional[str] = Field(None, description="Any additional information in context of database or context if not enough to fulfill user query.")
    