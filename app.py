"""
FastAPI backend for X video + caption downloader.

Run locally:
    pip install fastapi uvicorn yt-dlp --break-system-packages
    uvicorn app:app --reload --port 8000

Deploy on Railway/Render:
    - Add a Procfile / start command: uvicorn app:app --host 0.0.0.0 --port $PORT
    - Set Python buildpack, requirements.txt with fastapi, uvicorn, yt-dlp
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from extract import extract_tweet_media

app = FastAPI(title="X Video + Caption Downloader")

# Allow your frontend (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your actual frontend domain later
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
def extract(payload: ExtractRequest):
    if "x.com" not in payload.url and "twitter.com" not in payload.url:
        raise HTTPException(status_code=400, detail="URL must be an x.com or twitter.com link")

    try:
        data = extract_tweet_media(payload.url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract: {str(e)}")

    if not data.get("video_url"):
        raise HTTPException(status_code=404, detail="No video found in this tweet")

    return data
