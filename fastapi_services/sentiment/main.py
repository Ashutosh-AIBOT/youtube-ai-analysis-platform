"""
Sentiment Analysis Service
Analyses YouTube video transcripts/comments for sentiment
"""
import os, sys, time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from key_manager import smart_llm, key_status

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

API_KEY = os.getenv("INTERNAL_API_KEY", "mypassword123")

app = FastAPI(title="Sentiment Service", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

sec = APIKeyHeader(name="X-API-Key")
def verify(key: str = Depends(sec)):
    if key != API_KEY: raise HTTPException(401, "Wrong key")
    return key


class SentimentReq(BaseModel):
    text       : str
    video_id   : Optional[str] = ""
    video_title: Optional[str] = ""

class BatchReq(BaseModel):
    items: List[SentimentReq]


SENTIMENT_PROMPT = """Analyse the sentiment of this video content and return ONLY this JSON structure:

{{
  "overall_sentiment": "positive|negative|neutral|mixed",
  "score": 0.0,
  "confidence": 0.0,
  "emotions": {{
    "joy": 0.0,
    "sadness": 0.0,
    "anger": 0.0,
    "fear": 0.0,
    "surprise": 0.0,
    "excitement": 0.0
  }},
  "audience_reaction": "will_like|will_dislike|mixed|unclear",
  "engagement_prediction": "high|medium|low",
  "key_sentiments": ["sentiment1", "sentiment2", "sentiment3"],
  "summary": "one sentence summary of overall sentiment"
}}

Score is -1.0 (very negative) to 1.0 (very positive).
All emotion values are 0.0 to 1.0.

Video title: {title}
Content: {content}"""


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sentiment", **key_status()}


@app.post("/analyze")
async def analyze_sentiment(req: SentimentReq, _=Depends(verify)):
    t0 = time.time()
    try:
        result = await smart_llm(
            prompt     = SENTIMENT_PROMPT.format(
                title  = req.video_title or "Unknown",
                content= req.text[:3000]),
            system     = "You are a sentiment analysis expert. Return ONLY valid JSON.",
            max_tokens = 512,
            temperature= 0.1,
        )
        # parse JSON from reply
        import json, re
        reply = result["reply"]
        # extract JSON block
        match = re.search(r'\{.*\}', reply, re.DOTALL)
        if match:
            sentiment_data = json.loads(match.group())
        else:
            raise ValueError("No JSON in response")

        return {
            "video_id"  : req.video_id,
            "sentiment" : sentiment_data,
            "provider"  : result["provider"],
            "total_ms"  : round((time.time() - t0) * 1000),
        }
    except Exception as e:
        # fallback simple analysis
        text_lower = req.text.lower()
        pos = sum(1 for w in ["good","great","excellent","amazing","love","best","helpful"]
                  if w in text_lower)
        neg = sum(1 for w in ["bad","terrible","hate","worst","boring","useless","poor"]
                  if w in text_lower)
        score = (pos - neg) / max(pos + neg, 1)
        return {
            "video_id": req.video_id,
            "sentiment": {
                "overall_sentiment"      : "positive" if score > 0 else "negative" if score < 0 else "neutral",
                "score"                  : round(score, 2),
                "confidence"             : 0.5,
                "audience_reaction"      : "will_like" if score > 0 else "mixed",
                "engagement_prediction"  : "medium",
                "key_sentiments"         : ["informative"],
                "summary"                : "Basic sentiment analysis (LLM unavailable)",
            },
            "provider" : "fallback",
            "total_ms" : round((time.time() - t0) * 1000),
            "error"    : str(e),
        }


@app.post("/batch")
async def batch_sentiment(req: BatchReq, _=Depends(verify)):
    """Analyse multiple videos sentiment at once"""
    import asyncio
    tasks   = [analyze_sentiment(item, _) for item in req.items[:10]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "results": [r if not isinstance(r, Exception) else {"error": str(r)}
                    for r in results],
        "count"  : len(results),
    }


@app.get("/keys")
async def keys_status(_=Depends(verify)):
    return key_status()
