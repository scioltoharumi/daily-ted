"""
YouTube公式RSSから直近動画のメタデータを取得するヘルパー

使い方:
    python scripts/fetch_rss.py ted-ed
    python scripts/fetch_rss.py ted-talks
"""

import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request

CHANNELS = {
    "ted-ed": "UCsooa4yRKGN_zEE8iknghZA",
    "ted-talks": "UCAuUUnT6oDeKwE6v1NGQxug",
}

# YouTube RSSのXML名前空間
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_rss(source: str, hours: int = 24) -> list[dict]:
    """
    指定ソースの直近N時間以内に公開された動画メタデータを返す
    
    Returns:
        list of {video_id, title, description, published, thumbnail_url}
    """
    if source not in CHANNELS:
        raise ValueError(f"Unknown source: {source}. Use 'ted-ed' or 'ted-talks'")
    
    channel_id = CHANNELS[source]
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        xml_data = resp.read()
    
    root = ET.fromstring(xml_data)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    results = []
    for entry in root.findall("atom:entry", NS):
        title = entry.find("atom:title", NS).text
        published_str = entry.find("atom:published", NS).text
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        
        if published < cutoff:
            continue
        
        video_id = entry.find("yt:videoId", NS).text
        media_group = entry.find("media:group", NS)
        description = ""
        thumbnail_url = ""
        
        if media_group is not None:
            desc_el = media_group.find("media:description", NS)
            if desc_el is not None and desc_el.text:
                description = desc_el.text
            thumb_el = media_group.find("media:thumbnail", NS)
            if thumb_el is not None:
                thumbnail_url = thumb_el.get("url", "")
        
        results.append({
            "video_id": video_id,
            "title": title,
            "description": description,
            "published": published.isoformat(),
            "thumbnail_url": thumbnail_url,
        })
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_rss.py [ted-ed|ted-talks] [hours]")
        sys.exit(1)
    
    source = sys.argv[1]
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    
    videos = fetch_rss(source, hours=hours)
    print(f"Found {len(videos)} new videos in the last {hours}h:\n")
    for v in videos:
        print(f"  [{v['published']}]")
        print(f"  Title: {v['title']}")
        print(f"  ID: {v['video_id']}")
        print(f"  Thumb: {v['thumbnail_url']}")
        print()
