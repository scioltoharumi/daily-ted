"""
ted.com GraphQL API から TED-Ed の最新 talks 一覧を取得する。

D-019 採用版(2026-05-23):YouTube 直結フロー(D-016)から ted.com 公式 API に
切替。YouTube 経由は (a) クラウド IP の watch ページ遮断、(b) "X days ago" の
粗い相対時刻による恒久欠落、(c) 字幕が公式トランスクリプトと乖離、という
3 つの欠点を抱えていた。ted.com は topic="ted+ed" で 1000+ 件の TED-Ed
カタログを正確な publishedAt 付きで返す。

使い方:
    python scripts/fetch_ted_ed_talks.py --pending     # ★推奨: 未配信の在庫(古い順)
    python scripts/fetch_ted_ed_talks.py              # 直近24時間
    python scripts/fetch_ted_ed_talks.py 72           # 直近72時間
    python scripts/fetch_ted_ed_talks.py --since 2026-05-18  # 指定日以降
    python scripts/fetch_ted_ed_talks.py --first 30          # 取得件数の上限

返却 JSON は stdout に1行で出る(配列)。

## --pending を使う理由 (D-020 / 2026-08-03)

`--since <talks[0].published_at>` 方式は「時間窓」でしか新着を見ないため、
**バッチが1日でも起動しなかった日の在庫を取りこぼす**。実測では
2026-04-21〜2026-08-03 の 105 日中 69 日で daily commit が存在せず、
うち 7 日は「未配信の動画が在庫にあるのに skip 扱い」になっていた
(配信自体は後日行われたので恒久欠落は 0 件だったが、1〜4 日遅延した)。

`--pending` は時間窓ではなく **`data/talks/*.json` の配信済み集合との差分**
で判定するため、何日バッチが落ちても次回起動時に自動で追いつく(self-healing)。
"""

import argparse
import glob
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

GRAPHQL_URL = "https://www.ted.com/graphql"
TED_ED_TOPIC_SLUG = "ted+ed"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

LIST_QUERY = """
query TedEdList($slug: String!, $first: Int!, $after: String) {
  topic(slug: $slug) {
    id
    name
    videos(first: $first, after: $after) {
      pageInfo {
        hasNextPage
        endCursor
      }
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

# ted.com は first に 20 を超える値を渡しても 1 ページ 20 件で打ち切る。
# ページングしないと「直近20本」より前が永久に見えないため、必ず after で辿る。
PAGE_SIZE = 20


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


def _normalize(n: dict) -> dict:
    thumb = ""
    for img in n.get("primaryImageSet") or []:
        if img.get("aspectRatioName") == "16x9":
            thumb = img.get("url", "")
            break
    if not thumb and n.get("primaryImageSet"):
        thumb = n["primaryImageSet"][0].get("url", "")
    return {
        "ted_video_id": n["id"],
        "slug": n["slug"],
        "title": n["title"],
        "speaker": (n.get("presenterDisplayName") or "").strip() or "TED-Ed",
        "duration_sec": n.get("duration") or 0,
        "published_at": n["publishedAt"],
        "canonical_url": n["canonicalUrl"],
        "description": n.get("description") or "",
        "thumbnail_url": thumb,
    }


def fetch_catalog(limit: int = 60) -> list[dict]:
    """topic.videos を after カーソルで辿り、最大 limit 件のノードを返す。

    ted.com の既定順は「概ね publishedAt 降順」だが厳密ではない
    (実測で 2026-04-16 が 2026-04-14 の後に来るケースを確認)。
    そのため呼び出し側は必ず publishedAt で自前フィルタ/ソートすること。
    """
    nodes, seen, after = [], set(), None
    while len(nodes) < limit:
        data = graphql(LIST_QUERY, {"slug": TED_ED_TOPIC_SLUG, "first": PAGE_SIZE, "after": after})
        topic = data.get("topic")
        if not topic:
            raise RuntimeError(f"topic '{TED_ED_TOPIC_SLUG}' not found")
        videos = topic["videos"]
        for n in videos["nodes"]:
            if n["id"] not in seen:
                seen.add(n["id"])
                nodes.append(n)
        page = videos.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
        if not after:
            break
    return nodes[:limit]


def load_delivered(repo_root: str) -> tuple[set[str], set[str], str | None]:
    """配信済みの (ted_video_id 集合, 正規化タイトル集合, 最古 published_at) を返す。

    D-019 より前に生成された talk は `video_id` が YouTube ID のため
    ted.com の数値 id と突き合わせられない。タイトル一致を副次キーに使う。

    最古 published_at は `--pending` の下限(運用開始前の旧作を在庫扱いしない
    ための floor)として使う。
    """
    ids, titles, published = set(), set(), []
    for path in glob.glob(os.path.join(repo_root, "data", "talks", "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                talk = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if talk.get("video_id") is not None:
            ids.add(str(talk["video_id"]))
        if talk.get("title"):
            titles.add(talk["title"].strip().lower())
        if talk.get("published_at"):
            published.append(talk["published_at"])
    return ids, titles, (min(published) if published else None)


def fetch_pending(repo_root: str, limit: int = 60, since_iso: str | None = None) -> list[dict]:
    """未配信の TED-Ed 動画を publishedAt 昇順(古い順)で返す。

    時間窓を使わないため、バッチが何日停止していても次回起動時に
    在庫を自動で拾い直せる(self-healing)。

    `since_iso` 未指定時は「配信済み talk の最古 published_at」を下限とする。
    これを入れないと運用開始(2026-04-21)より前の TED-Ed カタログ全体が
    未配信として返ってしまう。
    """
    ids, titles, floor = load_delivered(repo_root)
    floor = since_iso or floor
    out = []
    for n in fetch_catalog(limit=limit):
        if str(n["id"]) in ids:
            continue
        if (n.get("title") or "").strip().lower() in titles:
            continue
        if floor and n["publishedAt"] < floor:
            continue
        out.append(_normalize(n))
    out.sort(key=lambda t: t["published_at"])
    return out


def fetch_recent_ted_ed(hours: int | None = None, since_iso: str | None = None, first: int = 30) -> list[dict]:
    nodes = fetch_catalog(limit=max(first, PAGE_SIZE))

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
        out.append(_normalize(n))
    out.sort(key=lambda t: t["published_at"], reverse=True)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("hours", nargs="?", type=int, default=24,
                   help="新着判定の時間窓(時間)。--since 指定時は無視。デフォルト24h。")
    p.add_argument("--since", help="ISO 8601 日時。これ以降に publish された talk を返す。")
    p.add_argument("--first", type=int, default=30, help="GraphQL で取得する最大件数(デフォルト30)。")
    p.add_argument("--json", action="store_true", help="JSON 配列を stdout に出す(機械可読)。")
    p.add_argument("--pending", action="store_true",
                   help="未配信の動画のみを古い順で返す(推奨。時間窓に依存せず取りこぼさない)。")
    p.add_argument("--repo-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   help="data/talks/*.json を探すリポジトリ root。--pending 時に使用。")
    args = p.parse_args()

    if args.pending:
        talks = fetch_pending(args.repo_root, limit=max(args.first, 60), since_iso=args.since)
        scope = "pending (undelivered, oldest first)"
    elif args.since:
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
