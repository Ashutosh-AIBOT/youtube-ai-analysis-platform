---
title: YouTube AI Analysis Platform
emoji: 🎥
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
---

# 🎥 YouTube AI Analysis Platform

A powerful, multi-service platform for deep analysis of YouTube content, sentiment tracking, and interactive RAG-based chat.

## 🚀 Deployment (Hugging Face Spaces)

This project is optimized for Hugging Face Spaces. It uses a **Multi-Service Architecture** running inside a single Docker container managed by `supervisord`.

### ✨ Key Features
- **Video Analysis**: Summaries, pros/cons, and roadmap generation.
- **Sentiment Engine**: Real-time emotion tracking across video segments.
- **RAG Assistant**: Chat with your YouTube playlists using advanced retrieval.
- **Modern UI**: Built with Django and premium CSS aesthetics.

## 🛠️ Architecture
- **Frontend**: Django + Gunicorn (Port 7860)
- **YouTube Core**: FastAPI + Uvicorn (Port 8005)
- **Sentiment**: FastAPI + Uvicorn (Port 8010)
- **RAG Worker**: FastAPI + Uvicorn (Port 8011)

## 🔑 Environment Variables
To make the AI work, add these to your Space's **Settings -> Variables and Secrets**:
- `DJANGO_SECRET_KEY`: Any long random string.
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `GROQ_API_KEY`: Your Groq API Key.
- `YOUTUBE_API_KEY`: Your YouTube Data API v3 Key.
- `INTERNAL_API_KEY`: `mypassword123` (used for service communication).

---
*Built with ❤️ for the AI community on Hugging Face.*
