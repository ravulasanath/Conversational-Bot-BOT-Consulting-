# app/main.py
from fastapi import FastAPI

from .database import Base, engine
from .routers import conversations

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BOT GPT Backend",
    version="1.0.0",
    description="Backend for BOT GPT conversational platform (case study).",
)


@app.get("/")
def home():
    return {
        "message": "BOT GPT Backend is running",
        "docs": "Visit /docs to explore the API"
    }


app.include_router(conversations.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
