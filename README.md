<h1 align="center">Conversational AI Backend with RAG (FastAPI • Groq • SQLite)</h1>

<p align="center">
  <b>A production-ready backend for chat with LLM + Retrieval-Augmented Generation using PDFs.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img src="https://img.shields.io/badge/Groq%20LLM-Enabled-purple?style=for-the-badge">
</p>

---
# Overview

This project implements a backend supporting both standard LLM chat and Retrieval-Augmented Generation using uploaded PDF documents.

---
# Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<repo>.git
cd <repo>
```

### 2. Create a Virtual Environment

```bash
conda create -n proenv python=3.10
conda activate proenv
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=YOUR_REAL_API_KEY_HERE
MODEL_NAME=mixtral-8x7b-32768
```

Never commit `.env` to the repository.

---
# Running the Server

```bash
uvicorn app.main:app --reload
```

* Backend URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---
# Features

### 1. Open Chat Mode

Standard multi-turn conversation with an LLM using the Groq API.

### 2. RAG Mode (Retrieval-Augmented Generation)

Upload PDFs → Extract text → Clean → Chunk → Retrieve relevant context → Build RAG-enhanced prompts → Generate accurate answers.

### 3. Persistent Storage (SQLite)

Stores:

* Users
* Conversations
* Messages
* Documents
* Document Chunks

### 4. Conversation Management

APIs for:

* Creating conversations
* Adding messages
* Uploading PDFs
* Listing conversations
* Fetching history
* Deleting conversations with cascade cleanup

---

# Testing the Project

You can test all APIs using Swagger UI or Postman.

## 1. Create Conversation

POST `/conversations`

```json
{
  "user_id": 1,
  "first_message": "Hello!",
  "mode": "open"
}
```

Modes: `open`, `rag`

---

## 2. Upload PDF (for RAG)

POST `/conversations/{id}/documents`

* form-data → file

Backend will extract, clean, chunk, and store the PDF content.

---

## 3. Send Message

POST `/conversations/{id}/messages`

```json
{
  "content": "What does the document talk about?"
}
```

RAG mode → retrieves chunks, builds RAG prompt

---

## 4. List Conversations

GET `/conversations?user_id=1`

---

## 5. Get Full Conversation

GET `/conversations/{id}`

---

## 6. Delete Conversation

DELETE `/conversations/{id}`

---

# Architecture

```
┌─────────────────────────┐
│        FastAPI          │
│     REST API Layer      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Conversation Logic    │
│  Open Chat + RAG Modes  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     RAG Pipeline        │
│ Extract → Chunk → Store │
│ Retrieve → Build Prompt │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Groq LLM API      │
│                         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│        SQLite DB        │
│ Users, Conversations,   │
│ Messages, Docs, Chunks  │
└─────────────────────────┘
```

---
