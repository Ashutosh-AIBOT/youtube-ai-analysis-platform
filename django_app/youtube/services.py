import httpx, asyncio
from django.conf import settings

API_KEY = settings.INTERNAL_API_KEY
H       = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def fetch_playlist(url: str) -> list:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{settings.YOUTUBE_SERVICE_URL}/playlist",
            headers=H,
            json={"url": url, "max_videos": 20})
        r.raise_for_status()
        return r.json().get("videos", [])


async def start_analysis(youtube_url: str) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{settings.YOUTUBE_SERVICE_URL}/analyze",
            headers=H,
            json={"url": youtube_url})
        r.raise_for_status()
        return r.json()["job_id"]


async def get_job_result(job_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(
            f"{settings.YOUTUBE_SERVICE_URL}/job/{job_id}",
            headers=H)
        r.raise_for_status()
        return r.json()


async def analyze_sentiment(text: str, video_id: str = "",
                             title: str = "") -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.post(
                f"{settings.SENTIMENT_SERVICE_URL}/analyze",
                headers=H,
                json={"text": text, "video_id": video_id,
                      "video_title": title})
            r.raise_for_status()
            return r.json()
        except Exception:
            return {"sentiment": {"overall_sentiment": "unknown",
                                   "score": 0, "audience_reaction": "unclear"}}


async def rag_ingest(video_id: str, title: str,
                     chunks: list, user_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as c:
        try:
            r = await c.post(
                f"{settings.RAG_WORKER_URL}/ingest",
                headers=H,
                json={"video_id": video_id, "video_title": title,
                      "chunks": chunks, "user_id": user_id})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}


async def rag_query(query: str, video_ids: list,
                    user_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as c:
        try:
            r = await c.post(
                f"{settings.RAG_WORKER_URL}/query",
                headers=H,
                json={"query": query, "video_ids": video_ids,
                      "user_id": user_id, "top_k": 5})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"answer": f"RAG error: {e}", "chunks": []}
