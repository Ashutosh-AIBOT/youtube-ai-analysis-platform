from dotenv import load_dotenv
import os

# Prefer repo-root `.env` for local dev, while still allowing plain env vars
# (Hugging Face Spaces typically injects env vars instead of mounting a file).
_here = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(_here, "..", ".env"))

# Keep the internal service key consistent across services
API_KEY        = os.getenv("INTERNAL_API_KEY", os.getenv("API_KEY", "mypassword123"))
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
LOCAL_LLM_URL  = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
LOCAL_MODEL    = os.getenv("LOCAL_MODEL", "phi3:mini")
