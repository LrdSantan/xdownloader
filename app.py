"""
FastAPI backend for X video + caption downloader.

Run locally:
    pip install fastapi uvicorn yt-dlp --break-system-packages
    uvicorn app:app --reload --port 8000

Deploy on Railway/Render:
    - Add a Procfile / start command: uvicorn app:app --host 0.0.0.0 --port $PORT
    - Set Python buildpack, requirements.txt with fastapi, uvicorn, yt-dlp
"""

import os
import shutil
import subprocess
import tempfile

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from extract import extract_tweet_media
from caption_banner import render_caption_banner

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


class CaptionedDownloadRequest(BaseModel):
    video_url: str
    author_name: str = ""
    author_handle: str = ""
    caption: str = ""
    filename: str = "clip.mp4"


@app.post("/download-with-caption")
def download_with_caption(payload: CaptionedDownloadRequest):
    """
    Downloads the source video, renders a caption banner matching its width,
    stacks the banner above the video with ffmpeg, and streams back a single
    combined mp4 (video + caption baked in, like the original screenshot).
    """
    if "twimg.com" not in payload.video_url:
        raise HTTPException(status_code=400, detail="Invalid video URL")

    work_dir = tempfile.mkdtemp(prefix="xdl_")
    input_path = os.path.join(work_dir, "input.mp4")
    banner_path = os.path.join(work_dir, "banner.png")
    output_path = os.path.join(work_dir, "output.mp4")

    try:
        # 1. Download source video to disk
        with httpx.stream("GET", payload.video_url, timeout=60) as r:
            with open(input_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        # 2. Get video width via ffprobe
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width", "-of", "csv=p=0", input_path,
            ],
            capture_output=True, text=True,
        )
        try:
            video_width = int(probe.stdout.strip())
        except ValueError:
            video_width = 720

        # 3. Render the caption banner at matching width
        banner = render_caption_banner(
            width=video_width,
            author_name=payload.author_name,
            author_handle=payload.author_handle,
            caption=payload.caption,
        )
        banner.save(banner_path)

        # 4. Stack banner above video with ffmpeg
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-loop", "1", "-i", banner_path,
                "-i", input_path,
                "-filter_complex",
                f"[1:v]scale={video_width}:-2[v];[0:v][v]vstack=inputs=2[out]",
                "-map", "[out]", "-map", "1:a?",
                "-c:v", "libx264", "-crf", "26", "-preset", "veryfast",
                "-c:a", "aac", "-shortest",
                output_path,
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"ffmpeg failed (code {result.returncode}): {result.stderr[-2500:]}")

        def stream_and_cleanup():
            with open(output_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
            shutil.rmtree(work_dir, ignore_errors=True)

        headers = {"Content-Disposition": f'attachment; filename="{payload.filename}"'}
        return StreamingResponse(stream_and_cleanup(), media_type="video/mp4", headers=headers)

    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))
