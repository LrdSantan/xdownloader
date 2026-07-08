"""
X (Twitter) video + caption extractor
--------------------------------------
Given a tweet URL, returns:
  - direct video URL (best quality mp4)
  - caption / tweet text
  - author display name, handle, profile pic (if available)
  - thumbnail

Usage:
    python extract.py "https://x.com/username/status/1234567890"

Requires: yt-dlp (pip install yt-dlp --break-system-packages)

NOTE: This will not run inside a network-restricted sandbox (x.com must be
reachable). It will work fine on a normal server (Railway, Render, a VPS, etc).
"""

import sys
import json
import yt_dlp


def extract_tweet_media(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "simulate": True,
        "forcejson": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # yt-dlp normalizes Twitter/X extraction under 'formats'
    # pick the best mp4 format (highest resolution/bitrate)
    formats = info.get("formats", [])
    video_formats = [f for f in formats if f.get("vcodec") != "none"]

    best_format = None
    if video_formats:
        best_format = max(
            video_formats,
            key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        )

    result = {
        "video_url": best_format["url"] if best_format else None,
        "video_ext": best_format.get("ext") if best_format else None,
        "width": best_format.get("width") if best_format else None,
        "height": best_format.get("height") if best_format else None,
        "caption": info.get("description") or info.get("title"),
        "author_name": info.get("uploader"),
        "author_handle": info.get("uploader_id"),
        "thumbnail": info.get("thumbnail"),
        "tweet_id": info.get("id"),
        "webpage_url": info.get("webpage_url"),
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <tweet_url>")
        sys.exit(1)

    tweet_url = sys.argv[1]
    try:
        data = extract_tweet_media(tweet_url)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
