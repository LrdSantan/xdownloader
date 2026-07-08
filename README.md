# X (Twitter) Video + Caption Downloader — Backend

## What this does
Given a tweet/X URL, returns JSON with:
- Direct video URL (best available quality)
- Caption / tweet text
- Author name + handle
- Thumbnail

## Files
- `extract.py` — core logic (uses yt-dlp to pull video + metadata)
- `app.py` — FastAPI wrapper exposing `POST /extract`
- `requirements.txt` — dependencies
- `Procfile` — start command for Railway/Render

## Run locally
```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Test it:
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://x.com/username/status/1234567890"}'
```

## Deploy on Railway
1. Push this folder to a GitHub repo
2. On Railway: New Project → Deploy from GitHub repo
3. Railway auto-detects Python + the Procfile
4. Set the port env var (Railway sets `$PORT` automatically)
5. Once deployed, you'll get a public URL like `https://your-app.up.railway.app`

## Deploy on Render
1. New Web Service → connect repo
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Next steps (frontend)
- Simple form: paste URL → POST to `/extract` → render:
  - Caption card (profile pic, name, handle, tweet text) via HTML/CSS or canvas
  - Video preview + download button using the returned `video_url`
- For downloading (not just streaming), you'll want the frontend to fetch the
  video URL through your own backend (proxy the file) rather than directly,
  since X's CDN links can be short-lived/signed and may block cross-origin
  downloads from the browser. A `/download` endpoint that streams the file
  through your server solves this cleanly.

## Known limitations
- Only works on public tweets (no login-walled content)
- X can change their internal API/structure, which may require yt-dlp updates
  (`pip install -U yt-dlp` periodically)
- Video-only tweets — image-only tweets will need a separate code path
  (yt-dlp mainly targets video/gif content)
