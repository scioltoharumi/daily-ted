"""
ted.com GraphQL API から TED-Ed の最新 talks 一覧を取得する。

D-019 採用版(2026-05-23):YouTube 直結フロー(D-016)から ted.com 公式 API に
切替。YouTube 経由は (a) クラウド IP の watch ページ遮断、(b) "X days ago" の
粗い相対時刻による恒久欠落、(c) 字幕が公式トランスクリプトと乖離、という
3 つの欠点を抱えていた。ted.com は topic="ted+ed" で 1000+ 件の TED-Ed
カタログを正確な publishedAt 付きで返す。

使い方:
    python scripts/fetch_ted_ed_talks.py              # 直近24時間
    python scripts/fetch_ted_ed_talks.py 72           # 直近72時間
    python scripts/fetch_ted_ed_talks.py --since 2026-05-18  # 指定日以降
    python scripts/fetch_ted_ed_talks.py --first 30          # 取得件数の上限

返却 JSON は stdout に1行で出る(配列)。スクリプト本体は GraphQL を1回
叩くだけ。
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

GRAPHQL_URL = "https://www.ted.com/graphql"
TED_ED_TOPIC_SLUG = "ted+ed"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

LIST_QUERY = """
query TedEdList($slug: String!, $first: Int!) {
  topic(slug: $slug) {
    id
    name
    videos(first: $first) {
      nodes {
        id
        slug
        title
        presenterDisplayName
        duration
        publishedAt
        canonicalUrl
        description
        primaryImageSet {
          url
          aspectRatioName
        }
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


def fetch_recent_ted_ed(hours: int | None = None, since_iso: str | None = None, first: int = 30) -> list[dict]:
    data = graphql(LIST_QUERY, {"slug": TED_ED_TOPIC_SLUG, "first": first})
    topic = data.get("topic")
    if not topic:
        raise RuntimeError(f"topic '{TED_ED_TOPIC_SLUG}' not found")
    nodes = topic["videos"]["nodes"]

    if since_iso:
        cutoff = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
    elif hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    else:
        cutoff = None

    out = []
    for n in nodes:
        published = datetime.fromisoformat(n["publishedAt"].replace("Z", "+00:00"))
        if cutoff is not None and published < cutoff:
            continue
        thumb = ""
        for img in n.get("primaryImageSet") or []:
            if img.get("aspectRatioName") == "16x9":
                thumb = img.get("url", "")
                break
        if not thumb and n.get("primaryImageSet"):
            thumb = n["primaryImageSet"][0].get("url", "")
        out.append({
            "ted_video_id": n["id"],
            "slug": n["slug"],
            "title": n["title"],
            "speaker": (n.get("presenterDisplayName") or "").strip() or "TED-Ed",
            "duration_sec": n.get("duration") or 0,
            "published_at": n["publishedAt"],
            "canonical_url": n["canonicalUrl"],
            "description": n.get("description") or "",
            "thumbnail_url": thumb,
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("hours", nargs="?", type=int, default=24,
                   help="新着判定の時間窓(時間)。--since 指定時は無視。デフォルト24h。")
    p.add_argument("--since", help="ISO 8601 日時。これ以降に publish された talk を返す。")
    p.add_argument("--first", type=int, default=30, help="GraphQL で取得する最大件数(デフォルト30)。")
    p.add_argument("--json", action="store_true", help="JSON 配列を stdout に出す(機械可読)。")
    args = p.parse_args()

    if args.since:
        talks = fetch_recent_ted_ed(since_iso=args.since, first=args.first)
        scope = f"since {args.since}"
    else:
        talks = fetch_recent_ted_ed(hours=args.hours, first=args.first)
        scope = f"last {args.hours}h"

    if args.json:
        print(json.dumps(talks, ensure_ascii=False))
        return

    print(f"Found {len(talks)} TED-Ed talks ({scope}):\n", file=sys.stderr)
    for t in talks:
        print(f"  [{t['published_at'][:10]}] [{t['duration_sec']:>4d}s] {t['title']}", file=sys.stderr)
        print(f"    ted_video_id : {t['ted_video_id']}", file=sys.stderr)
        print(f"    slug         : {t['slug']}", file=sys.stderr)
        print(f"    speaker      : {t['speaker']}", file=sys.stderr)
        print(f"    canonical_url: {t['canonical_url']}", file=sys.stderr)
        print(file=sys.stderr)


if __name__ == "__main__":
    main()
