from fastapi import APIRouter, Request
from server.manifest import get_manifest, Manifest

router = APIRouter()

@router.get("/manifest.json")
async def manifest_endpoint(request: Request) -> Manifest:
    manifest = get_manifest()
    manifest.logo = str(request.base_url) + "logo.png"
    return manifest


from typing import Annotated
from fastapi import HTTPException, Path
import asyncio
import re
from streaming.metadata import resolve_imdb_id
from streaming.provider import find_all_matches, extract_streams
from streaming.helpers import generate_stream_title, generate_stream_description, get_stream_filename
from urllib.parse import quote

@router.get("/stream/{type}/{id}.json")
async def stream_endpoint(request: Request, type: Annotated[str, Path(...)], id: Annotated[str, Path(...)]):
    if type not in ["movie", "series"]:
        raise HTTPException(status_code=404, detail="Unsupported type")

    parts = id.split(":")
    imdb_id = parts[0]
    season = 1
    episode = 1
    
    if type == "series" and len(parts) >= 3:
        season = int(parts[1])
        episode = int(parts[2])


    meta = await resolve_imdb_id(request.app.state.http_client, type, imdb_id)
    title = meta.get("name")
    
    if not title:
        return {"streams": []}

    year_match = re.search(r'\d{4}', str(meta.get("releaseInfo", ""))) or re.search(r'\d{4}', str(meta.get("year", "")))
    year = year_match.group(0) if year_match else ""

    matches = await find_all_matches(title, year, is_movie=(type == "movie"))
    
    if not matches:
        return {"streams": []}

    stream_results = await extract_streams(matches, type == "movie", season, episode)
    
    # Sort by highest resolution first
    stream_results.sort(key=lambda x: getattr(x["download"], 'resolution', 0), reverse=True)
    
    streams = []
    seen_urls = set()
    
    for stream_data in stream_results:
        dl = stream_data["download"]
        audio_lang = stream_data["audio_lang"]
        subtitle_langs = stream_data["subtitle_langs"]
        
        url_str = str(dl.url)
        # Deduplicate streams based on the URL path, ignoring query parameters
        base_dl_url = url_str.split('?')[0] if '?' in url_str else url_str
        if base_dl_url in seen_urls:
            continue
        seen_urls.add(base_dl_url)
        
        resolution = getattr(dl, 'resolution', 0)
        size = getattr(dl, 'size', 0)
        
        filename = get_stream_filename(url_str)
        audio_langs_display = [audio_lang] if audio_lang else None
        
        streams.append({
            "name": "MovieBox",
            "title": generate_stream_description(
                resolution,
                size,
                audio_langs=audio_langs_display,
                subtitle_langs=subtitle_langs if subtitle_langs else None,
            ),
            "url": url_str,
            "behaviorHints": {
                "notWebReady": True,
                "filename": filename,
                "proxyHeaders": {
                    "request": {
                        "Referer": "https://fmoviesunblocked.net/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    }
                }
            }
        })

    return {"streams": streams}


