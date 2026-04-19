# AITube: Agentic AI YouTube Analysis and RAG Platform

AITube is a sophisticated, microservices-oriented platform designed to provide deep insights into YouTube content. By leveraging state-of-the-art Large Language Models (LLMs) and Vector Databases, AITube transforms passive video watching into an interactive, AI-driven learning experience.

## Technical Architecture Overview

The system architecture is built on a distributed microservices model to ensure scalability and separation of concerns:

*   **Core Orchestrator (Django)**: Manages the user lifecycle, playlist indexing, and cross-service communication.
*   **Video Intelligence Service (FastAPI)**: Utilizes `yt-dlp` for high-fidelity metadata extraction and advanced transcript processing.
*   **Cognitive Analysis Service (FastAPI)**: Performs multi-dimensional analysis including thematic summarization, roadmap generation, and sentiment modeling using Gemini 1.5.
*   **RAG Engine (FastAPI + ChromaDB)**: Implements a Retrieval-Augmented Generation pipeline to enable context-aware conversations based on video transcripts.

## Key Capabilities

### 1. Advanced Content Analysis
- **Automated Roadmaps**: Generates step-by-step learning paths based on video content.
- **Key Takeaways**: Extracts actionable insights and structured knowledge points.
- **Sentiment & Emotion Modeling**: Analyzes audience perception and emotional tone through LLM-assisted scoring.

### 2. Contextual RAG Chat
- **Vectorized Search**: Transcripts are indexed in ChromaDB for semantic retrieval.
- **Augmented Inference**: Uses Llama-3 (via Groq) to answer complex questions with high precision and low latency.

### 3. Production-Ready Deployment
- **Docker Integration**: Full containerization for all services ensuring environment parity.
- **Render Blueprints**: Ready-to-use `render.yaml` for automated cloud deployment.
- **Scalable Infrastructure**: Designed to integrate with external vector stores like Pinecone and managed PostgreSQL databases.

## Development and Deployment

### Local Environment Setup
1.  Initialize the environment configuration:
    ```bash
    cp .env.example .env
    ```
2.  Launch the services using Docker Compose:
    ```bash
    docker-compose up --build
    ```

### Production Deployment
The platform is optimized for deployment on **Render**. For detailed instructions on secret management and internal networking, refer to the `deployment_guide.md` and `system_design.md` documents.

## Technology Stack
- **Frameworks**: Django, FastAPI, LangChain
- **AI/ML**: Groq (Llama-3), Google Gemini 1.5 Flash
- **Database**: PostgreSQL (Relational), ChromaDB (Vector)
- **Utilities**: yt-dlp, ffmpeg, Whitenoise

---
© 2024 AITube Platform. All rights reserved.
