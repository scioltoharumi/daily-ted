"""配信記録(data/index.json + data/talks/)の整合性を監査する。

D-020 (2026-08-03) の再発防止策。日次バッチが「起動しなかった日」と
「起動して新作が無かった日」は区別できないまま `skipped_dates` に
まとめられており、実測で以下の歪みが生じていた:

- 2026-04-21〜2026-08-03 の 105 日中、`daily:` commit があるのは 36 日のみ
- `skipped_dates` 66 日のうち 38 日は commit が無い(後日 backfill)
- うち 7 日は **未配信の在庫があるのに "no new upload" と記録**していた
  (恒久欠落は 0 件だったが配信が 1〜4 日遅延した)

本スクリプトは以下を検出して非ゼロ終了する:

1. pending      : 未配信のまま残っている TED-Ed 動画
2. false-skip   : 在庫があったのに skip 記録された日
3. uncovered    : delivered でも skipped でもない日(記録の穴)
4. inconsistent : index.json と data/talks/*.json の不一致

使い方:
    python scripts/audit_delivery.py              # 全項目(要ネットワーク)
    python scripts/audit_delivery.py --offline    # ローカル整合性のみ
    python scripts/audit_delivery.py --json       # 機械可読
"""

import argparse
import glob
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
BATCH_HOUR_JST = 6  # cron 0 21 * * * UTC = JST 06:00

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_local(repo_root: str) -> dict:
    with open(os.path.join(repo_root, "data", "index.json"), encoding="utf-8") as f:
        index = json.load(f)
    talks = {}
    for path in glob.glob(os.path.join(repo_root, "data", "talks", "*.json")):
        with open(path, encoding="utf-8") as f:
            t = json.load(f)
        talks[os.path.basename(path)[:-5]] = t
    return {"index": index, "talks": talks}


def first_deliverable_date(published_at: str) -> str:
    """publishedAt(UTC ISO) を、最初にバッチが拾える JST 配信日に変換する。"""
    p = datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(JST)
    d = p.date() if p.hour < BATCH_HOUR_JST else p.date() + timedelta(days=1)
    return d.isoformat()


def check_local(local: dict) -> list[dict]:
    """index.json と talks/*.json の整合性(ネットワーク不要)。"""
    problems = []
    index, talks = local["index"], local["talks"]
    summaries = {t["date"]: t for t in index.get("talks", [])}
    skipped = set(index.get("skipped_dates", []))

    for d in sorted(set(summaries) - set(talks)):
        problems.append({"kind": "inconsistent", "date": d,
                         "detail": "index.json に entry があるが data/talks/%s.json が無い" % d})
    for d in sorted(set(talks) - set(summaries)):
        problems.append({"kind": "inconsistent", "date": d,
                         "detail": "data/talks/%s.json があるが index.json に entry が無い" % d})
    for d in sorted(set(summaries) & skipped):
        problems.append({"kind": "inconsistent", "date": d,
                         "detail": "配信済みなのに skipped_dates にも入っている"})

    for d, t in sorted(talks.items()):
        s = summaries.get(d)
        if not s:
            continue
        for key in ("title", "speaker", "duration_sec", "primary_topic", "difficulty"):
            if s.get(key) != t.get(key):
                problems.append({"kind": "inconsistent", "date": d,
                                 "detail": "index.json と talk の %s が不一致: %r != %r"
                                           % (key, s.get(key), t.get(key))})

    # 記録の穴:運用開始〜最終記録日で delivered/skipped どちらでもない日
    all_dates = sorted(set(summaries) | skipped)
    if all_dates:
        start = date.fromisoformat(all_dates[0])
        end = date.fromisoformat(all_dates[-1])
        cur = start
        while cur <= end:
            s = cur.isoformat()
            if s not in summaries and s not in skipped:
                problems.append({"kind": "uncovered", "date": s,
                                 "detail": "delivered でも skipped でもない(記録の穴)"})
            cur += timedelta(days=1)
    return problems


def check_remote(local: dict, repo_root: str) -> list[dict]:
    """ted.com のカタログと突き合わせ、在庫漏れ・誤 skip を検出する。"""
    sys.path.insert(0, os.path.join(repo_root, "scripts"))
    from fetch_ted_ed_talks import fetch_catalog, load_delivered  # noqa: E402

    problems = []
    index, talks = local["index"], local["talks"]
    ids, titles, floor = load_delivered(repo_root)
    catalog = [n for n in fetch_catalog(limit=80)
               if not floor or n["publishedAt"] >= floor]

    delivered_on = {}
    for d, t in talks.items():
        if t.get("video_id") is not None:
            delivered_on[str(t["video_id"])] = d
        if t.get("title"):
            delivered_on.setdefault(t["title"].strip().lower(), d)

    def delivered_date(n):
        return delivered_on.get(str(n["id"])) or delivered_on.get((n.get("title") or "").strip().lower())

    for n in sorted(catalog, key=lambda x: x["publishedAt"]):
        if not delivered_date(n):
            problems.append({"kind": "pending", "date": n["publishedAt"][:10],
                             "detail": "未配信: video_id=%s %s" % (n["id"], n["title"])})

    for d in sorted(set(index.get("skipped_dates", []))):
        stuck = []
        for n in catalog:
            if first_deliverable_date(n["publishedAt"]) > d:
                continue
            dd = delivered_date(n)
            if dd is None or dd > d:
                stuck.append("video_id=%s %s" % (n["id"], n["title"][:45]))
        if stuck:
            problems.append({"kind": "false-skip", "date": d,
                             "detail": "在庫があるのに skip 記録: " + "; ".join(stuck)})
    return problems


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=REPO_ROOT)
    p.add_argument("--offline", action="store_true", help="ted.com へアクセスせずローカル整合性のみ検査")
    p.add_argument("--json", action="store_true", help="JSON で結果を出力")
    p.add_argument("--since", metavar="YYYY-MM-DD",
                   help="この日付以降のみ報告する。D-020 以前の既知の歪み"
                        "(false-skip 7件 / uncovered 15件)を除いて再発だけを見るのに使う。")
    args = p.parse_args()

    local = load_local(args.repo_root)
    problems = check_local(local)
    if not args.offline:
        try:
            problems += check_remote(local, args.repo_root)
        except Exception as e:  # ネットワーク断でローカル検査結果まで失わない
            problems.append({"kind": "error", "date": "", "detail": "remote check failed: %s" % e})

    if args.since:
        problems = [p_ for p_ in problems if p_["kind"] == "error" or p_["date"] >= args.since]

    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        by_kind = {}
        for p_ in problems:
            by_kind.setdefault(p_["kind"], []).append(p_)
        if not problems:
            print("OK: 配信記録に問題は見つかりませんでした")
        for kind in ("pending", "false-skip", "uncovered", "inconsistent", "error"):
            items = by_kind.get(kind)
            if not items:
                continue
            print(f"\n[{kind}] {len(items)} 件")
            for it in items:
                print(f"  {it['date']}  {it['detail']}")

    blocking = [p_ for p_ in problems if p_["kind"] in ("pending", "false-skip", "inconsistent")]
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
