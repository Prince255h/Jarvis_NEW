"""Web Search (7.4) and YouTube Video Summarizer / Transcript Fetcher (7.5) for JARVIS."""

import re
import html
import json
import urllib.parse
import xml.etree.ElementTree as ET
import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ==========================================
# 7.4 WEB SEARCH (DuckDuckGo HTML + Instant API)
# ==========================================

def web_search(query: str, max_results: int = 6) -> list[dict]:
    """Search the web using DuckDuckGo HTML endpoint with Instant Answer API fallback."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query cannot be empty.")

    results = []

    # 1. Try DuckDuckGo HTML search
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        body = resp.text

        # Extract result blocks cleanly
        link_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>|<div[^>]*class="result__snippet"[^>]*>(.*?)</div>',
            re.IGNORECASE | re.DOTALL,
        )

        links = link_pattern.findall(body)
        snippets = snippet_pattern.findall(body)

        for idx, (href, raw_title) in enumerate(links[:max_results]):
            # Unwrap DDG redirect URLs if present
            actual_url = href
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs and qs["uddg"]:
                actual_url = qs["uddg"][0]

            title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
            raw_snip = ""
            if idx < len(snippets):
                raw_snip = snippets[idx][0] or snippets[idx][1] or ""
            snippet = html.unescape(re.sub(r"<[^>]+>", "", raw_snip)).strip()

            if title:
                results.append({
                    "title": title,
                    "url": actual_url,
                    "snippet": snippet,
                })
    except Exception:
        pass

    # 2. Fallback to DuckDuckGo Instant Answer JSON API
    if not results:
        try:
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading") or query,
                    "url": data.get("AbstractURL") or "",
                    "snippet": data["AbstractText"],
                })

            for topic in data.get("RelatedTopics", []):
                if len(results) >= max_results:
                    break
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic["Text"].split(" - ")[0][:90],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic["Text"],
                    })
        except Exception:
            pass

    return results


def format_search_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"No web results found for '{query}'."
    lines = [f"Web Search Results for: {query}\n"]
    for idx, item in enumerate(results, 1):
        lines.append(f"{idx}. {item['title']}")
        if item.get("url"):
            lines.append(f"   URL: {item['url']}")
        if item.get("snippet"):
            lines.append(f"   Summary: {item['snippet']}")
        lines.append("")
    return "\n".join(lines).strip()


# ==========================================
# 7.5 YOUTUBE VIDEO METADATA & TRANSCRIPT
# ==========================================

def extract_youtube_video_id(url_or_id: str) -> str:
    text = (url_or_id or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(1)

    raise ValueError("Could not extract a valid YouTube video ID from the provided URL.")


def _parse_caption_response(cap_url: str) -> str:
    """Fetch caption track as JSON3 or XML timedtext and return clean transcript text."""
    # Try JSON3 format first (most reliable)
    sep = "&" if "?" in cap_url else "?"
    try:
        j_resp = requests.get(f"{cap_url}{sep}fmt=json3", headers=HEADERS, timeout=12)
        if j_resp.ok and j_resp.text.strip().startswith("{"):
            payload = j_resp.json()
            segs = []
            for ev in payload.get("events", []):
                for seg in ev.get("segs", []):
                    t = (seg.get("utf8") or "").replace("\n", " ").strip()
                    if t:
                        segs.append(t)
            if segs:
                return " ".join(segs)[:16000]
    except Exception:
        pass

    # Fallback to XML timedtext
    try:
        x_resp = requests.get(cap_url, headers=HEADERS, timeout=12)
        if x_resp.ok and x_resp.text.strip().startswith("<"):
            root = ET.fromstring(x_resp.text)
            segments = [
                html.unescape("".join(el.itertext())).replace("\n", " ").strip()
                for el in root.findall(".//text")
            ]
            transcript = " ".join(s for s in segments if s)
            if transcript:
                return transcript[:16000]
    except Exception:
        pass

    return ""


def _pick_caption_track(tracks: list) -> dict | None:
    if not tracks:
        return None
    for tr in tracks:
        if str(tr.get("languageCode", "")).startswith("en") and tr.get("kind") != "asr":
            return tr
    for tr in tracks:
        if str(tr.get("languageCode", "")).startswith("en"):
            return tr
    return tracks[0]


def fetch_youtube_video_info(url_or_id: str) -> dict:
    """Fetch YouTube title, channel, description, and captions/transcript with Innertube fallback."""
    video_id = extract_youtube_video_id(url_or_id)
    watch_url = f"https://www.youtube.com/watch?v={video_id}"

    info = {
        "video_id": video_id,
        "url": watch_url,
        "title": "Unknown Video",
        "author": "Unknown Channel",
        "description": "",
        "transcript": "",
    }

    # 1. Reliable oEmbed metadata
    try:
        oembed = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": watch_url, "format": "json"},
            headers=HEADERS,
            timeout=10,
        )
        if oembed.ok:
            od = oembed.json()
            info["title"] = od.get("title", info["title"])
            info["author"] = od.get("author_name", info["author"])
    except Exception:
        pass

    # 2. Try YouTube Innertube player API (ANDROID client often returns working caption tracks)
    try:
        it_resp = requests.post(
            "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
            json={
                "context": {
                    "client": {
                        "clientName": "ANDROID",
                        "clientVersion": "19.09.37",
                        "hl": "en",
                        "gl": "US",
                    }
                },
                "videoId": video_id,
            },
            headers={"User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip"},
            timeout=12,
        )
        if it_resp.ok:
            pdata = it_resp.json()
            vd = pdata.get("videoDetails", {})
            if vd.get("title"):
                info["title"] = vd["title"]
            if vd.get("author"):
                info["author"] = vd["author"]
            if vd.get("shortDescription"):
                info["description"] = vd["shortDescription"][:3000]
            tracks = (
                pdata.get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
            chosen = _pick_caption_track(tracks)
            if chosen and chosen.get("baseUrl"):
                info["transcript"] = _parse_caption_response(chosen["baseUrl"])
    except Exception:
        pass

    # 3. Fallback to watch page HTML scraping if description or transcript is still missing
    if not info["description"] or not info["transcript"]:
        try:
            page_resp = requests.get(watch_url, headers=HEADERS, timeout=15)
            page_resp.raise_for_status()
            page_html = page_resp.text

            if not info["description"]:
                desc_match = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', page_html)
                if desc_match:
                    try:
                        info["description"] = json.loads(f'"{desc_match.group(1)}"')[:3000]
                    except Exception:
                        pass

            if not info["transcript"]:
                cap_match = re.search(r'"captionTracks":(\[.*?\])', page_html)
                if cap_match:
                    try:
                        tracks = json.loads(cap_match.group(1))
                        chosen = _pick_caption_track(tracks)
                        if chosen and chosen.get("baseUrl"):
                            info["transcript"] = _parse_caption_response(chosen["baseUrl"])
                    except Exception:
                        pass
        except Exception:
            pass

    return info


def build_youtube_context(info: dict) -> str:
    parts = [
        f"YouTube Title: {info['title']}",
        f"Channel: {info['author']}",
        f"URL: {info['url']}",
    ]
    if info.get("description"):
        parts.append(f"\nDescription:\n{info['description']}")
    if info.get("transcript"):
        parts.append(f"\nTranscript:\n{info['transcript']}")
    else:
        parts.append("\nNote: Video captions/transcript were unavailable; summarize based on metadata and description.")
    return "\n".join(parts)

