"""
FastAPI backend for X video + caption downloader.

Run locally:
    pip install fastapi uvicorn yt-dlp --break-system-packages
    uvicorn app:app --reload --port 8000

Deploy on Railway/Render:
    - Add a Procfile / start command: uvicorn app:app --host 0.0.0.0 --port $PORT
    - Set Python buildpack, requirements.txt with fastapi, uvicorn, yt-dlp
"""

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


@app.get("/download")
def download(video_url: str, filename: str = "video.mp4"):
    """
    Streams the video through our server so the browser can trigger a real
    download (X's CDN URLs are signed/expiring and often block direct
    cross-origin downloads from the browser).
    """
    if "twimg.com" not in video_url:
        raise HTTPException(status_code=400, detail="Invalid video URL")

    def stream():
        with httpx.stream("GET", video_url, timeout=60) as r:
            for chunk in r.iter_bytes(chunk_size=8192):
                yield chunk

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(stream(), media_type="video/mp4", headers=headers)
