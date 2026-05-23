"""
youtube.com/@TEDEd/videos の HTML から最新の TED-Ed 動画一覧を取得する。

YouTube TED-Ed の RSS フィード(/feeds/videos.xml?channel_id=...)は
Made for Kids 設定下で 404 を返すため、このスクレイピング方式を採用する。

使い方:
    python scripts/fetch_ted_ed_videos.py             # 直近24時間以内
    python scripts/fetch_ted_ed_videos.py 168         # 直近7日

仕組み:
1. /@TEDEd/videos の HTML を取得
2. var ytInitialData = {...}; を正規表現で抜き出し JSON パース
3. tabs[Videos].richGridRenderer.contents から各動画の lockupViewModel を取得
4. lockupViewModel.contentId(videoId)、metadata.title、metadata.contentMetadataViewModel
   から title / publishedTimeText / 動画長 / サムネイル等を抽出
5. publishedTimeText("2 days ago" 等)を timedelta に変換し、N 時間以内のみ返却
"""

import json
import re
import sys
import urllib.request
from datetime import timedelta

CHANNEL_URL = "https://www.youtube.com/@TEDEd/videos"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_yt_initial_data(html: str) -> dict:
    m = re.search(r"var ytInitialData\s*=\s*({.+?});\s*</script>", html, re.DOTALL)
    if not m:
        raise ValueError("ytInitialData not found. YouTube may have changed page structure.")
    return json.loads(m.group(1))


_REL_RE = re.compile(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", re.IGNORECASE)
_REL_UNIT = {
    "second": timedelta(seconds=1),
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


def parse_relative_time(text: str):
    """'2 days ago' → timedelta。マッチしない場合は None を返す。"""
    if not text:
        return None
    m = _REL_RE.search(text)
    if not m:
        return None
    return int(m.group(1)) * _REL_UNIT[m.group(2).lower()]


def _extract_video_entry(lockup: dict) -> dict | None:
    video_id = lockup.get("contentId")
    if not video_id or not isinstance(video_id, str):
        return None

    meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
    title = meta.get("title", {}).get("content", "")

    rows = (
        meta.get("metadata", {})
        .get("contentMetadataViewModel", {})
        .get("metadataRows", [])
    )
    view_text = ""
    published_text = ""
    if rows and rows[0].get("metadataParts"):
        parts = rows[0]["metadataParts"]
        if len(parts) >= 1:
            view_text = parts[0].get("text", {}).get("content", "")
        if len(parts) >= 2:
            published_text = parts[1].get("text", {}).get("content", "")

    ci = lockup.get("contentImage", {}).get("thumbnailViewModel", {})
    thumbnail_url = ""
    srcs = ci.get("image", {}).get("sources", [])
    if srcs:
        thumbnail_url = srcs[-1].get("url", "")

    duration_text = ""
    for ov in ci.get("overlays", []):
        if not isinstance(ov, dict):
            continue
        for b in ov.get("thumbnailBottomOverlayViewModel", {}).get("badges", []):
            tv = b.get("thumbnailBadgeViewModel", {})
            if tv.get("text"):
                duration_text = tv["text"]
                break

    return {
        "video_id": video_id,
        "title": title,
        "published_text": published_text,
        "view_text": view_text,
        "duration_text": duration_text,
        "thumbnail_url": thumbnail_url,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def extract_videos(yt_data: dict) -> list[dict]:
    tabs = yt_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
    videos_tab = None
    for t in tabs:
        tr = t.get("tabRenderer") or {}
        if tr.get("title") == "Videos":
            videos_tab = tr
            break
    if not videos_tab:
        raise ValueError("Videos tab not found in ytInitialData")

    grid = videos_tab["content"]["richGridRenderer"]["contents"]
    out: list[dict] = []
    for entry in grid:
        lockup = (
            entry.get("richItemRenderer", {})
            .get("content", {})
            .get("lockupViewModel")
        )
        if not lockup:
            continue
        rec = _extract_video_entry(lockup)
        if rec:
            out.append(rec)
    return out


def filter_recent(videos: list[dict], hours: int) -> list[dict]:
    cutoff = timedelta(hours=hours)
    out = []
    for v in videos:
        delta = parse_relative_time(v["published_text"])
        if delta is not None and delta <= cutoff:
            out.append(v)
    return out


def fetch_ted_ed_videos(hours: int = 24) -> list[dict]:
    html = fetch_html(CHANNEL_URL)
    yt_data = extract_yt_initial_data(html)
    all_videos = extract_videos(yt_data)
    return filter_recent(all_videos, hours)


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    videos = fetch_ted_ed_videos(hours=hours)
    print(f"Found {len(videos)} TED-Ed videos within last {hours}h:\n")
    for v in videos:
        print(f"  [{v['published_text']:<15s}] [{v['duration_text']:<8s}] {v['title']}")
        print(f"    videoId  : {v['video_id']}")
        print(f"    url      : {v['url']}")
        print(f"    thumbnail: {v['thumbnail_url']}")
        print()
