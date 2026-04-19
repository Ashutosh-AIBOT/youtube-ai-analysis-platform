"""
RAG Worker Service
- Accepts document chunks
- Embeds and stores in Pinecone OR ChromaDB
- Query splits work across multiple instances
- Load balanced chunk processing
"""
import os, sys, time, hashlib
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from key_manager import smart_llm, key_status

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

API_KEY        = os.getenv("INTERNAL_API_KEY", "mypassword123")
PINECONE_KEY   = os.getenv("PINECONE_API_KEY", "").strip()
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "youtube-rag")
WORKER_ID      = os.getenv("WORKER_ID", "worker-1")

app = FastAPI(title=f"RAG Worker {WORKER_ID}", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

sec = APIKeyHeader(name="X-API-Key")
def verify(key: str = Depends(sec)):
    if key != API_KEY: raise HTTPException(401, "Wrong key")
    return key

# ── Vector store (Pinecone if key exists, else ChromaDB) ──
_embedder  = None
_pinecone  = None
_chroma    = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_store():
    global _pinecone, _chroma
    if PINECONE_KEY:
        if _pinecone is None:
            from pinecone import Pinecone
            pc        = Pinecone(api_key=PINECONE_KEY)
            _pinecone = pc.Index(PINECONE_INDEX)
        return "pinecone", _pinecone
    else:
        if _chroma is None:
            import chromadb
            client = chromadb.PersistentClient(path="./chromadb")
            _chroma = client.get_or_create_collection(
                "youtube_rag", metadata={"hnsw:space": "cosine"})
        return "chroma", _chroma


# ── Request models ─────────────────────────────────────
class IngestReq(BaseModel):
    video_id  : str
    video_title: str
    chunks    : List[str]
    user_id   : str = "default"

class QueryReq(BaseModel):
    query     : str
    video_ids : List[str] = []
    user_id   : str = "default"
    top_k     : int = 5
    generate  : bool = True


# ── Chunk text ─────────────────────────────────────────
def chunk_text(text: str, size: int = 80, overlap: int = 15) -> List[str]:
    words, chunks, i = text.split(), [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i+size]))
        i += size - overlap
    return [c for c in chunks if c.strip()]


# ── Ingest ─────────────────────────────────────────────
@app.post("/ingest")
async def ingest(req: IngestReq, _=Depends(verify)):
    t0    = time.time()
    emb   = get_embedder()
    store_type, store = get_store()

    vecs  = emb.encode(req.chunks, batch_size=32,
                       show_progress_bar=False).tolist()
    ids   = [f"{req.user_id}_{req.video_id}_chunk_{i}"
             for i in range(len(req.chunks))]
    metas = [{"text": req.chunks[i], "video_id": req.video_id, "video_title": req.video_title,
               "user_id": req.user_id, "chunk_no": i, "worker": WORKER_ID}
             for i in range(len(req.chunks))]

    if store_type == "pinecone":
        # Pinecone upsert in batches of 100
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            store.upsert(vectors=[
                {"id": ids[j], "values": vecs[j], "metadata": metas[j]}
                for j in range(i, min(i+batch_size, len(ids)))
            ])
    else:
        store.upsert(ids=ids, documents=req.chunks,
                     embeddings=vecs, metadatas=metas)

    return {"ok": True, "chunks_stored": len(req.chunks),
            "store": store_type, "worker": WORKER_ID,
            "total_ms": round((time.time()-t0)*1000)}


# ── Query ──────────────────────────────────────────────
@app.post("/query")
async def query(req: QueryReq, _=Depends(verify)):
    t0    = time.time()
    emb   = get_embedder()
    qvec  = emb.encode(req.query).tolist()
    store_type, store = get_store()

    chunks = []
    if store_type == "pinecone":
        filter_dict = {"user_id": req.user_id}
        if req.video_ids:
            filter_dict["video_id"] = {"$in": req.video_ids}
        res = store.query(vector=qvec, top_k=req.top_k*2,
                          filter=filter_dict, include_metadata=True)
        for m in res.get("matches", []):
            chunks.append({
                "text"    : m["metadata"].get("text", ""),
                "video_id": m["metadata"].get("video_id",""),
                "score"   : round(m["score"], 4),
            })
    else:
        where = {"user_id": req.user_id}
        res   = store.query(query_embeddings=[qvec],
                            n_results=min(req.top_k*2, max(store.count(),1)),
                            where=where)
        for i, doc in enumerate(res["documents"][0]):
            chunks.append({
                "text"    : doc,
                "video_id": res["metadatas"][0][i].get("video_id",""),
                "score"   : round(1-(res["distances"][0][i] or 0), 4),
            })

    # rerank
    if len(chunks) > 1:
        from sentence_transformers import CrossEncoder
        rr     = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-2-v2",max_length=256)
        scores = rr.predict([[req.query, c["text"]] for c in chunks])
        for i, c in enumerate(chunks):
            c["rerank_score"] = round(float(scores[i]), 4)
        chunks.sort(key=lambda x: x.get("rerank_score", x["score"]), reverse=True)

    top = chunks[:req.top_k]

    if not req.generate or not top:
        return {"chunks": top, "answer": None,
                "total_ms": round((time.time()-t0)*1000)}

    context = "\n\n---\n\n".join(c["text"] for c in top)
    result  = await smart_llm(
        prompt = f"Use the context below to answer accurately.\n\nCONTEXT:\n{context}\n\nQUESTION: {req.query}\n\nANSWER:",
        system = "You are a helpful RAG assistant.",
    )
    return {
        "answer"  : result["reply"],
        "provider": result["provider"],
        "chunks"  : top,
        "total_ms": round((time.time()-t0)*1000),
    }


@app.get("/health")
async def health():
    store_type, _ = get_store()
    return {"status": "ok", "worker": WORKER_ID,
            "store": store_type, **key_status()}

@app.delete("/video/{video_id}")
async def delete_video(video_id: str, user_id: str = "default", _=Depends(verify)):
    store_type, store = get_store()
    if store_type == "pinecone":
        store.delete(filter={"video_id": video_id, "user_id": user_id})
    else:
        store.delete(where={"video_id": video_id})
    return {"deleted": True, "video_id": video_id}
