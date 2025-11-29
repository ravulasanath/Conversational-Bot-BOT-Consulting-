<h1 align="center">🤖 FastAPI LLM Chat Backend (Open Chat + RAG with PDFs)</h1>

<p align="center">
  <b>A production-ready backend for chat with LLM + Retrieval-Augmented Generation using PDFs.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img src="https://img.shields.io/badge/Groq%20LLM-Enabled-purple?style=for-the-badge">
</p>

---

# 📌 Overview

This project implements a **fully functional backend chat system** supporting:

### ✅ Open Chat Mode  
Regular conversation with an LLM (Groq API).

### ✅ RAG Mode (Retrieval-Augmented Generation)  
Upload PDFs → Extract text → Chunk → Retrieve relevant context → Enhance LLM responses.

### ✅ Persistent Storage  
SQLite stores:
- Users  
- Conversations  
- Messages  
- Documents  
- Chunks  

### 🎯 Best For:
- AI chat apps  
- LLM-integrated dashboards  
- Document Q&A  
- PDF chat tools (ChatPDF-like)  

---

# ⚙️ Architecture

