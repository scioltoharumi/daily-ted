"""
ted.com GraphQL の `translation` を使って公式トランスクリプトを段落・cue 単位で取得する。

D-019 採用版。YouTube 字幕(youtube-transcript-api 経由)は公式 lesson 本文と
語句・句読点・行分割が乖離する事例が多く、かつクラウド IP が YouTube に
遮断される問題があったため、ted.com の `translation` クエリに統一。

使い方:
    python scripts/fetch_ted_transcript.py <ted_video_id> [lang]
    例: python scripts/fetch_ted_transcript.py 177595
        python scripts/fetch_ted_transcript.py 177595 en

返却(JSON):
    {
      "video_id": "...",
      "language": "en",
      "duration_sec": <end_of_last_cue_in_seconds>,
      "paragraphs": [
        {
          "start_sec": float,    # 段落最初の cue の startTime / 1000
          "cues": [
            { "start_sec": float, "end_sec": float, "duration_sec": float, "text": str },
            ...
          ]
        },
        ...
      ]
    }

snippets 互換が必要な場合は `--flat` を付けると全 cue をフラット配列で出す:
    [{ "start_sec": float, "duration_sec": float, "text": str }, ...]
"""

import argparse
import json
import sys
import urllib.request

GRAPHQL_URL = "https://www.ted.com/graphql"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

QUERY = """
query Transcript($vid: ID!, $lang: String!) {
  translation(language: $lang, videoId: $vid) {
    paragraphs {
      cues {
        startTime
        endTime
        text
      }
    }
  }
}
"""


def graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def fetch_transcript(ted_video_id: str, language: str = "en") -> dict:
    data = graphql(QUERY, {"vid": str(ted_video_id), "lang": language})
    tr = data.get("translation")
    if not tr:
        raise RuntimeError(f"No transcript for videoId={ted_video_id} language={language}")

    paragraphs_out = []
    last_end_ms = 0
    for p in tr["paragraphs"]:
        cues_out = []
        for c in p["cues"]:
            start_ms = c["startTime"]
            end_ms = c["endTime"]
            last_end_ms = max(last_end_ms, end_ms)
            cues_out.append({
                "start_sec": round(start_ms / 1000.0, 3),
                "end_sec": round(end_ms / 1000.0, 3),
                "duration_sec": round((end_ms - start_ms) / 1000.0, 3),
                "text": c["text"],
            })
        if cues_out:
            paragraphs_out.append({
                "start_sec": cues_out[0]["start_sec"],
                "cues": cues_out,
            })

    return {
        "video_id": str(ted_video_id),
        "language": language,
        "duration_sec": round(last_end_ms / 1000.0, 3),
        "paragraphs": paragraphs_out,
    }


def to_flat_snippets(transcript: dict) -> list[dict]:
    """youtube-transcript-api 互換のフラット snippets 形式に変換。"""
    flat = []
    for p in transcript["paragraphs"]:
        for c in p["cues"]:
            flat.append({
                "start_sec": c["start_sec"],
                "duration_sec": c["duration_sec"],
                "text": c["text"],
            })
    return flat


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ted_video_id", help="ted.com の数値 video id (例: 177595)")
    p.add_argument("language", nargs="?", default="en")
    p.add_argument("--flat", action="store_true", help="フラット snippets 配列で出す")
    p.add_argument("--summary", action="store_true", help="人間可読サマリのみ表示")
    args = p.parse_args()

    tr = fetch_transcript(args.ted_video_id, args.language)

    if args.summary:
        total_cues = sum(len(p["cues"]) for p in tr["paragraphs"])
        total_chars = sum(len(c["text"]) for p in tr["paragraphs"] for c in p["cues"])
        print(f"video_id={tr['video_id']} lang={tr['language']}")
        print(f"paragraphs={len(tr['paragraphs'])} cues={total_cues} chars={total_chars} duration={tr['duration_sec']:.1f}s")
        print()
        for p in tr["paragraphs"][:2]:
            print("---")
            for c in p["cues"][:3]:
                print(f"  [{c['start_sec']:>6.2f}s +{c['duration_sec']:>4.2f}s] {c['text']}")
        return

    out = to_flat_snippets(tr) if args.flat else tr
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
