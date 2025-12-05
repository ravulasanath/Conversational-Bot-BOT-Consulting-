
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    UploadFile,
    File,
)
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..llm_client import call_llm

from PyPDF2 import PdfReader
import os
import re


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)

MAX_HISTORY_MESSAGES = 10  # sliding window size
UPLOAD_DIR = "uploaded_docs"


# Helper functions


def get_or_create_user(db: Session, user_id: int) -> models.User:
    """
    For simplicity:
    - if user with given id exists -> return it
    - else create a new user with this id and default name
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        return user

    
    user = models.User(id=user_id, name=f"user-{user_id}")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def build_llm_history(messages: List[models.Message]) -> List[dict]:
    """
    Convert DB messages -> LLM messages.
    Uses only the last MAX_HISTORY_MESSAGES messages (sliding window).
    """
    last = messages[-MAX_HISTORY_MESSAGES:]
    return [{"role": m.role, "content": m.content} for m in last]


# RAG helpers 


def chunk_text(text: str, max_chars: int = 800, overlap: int = 200) -> List[str]:
    """
    Character-based chunker with safety checks to avoid MemoryError.
    Designed for small PDFs (1–5 pages).
    """
    text = text.strip()

    # Safety check: don't accept huge text blobs
    if len(text) > 200_000:
        raise ValueError("Text too large — chunking aborted")

    chunks: List[str] = []
    text_len = len(text)

    # step must be positive
    step = max_chars - overlap
    if step <= 0:
        step = max_chars

    start = 0
    while start < text_len:
        end = min(start + max_chars, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def normalize(text: str) -> List[str]:
    """
    Very simple tokenizer: lowercase + keep only alphabetic tokens.
    Used for naive keyword-based similarity.
    """
    text = text.lower()
    words = re.findall(r"[a-zA-Z]+", text)
    return words


def simple_similarity(query: str, chunk: str) -> float:
    """
    Compute simple Jaccard similarity between query words and chunk words.
    This is NOT real embeddings, but good enough to demonstrate retrieval.
    """
    q_words = set(normalize(query))
    c_words = set(normalize(chunk))
    if not q_words or not c_words:
        return 0.0

    inter = len(q_words & c_words)
    union = len(q_words | c_words)
    return inter / union


def retrieve_relevant_chunks(
    db: Session, conversation_id: int, query: str, top_k: int = 3
) -> List[str]:
    """
    Retrieve the most relevant chunks for a conversation using simple keyword similarity.
    """
    chunks = (
        db.query(models.DocumentChunk)
        .join(models.Document)
        .filter(models.Document.conversation_id == conversation_id)
        .all()
    )

    if not chunks:
        return []

    scored = [
        (simple_similarity(query, ch.content), ch.content)
        for ch in chunks
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    best = [c for score, c in scored[:top_k] if score > 0]
    return best


def build_rag_prompt(context_chunks: List[str], user_message: str) -> List[dict]:
    """
    Construct LLM messages with RAG context.
    """
    context_text = "\n\n".join(context_chunks) if context_chunks else "No relevant context found."
    system_msg = (
        "You are a helpful assistant. Use the provided context to answer "
        "the user's question. If the context is not enough, say so clearly."
    )
    context_msg = f"CONTEXT:\n{context_text}"
    user_msg = f"QUESTION:\n{user_message}"

    return [
        {"role": "system", "content": system_msg},
        {"role": "assistant", "content": context_msg},
        {"role": "user", "content": user_msg},
    ]



# API endpoints



@router.post(
    "",
    response_model=schemas.ConversationDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: schemas.ConversationCreate,
    db: Session = Depends(get_db),
):
    """
    Start a new conversation with the first user message.
    Supports mode = 'open' or 'rag' (RAG needs documents to be uploaded later).
    """
    # Ensure user exists (or create)
    user = get_or_create_user(db, payload.user_id)

    # Determine mode: "open" (default) or "rag"
    mode = payload.mode or "open"
    if mode not in ("open", "rag"):
        raise HTTPException(
            status_code=400,
            detail="mode must be 'open' or 'rag'",
        )

    # Create conversation
    conversation = models.Conversation(user_id=user.id, mode=mode)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # First user message
    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.first_message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # For first reply, we use normal sliding window logic.
    history = build_llm_history([user_msg])
    try:
        assistant_text = call_llm(history)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to call LLM: {e}",
        )

    assistant_msg = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    db.refresh(conversation)  # to load messages
    return conversation


@router.post(
    "/{conversation_id}/documents",
    response_model=schemas.DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    conversation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a document (text-based PDF) and attach it to a conversation.
    The text is extracted, chunked, and stored for later RAG use.
    Designed for small PDFs (1-5 pages).
    """
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save file to disk
    filepath = os.path.join(UPLOAD_DIR, f"conv{conversation_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())

    # Extract text from PDF
    try:
        reader = PdfReader(filepath)
        full_text_parts: List[str] = []

        for page in reader.pages:
            text = page.extract_text()
            if not text:
                continue
            text = text.strip()
            # Ignore tiny/noise pages
            if len(text) < 10:
                continue
            full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {e}")

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="No text found in document")

    # Safety: limit size to prevent MemoryError
    if len(full_text) > 200_000:
        raise HTTPException(
            status_code=400,
            detail="PDF too large. Please upload a smaller document (around 1–5 pages).",
        )

    # Chunk the text (with internal safety)
    try:
        chunks = chunk_text(full_text, max_chars=800, overlap=200)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunking failed: {e}")

    # Store document + chunks
    doc = models.Document(
        conversation_id=conversation.id,
        filename=file.filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    for idx, ch in enumerate(chunks):
        db.add(
            models.DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=ch,
            )
        )
    db.commit()

    return schemas.DocumentUploadResult(
        document_id=doc.id,
        num_chunks=len(chunks),
    )


@router.get("", response_model=List[schemas.ConversationSummary])
def list_conversations(
    user_id: int = Query(..., description="User ID to list conversations for"),
    db: Session = Depends(get_db),
):
    """
    List all conversations for a given user.
    """
    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.created_at.desc())
        .all()
    )
    return conversations


@router.get("/{conversation_id}", response_model=schemas.ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a conversation with full message history.
    """
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/{conversation_id}/messages", response_model=schemas.AssistantReply)
def add_message(
    conversation_id: int,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    """
    Add a new user message to an existing conversation.

    If conversation.mode == 'rag':
        - Retrieve relevant document chunks
        - Build a RAG prompt
    Else:
        - Use normal sliding window conversation history.
    """
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Store user message
    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    db.refresh(conversation)  # ensures .messages and .mode are up-to-date

    try:
        if conversation.mode == "rag":
            # RAG flow
            context_chunks = retrieve_relevant_chunks(
                db, conversation_id=conversation.id, query=payload.content, top_k=3
            )
            messages = build_rag_prompt(context_chunks, payload.content)
        else:
            # Open chat flow (no extra context)
            history = build_llm_history(conversation.messages)
            messages = history

        assistant_text = call_llm(messages)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to call LLM: {e}",
        )

    assistant_msg = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return schemas.AssistantReply(assistant_message=assistant_msg)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a conversation and all its messages + documents + chunks.
    """
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return
