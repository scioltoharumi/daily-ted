"""
YouTube 動画 ID から字幕(transcript)を取得する。

ted.com 経由のスクレイピングは、TED-Ed の最新動画が ted.com に掲載されない
ケースが多いため廃止。動画字幕は YouTube から youtube-transcript-api 経由で取得する。

依存: pip install youtube-transcript-api

使い方:
    python scripts/fetch_youtube_transcript.py <video_id> [lang_csv]
    例: python scripts/fetch_youtube_transcript.py 4UJTtk_2ly0
        python scripts/fetch_youtube_transcript.py 4UJTtk_2ly0 en

返却データ構造(snippets):
    [{ "start_sec": float, "duration_sec": float, "text": str }, ...]
"""

import json
import sys

from youtube_transcript_api import YouTubeTranscriptApi


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> list[dict]:
    """指定動画の英語字幕(優先順位は languages の順)を取得して snippets に変換する。"""
    languages = languages or ["en"]
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)
    return [
        {
            "start_sec": float(s.start),
            "duration_sec": float(s.duration),
            "text": s.text,
        }
        for s in fetched
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_youtube_transcript.py <video_id> [lang_csv]")
        print("Example: python fetch_youtube_transcript.py 4UJTtk_2ly0")
        sys.exit(1)

    video_id = sys.argv[1]
    languages = sys.argv[2].split(",") if len(sys.argv) > 2 else ["en"]

    snippets = fetch_transcript(video_id, languages)
    total_chars = sum(len(s["text"]) for s in snippets)
    duration = (snippets[-1]["start_sec"] + snippets[-1]["duration_sec"]) if snippets else 0.0

    print(f"Fetched {len(snippets)} snippets for {video_id}")
    print(f"Total characters: {total_chars}")
    print(f"Estimated duration: {duration:.1f}s")
    print()
    print("--- first 5 snippets ---")
    for s in snippets[:5]:
        print(f"  [{s['start_sec']:>6.1f}s +{s['duration_sec']:>4.1f}s] {s['text']}")
    print()
    print("--- last 3 snippets ---")
    for s in snippets[-3:]:
        print(f"  [{s['start_sec']:>6.1f}s +{s['duration_sec']:>4.1f}s] {s['text']}")
