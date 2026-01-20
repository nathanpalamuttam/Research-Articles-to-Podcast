#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

import boto3
from dotenv import load_dotenv

from arxiv_utils import get_arxiv_info


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EPISODES_JSON = PROJECT_ROOT / "data" / "episodes.json"
OUT_AUDIO = PROJECT_ROOT / "outputs" / "audio"
OUT_TMP = PROJECT_ROOT / "outputs" / "tmp"

KEEP_N_DEFAULT = 30

PODCAST_TITLE = "Research Articles (Private)"
PODCAST_DESCRIPTION = "Automatically generated audio narrations of research papers."
ITUNES_CATEGORY = "Science"
EXPLICIT = False

ARTWORK_KEY = "artwork/podcast-cover.png"
INDEX_KEY = "index.html"

# If you have a local cover you want auto-uploaded if missing:
LOCAL_COVER_PATH = PROJECT_ROOT / "assets" / "podcast-cover.png"


def load_env():
    load_dotenv(PROJECT_ROOT / ".env")


def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=require_env("R2_ENDPOINT"),
        aws_access_key_id=require_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=require_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def public_url_for_key(key: str) -> str:
    base = require_env("R2_PUBLIC_BASE").rstrip("/")
    return f"{base}/{key}"


def upload_bytes(key: str, data: bytes, content_type: Optional[str] = None):
    s3 = r2_client()
    bucket = require_env("R2_BUCKET")
    kwargs = {"Bucket": bucket, "Key": key, "Body": data}
    if content_type:
        kwargs["ContentType"] = content_type
    s3.put_object(**kwargs)


def upload_file(key: str, path: Path, content_type: Optional[str] = None):
    upload_bytes(key, path.read_bytes(), content_type=content_type)


def head_object_exists(key: str) -> bool:
    s3 = r2_client()
    bucket = require_env("R2_BUCKET")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def delete_key(key: str):
    s3 = r2_client()
    bucket = require_env("R2_BUCKET")
    s3.delete_object(Bucket=bucket, Key=key)


def rfc822(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def slugify(s: str, max_len: int = 120) -> str:
    """
    Safe-ish filename/key slug. Keeps it readable.
    """
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)          # drop punctuation
    s = re.sub(r"[\s_-]+", "-", s)          # spaces -> hyphen
    s = s.strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "episode"


def find_mp3_for_title(arxiv_id: str) -> Path:
    # Use the shared utility to get paper info (supports both arXiv and bioRxiv)
    info = get_arxiv_info(arxiv_id)
    title = info['title']

    # Clean title - remove special chars but keep spaces to match new_tts_generator.py
    clean_title = re.sub(r'[^\w\s-]', '', title)
    clean_title = clean_title[:100]

    mp3_path = OUT_AUDIO / f"{clean_title}_podcast.mp3"

    if not mp3_path.exists():
        raise FileNotFoundError(f"Expected MP3 not found: {mp3_path}")

    return mp3_path
    


def ensure_index_html():
    if head_object_exists(INDEX_KEY):
        return
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(PODCAST_TITLE)}</title></head>"
        "<body>"
        f"<h1>{escape(PODCAST_TITLE)}</h1>"
        "<p>Private podcast feed.</p>"
        "</body></html>"
    )
    upload_bytes(INDEX_KEY, html.encode("utf-8"), content_type="text/html; charset=utf-8")


def ensure_artwork():
    if head_object_exists(ARTWORK_KEY):
        return
    if not LOCAL_COVER_PATH.exists():
        raise RuntimeError(
            f"Artwork missing in R2 and local cover not found at {LOCAL_COVER_PATH}. "
            f"Upload your cover to R2 key '{ARTWORK_KEY}' or place it at assets/podcast-cover.png."
        )
    upload_file(ARTWORK_KEY, LOCAL_COVER_PATH, content_type="image/png")


@dataclass
class Episode:
    guid: str
    title: str
    description: str
    pubdate_iso: str
    mp3_key: str
    mp3_length_bytes: int
    episode_page_key: str


def load_episodes() -> list[dict]:
    if not EPISODES_JSON.exists():
        return []
    return json.loads(EPISODES_JSON.read_text(encoding="utf-8"))


def save_episodes(items: list[dict]):
    EPISODES_JSON.parent.mkdir(parents=True, exist_ok=True)
    EPISODES_JSON.write_text(json.dumps(items, indent=2), encoding="utf-8")


def tag_mp3_with_ffmpeg(in_path: Path, out_path: Path, title: str):
    """
    Adds ID3v2.3 tags (helps podcast validators and some players).
    Requires: brew install ffmpeg
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_path),
        "-c", "copy",
        "-id3v2_version", "3",
        "-metadata", f"title={title}",
        "-metadata", f"artist={PODCAST_TITLE}",
        "-metadata", f"album={PODCAST_TITLE}",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def render_episode_html(ep_title: str, mp3_url: str, pubdate: datetime) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{escape(ep_title)}</title></head>
<body>
  <h1>{escape(ep_title)}</h1>
  <p>Published: {escape(rfc822(pubdate))}</p>
  <p><a href="{escape(mp3_url)}">Play / download MP3</a></p>
</body></html>
"""

PODCAST_AUTHOR = "Research Articles Podcast"
PODCAST_OWNER_EMAIL = "npalamuttam04@gmail.com"


def render_feed_xml(episodes: list[dict]) -> str:
    channel_link = public_url_for_key(INDEX_KEY)
    artwork_url = public_url_for_key(ARTWORK_KEY)
    itunes_explicit = "true" if EXPLICIT else "false"

    items_xml = []
    base = require_env("R2_PUBLIC_BASE").rstrip("/")

    for e in episodes:
        dt = datetime.fromisoformat(e["pubdate_iso"].replace("Z", "+00:00"))
        mp3_url = f"{base}/{e['mp3_key']}"
        page_url = f"{base}/{e['episode_page_key']}"

        items_xml.append(
            f"""    <item>
      <title>{escape(e['title'])}</title>
      <description>{escape(e['description'])}</description>
      <link>{escape(page_url)}</link>
      <enclosure url="{escape(mp3_url)}" length="{int(e['mp3_length_bytes'])}" type="audio/mpeg"/>
      <guid>{escape(e['guid'])}</guid>
      <pubDate>{escape(rfc822(dt))}</pubDate>
    </item>"""
        )

    items_str = "\n".join(items_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <description>{escape(PODCAST_DESCRIPTION)}</description>
    <language>en-us</language>
    <link>{escape(channel_link)}</link>

    <!-- Spotify / Apple ownership metadata -->
    <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
    <itunes:owner>
      <itunes:name>{escape(PODCAST_AUTHOR)}</itunes:name>
      <itunes:email>{escape(PODCAST_OWNER_EMAIL)}</itunes:email>
    </itunes:owner>

    <itunes:explicit>{itunes_explicit}</itunes:explicit>
    <itunes:category text="{escape(ITUNES_CATEGORY)}"/>
    <itunes:image href="{escape(artwork_url)}"/>

{items_str}
  </channel>
</rss>
"""



def main():
    load_env()

    parser = argparse.ArgumentParser()
    parser.add_argument("--arxiv", required=True, help="arXiv id like 2412.14689")
    parser.add_argument("--keep", type=int, default=KEEP_N_DEFAULT, help="Keep last N episodes (R2 + feed)")
    parser.add_argument("--description", default="Audio narration of the research paper.", help="Episode description (override)")
    parser.add_argument("--no_ffmpeg_tag", action="store_true", help="Skip ffmpeg ID3 tagging")
    args = parser.parse_args()

    OUT_TMP.mkdir(parents=True, exist_ok=True)

    info = get_arxiv_info(args.arxiv)
    title = info["title"]
    description = args.description

    # 1) locate MP3 produced by your pipeline
    mp3_in = find_mp3_for_title(args.arxiv)

    # 2) optionally tag MP3 for compatibility
    mp3_to_upload = mp3_in
    if not args.no_ffmpeg_tag:
        tagged = OUT_TMP / f"{slugify(title)}_tagged.mp3"
        tag_mp3_with_ffmpeg(mp3_in, tagged, title=title)
        mp3_to_upload = tagged

    mp3_len = mp3_to_upload.stat().st_size

    # 3) ensure shared assets exist
    ensure_index_html()
    ensure_artwork()

    # 4) choose stable episode slug + keys
    #    Use slugified title for nice URLs, but GUID uses arxiv id + timestamp to avoid collisions if you re-run.
    slug = slugify(title)
    now = datetime.now(timezone.utc)
    guid = f"{args.arxiv}-{now.strftime('%Y%m%d%H%M%S')}"

    mp3_key = f"podcasts/{slug}.mp3"
    episode_page_key = f"episodes/{slug}.html"

    # 5) upload MP3
    upload_file(mp3_key, mp3_to_upload, content_type="audio/mpeg")
    mp3_url = public_url_for_key(mp3_key)

    # 6) upload episode HTML (HTML required by some validators)
    ep_html = render_episode_html(title, mp3_url, now)
    upload_bytes(episode_page_key, ep_html.encode("utf-8"), content_type="text/html; charset=utf-8")

    # 7) update episodes.json
    items = load_episodes()
    items.append({
        "guid": guid,
        "title": title,
        "description": description,
        "pubdate_iso": now.isoformat().replace("+00:00", "Z"),
        "mp3_key": mp3_key,
        "mp3_length_bytes": mp3_len,
        "episode_page_key": episode_page_key,
    })
    items.sort(key=lambda x: x["pubdate_iso"], reverse=True)
    save_episodes(items)

    # 8) render + upload feed.xml (keeping last N)
    kept = items[: args.keep]
    feed_xml = render_feed_xml(kept)
    upload_bytes("feed.xml", feed_xml.encode("utf-8"), content_type="text/xml; charset=utf-8")

    # 9) cleanup old episodes in R2 beyond keep
    for old in items[args.keep:]:
        delete_key(old["mp3_key"])
        delete_key(old["episode_page_key"])

    # also update local episodes.json to match kept list (optional; keeps your DB small)
    save_episodes(items[: args.keep])

    print("Published episode:", title)
    print("MP3:", mp3_url)
    print("Episode page:", public_url_for_key(episode_page_key))
    print("Feed:", public_url_for_key("feed.xml"))


if __name__ == "__main__":
    main()
