
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


#  Message 

class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    pass


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


#  Conversation 

class ConversationBase(BaseModel):
    user_id: int


class ConversationCreate(ConversationBase):
    first_message: str
    # NEW: mode (default "open")
    mode: Optional[str] = "open"  # "open" or "rag"


class ConversationSummary(BaseModel):
    id: int
    created_at: datetime
    title: Optional[str] = None

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    title: Optional[str] = None
    mode: str
    messages: List[MessageOut]

    model_config = {"from_attributes": True}


# Assistant reply 

class AssistantReply(BaseModel):
    assistant_message: MessageOut

    model_config = {"from_attributes": True}


#  Document upload 

class DocumentUploadResult(BaseModel):
    document_id: int
    num_chunks: int
