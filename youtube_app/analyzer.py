import subprocess, json, re, time, tempfile, glob, httpx
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from urllib.parse import urlparse, parse_qs
from config import GROQ_API_KEY, GEMINI_API_KEY, YOUTUBE_API_KEY, LOCAL_LLM_URL, LOCAL_MODEL

# ── LLM helper ─────────────────────────────────────────
def _get_llm():
    if GROQ_API_KEY:
        try:
            return ChatGroq(api_key=GROQ_API_KEY,
                            model_name="llama-3.3-70b-versatile",
                            temperature=0.3)
        except Exception as e:
            print(f"[ERROR] Groq LLM init failed: {e}")
            pass
    if GEMINI_API_KEY:
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=0.3)
        except Exception as e:
            print(f"[ERROR] Gemini LLM init failed: {e}")
            pass
    return None


async def _local_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{LOCAL_LLM_URL}/api/generate",
            json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False})
        r.raise_for_status()
        return r.json()["response"]


async def _ask(prompt: str, system: str = "You are a helpful analyst.") -> tuple[str, str]:
    """Returns (reply, provider)"""
    print(f"[DEBUG] Asking LLM (system: {system[:50]}...)")
    llm = _get_llm()
    if llm:
        print(f"[DEBUG] Using Cloud LLM: {llm}")
        tmpl  = ChatPromptTemplate.from_messages([
            ("system", system), ("human", "{input}")])
        chain = tmpl | llm | StrOutputParser()
        reply = chain.invoke({"input": prompt})
        prov  = "groq" if isinstance(llm, ChatGroq) else "gemini"
        print(f"[DEBUG] LLM Response received from {prov}")
        return reply, prov
    print(f"[DEBUG] Falling back to Local LLM at {LOCAL_LLM_URL}")
    reply = await _local_llm(f"{system}\n\n{prompt}")
    return reply, "local"


# ── yt-dlp helpers ─────────────────────────────────────
def get_video_info(url: str) -> dict:
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", url],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            return {
                "title"      : d.get("title", ""),
                "duration"   : d.get("duration", 0),
                "channel"    : d.get("channel", ""),
                "view_count" : d.get("view_count", 0),
                "upload_date": d.get("upload_date", ""),
                "description": (d.get("description") or "")[:400],
                "thumbnail"  : d.get("thumbnail", ""),
            }
    except Exception:
        pass
    return {}


from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(url: str) -> str:
    """Try youtube-transcript-api first, fall back to yt-dlp, then description"""
    print(f"[DEBUG] Fetching transcript for {url}")
    video_id = ""
    if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url: video_id = url.split("be/")[1].split("?")[0]
    
    if video_id:
        try:
            print(f"[DEBUG] Trying youtube-transcript-api for {video_id}")
            tr_list = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([i['text'] for i in tr_list])
            print(f"[DEBUG] Successfully got transcript from API: {len(text)} chars")
            return text
        except Exception as e:
            print(f"[WARNING] youtube-transcript-api failed: {e}")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            print(f"[DEBUG] Falling back to yt-dlp subtitles in {tmp}")
            res = subprocess.run(
                ["yt-dlp", "--write-auto-subs", "--sub-format", "vtt",
                 "--skip-download", "-o", f"{tmp}/v", url],
                capture_output=True, text=True, timeout=60)
            files = glob.glob(f"{tmp}/*.vtt")
            if files:
                print(f"[DEBUG] Found subtitle file via yt-dlp: {files[0]}")
                raw   = open(files[0]).read()
                clean = re.sub(r"<[^>]+>", "", raw)
                clean = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}.*?-->\s*\d{2}:\d{2}:\d{2}\.\d{3}", "", clean)
                clean = re.sub(r"\n+", "\n", clean).strip()
                return clean
            else:
                print("[DEBUG] No subtitle files found via yt-dlp.")
    except Exception as e:
        print(f"[ERROR] get_transcript fallback failed: {e}")
    return ""


def get_playlist_videos(url: str, max_videos: int = 10) -> list:
    """
    Returns a list of videos in a playlist.

    Primary: `yt-dlp --flat-playlist` (works without API key, but can be blocked in some hosted envs).
    Fallback: YouTube Data API v3 `playlistItems` if `YOUTUBE_API_KEY` is set.
    """
    yt_videos: list[dict] = []
    try:
        r = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json",
             "--playlist-end", str(max_videos), url],
            capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            err = (r.stderr or "").strip().splitlines()[:6]
            print(f"[WARNING] yt-dlp playlist failed (rc={r.returncode}): " + " | ".join(err))
        for line in (r.stdout or "").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                vid = d.get("id", "") or ""
                if not vid:
                    continue
                yt_videos.append({
                    "title": d.get("title", "") or "",
                    "id": vid,
                    "url": f"https://youtube.com/watch?v={vid}",
                    "duration": d.get("duration", 0) or 0,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[WARNING] yt-dlp playlist exception: {e}")

    if yt_videos:
        return yt_videos[:max_videos]

    api_key = (YOUTUBE_API_KEY or "").strip()
    if not api_key:
        return []

    playlist_id = _extract_playlist_id(url)
    if not playlist_id:
        print("[WARNING] Could not extract playlist id from URL for API fallback.")
        return []

    try:
        return _fetch_playlist_videos_api(playlist_id, api_key, max_videos=max_videos)
    except Exception as e:
        print(f"[WARNING] YouTube Data API playlist fallback failed: {e}")
        return []


def _extract_playlist_id(url: str) -> str:
    try:
        qs = parse_qs(urlparse(url).query)
        pl = (qs.get("list") or [""])[0].strip()
        if pl:
            return pl
    except Exception:
        pass
    # Some users paste only the id, or URLs like "...?list=...&si=..."
    m = re.search(r"(?:^|[?&])list=([A-Za-z0-9_-]+)", url)
    return (m.group(1) if m else "").strip()


def _fetch_playlist_videos_api(playlist_id: str, api_key: str, max_videos: int = 10) -> list:
    videos: list[dict] = []
    page_token: str | None = None

    with httpx.Client(timeout=20) as c:
        while len(videos) < max_videos:
            remaining = max_videos - len(videos)
            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": min(50, remaining),
                "key": api_key,
            }
            if page_token:
                params["pageToken"] = page_token
            r = c.get("https://www.googleapis.com/youtube/v3/playlistItems", params=params)
            if r.status_code != 200:
                raise RuntimeError(f"playlistItems status={r.status_code} body={r.text[:200]}")
            data = r.json()
            for item in data.get("items", []) or []:
                sn = item.get("snippet") or {}
                rid = (sn.get("resourceId") or {}).get("videoId") or ""
                if not rid:
                    continue
                videos.append({
                    "title": sn.get("title", "") or "",
                    "id": rid,
                    "url": f"https://youtube.com/watch?v={rid}",
                    "duration": 0,
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return videos[:max_videos]


# ── emotion detection (keyword-based, no heavy model) ──
EMOTIONS = {
    "excited" : ["wow", "amazing", "incredible", "awesome", "brilliant", "fantastic"],
    "happy"   : ["great", "wonderful", "love", "enjoy", "happy", "excellent", "good"],
    "focused" : ["important", "note", "key", "must", "learn", "understand", "critical"],
    "sad"     : ["unfortunately", "problem", "fail", "bad", "difficult", "hard", "sad"],
    "neutral" : [],
}

def detect_emotions(transcript: str) -> list:
    if not transcript:
        return []
    words    = transcript.lower().split()
    segments = []
    window   = 60
    for i in range(0, min(len(words), window * 8), window):
        chunk = words[i:i + window]
        scores = {e: sum(1 for w in chunk if w in kws)
                  for e, kws in EMOTIONS.items() if kws}
        dominant = max(scores, key=scores.get) if max(scores.values(), default=0) > 0 else "neutral"
        segments.append({
            "segment"   : i // window + 1,
            "word_range": f"{i}–{i+window}",
            "emotion"   : dominant,
            "confidence": round(min(1.0, scores.get(dominant, 0) / 3), 2),
        })
    return segments


# ── LLM analysis prompts ───────────────────────────────
SUMMARY_PROMPT = """You are an expert content analyst. Analyse this YouTube video and return EXACTLY this structure with no extra text:

SUMMARY:
Write 2-3 short crisp sentences. Each sentence max 20 words. Cover: what the video is about, what problem it solves, and what viewer learns.

KEY POINTS:
- One key insight as a short sentence (max 15 words, start with strong verb)
- Cover the most important concept in the video
- Include a technical or practical insight
- Include one actionable thing viewer can do after watching
- Include one non-obvious or surprising fact from the video

PROS:
+ One clear strength of this content (max 12 words)
+ Strength focused on learning or explanation quality (max 12 words)
+ Strength about practical value (max 12 words)

CONS:
- One honest gap or limitation (max 12 words)
- One thing missing or assumed without explanation (max 12 words)

TARGET AUDIENCE:
One sentence: exactly who benefits most from watching this.

Video title: {title}
Content: {content}"""

ROADMAP_PROMPT = """You are a learning path expert. Create a step-by-step roadmap from this video.

Rules:
- Each step is one short sentence (max 15 words)
- Start each step with an action verb: Learn, Understand, Build, Practice, Explore, Apply, Master
- Order steps from easiest to hardest
- Match number of steps to number of topics covered (max 7 steps)
- Write only the step text — no numbers, no bullets

Video title: {title}
Content: {content}"""


async def analyse_video(url: str) -> dict:
    print(f"[INFO] Starting analysis for video: {url}")
    t0   = time.time()
    info = get_video_info(url)
    print(f"[DEBUG] Video info retrieved: {info.get('title')}")
    
    tx   = get_transcript(url) or info.get("description", "")
    if not tx:
        print("[WARNING] No transcript or description found.")
    
    result = {
        "url"       : url,
        "video_info": info,
        "emotions"  : detect_emotions(tx),
        "transcript_preview": tx[:300] + "..." if len(tx) > 300 else tx,
    }

    if tx:
        # Simple chunking: Take up to 5000 chars for now to avoid token limits but provide more context
        content = tx[:5000] 
        print(f"[DEBUG] Analyzing content chunk (5000 chars max). Total length was {len(tx)}")
        title   = info.get("title", "")

        print("[DEBUG] Requesting summary analysis...")
        summary, prov = await _ask(
            SUMMARY_PROMPT.format(title=title, content=content),
            "You are a precise video content analyst.")
        result["analysis"] = summary
        result["provider"] = prov

        print("[DEBUG] Requesting roadmap analysis...")
        roadmap, _ = await _ask(
            ROADMAP_PROMPT.format(title=title, content=content),
            "You extract structured learning paths from content.")
        result["roadmap"] = roadmap
        print("[INFO] Analysis completed successfully.")
    else:
        result["analysis"] = "No transcript available — install yt-dlp and ffmpeg for full analysis."
        result["roadmap"]  = "Unavailable without transcript."
        result["provider"] = "none"
        print("[INFO] Analysis finished with no transcript.")

    result["total_ms"] = round((time.time() - t0) * 1000)
    return result
