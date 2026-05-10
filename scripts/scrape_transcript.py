"""
ted.com/talks/{slug} からトランスクリプトを抽出するヘルパー

使い方:
    python scripts/scrape_transcript.py ted_ed_the_fascinating_reason_you_loved_peek_a_boo

仕組み:
1. ted.com/talks/{slug} のHTMLをfetch
2. <script> タグ内の q("talkPage.init", {...}) JSONを正規表現で抽出
3. JSONをパースし、transcript_paragraphs等の構造を返す

注意点:
- TED.comのHTML構造は時折変わる。失敗時はHTML全体を確認すること
- レート制限に注意(1日数十回までなら問題ない見込み)
"""

import json
import re
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError


def fetch_html(slug: str) -> str:
    url = f"https://www.ted.com/talks/{slug}"
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_talk_data(html: str) -> dict:
    """
    HTMLから q("talkPage.init", {...}) のJSONを抽出
    """
    # 正規表現は貪欲にしないように注意
    pattern = r'q\(\s*"talkPage\.init"\s*,\s*({.+?})\s*\)\s*;'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        # 別パターンも試す
        pattern2 = r'"talkPage\.init"\s*,\s*({.+?})\s*\)'
        m = re.search(pattern2, html, re.DOTALL)
    
    if not m:
        raise ValueError(
            "talkPage.init JSON not found in HTML. "
            "TED.com may have changed its structure."
        )
    
    json_str = m.group(1)
    return json.loads(json_str)


def extract_transcript(talk_data: dict) -> list[dict]:
    """
    talk_dataからトランスクリプト段落を抽出
    
    実際の構造はTED側で変わる可能性があるため、複数のパスを試す
    
    Returns:
        list of {start_sec, text}
    """
    # よくある構造のパターン
    paths = [
        ["talks", 0, "player_talks", 0, "transcript_paragraphs"],
        ["talks", 0, "transcript_paragraphs"],
        ["transcript_paragraphs"],
        ["talk", "transcript_paragraphs"],
    ]
    
    for path in paths:
        try:
            current = talk_data
            for key in path:
                current = current[key]
            if isinstance(current, list):
                return [
                    {
                        "start_sec": p.get("time", p.get("start_sec", 0)) // 1000 if isinstance(p.get("time"), int) and p.get("time", 0) > 1000 else p.get("time", p.get("start_sec", 0)),
                        "text": p.get("text", " ".join(c.get("text", "") for c in p.get("cues", []))),
                    }
                    for p in current
                ]
        except (KeyError, IndexError, TypeError):
            continue
    
    # 全部失敗した場合は構造をダンプ
    raise ValueError(
        "Could not locate transcript in talk_data. "
        f"Top-level keys: {list(talk_data.keys()) if isinstance(talk_data, dict) else type(talk_data)}"
    )


def get_meta(talk_data: dict) -> dict:
    """
    タイトル・話者・動画長などのメタ情報を抽出
    """
    paths_to_try = [
        ["talks", 0],
        ["talk"],
    ]
    
    for path in paths_to_try:
        try:
            current = talk_data
            for key in path:
                current = current[key]
            return {
                "title": current.get("title"),
                "speaker": current.get("speaker_name") or current.get("speakers", [{}])[0].get("full_name"),
                "duration_sec": current.get("duration"),
                "slug": current.get("slug"),
            }
        except (KeyError, IndexError, TypeError):
            continue
    return {}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_transcript.py <slug>")
        print("Example: python scrape_transcript.py ted_ed_the_fascinating_reason_you_loved_peek_a_boo")
        sys.exit(1)
    
    slug = sys.argv[1]
    print(f"Fetching: https://www.ted.com/talks/{slug}\n")
    
    try:
        html = fetch_html(slug)
        print(f"HTML size: {len(html):,} bytes")
        
        talk_data = extract_talk_data(html)
        print(f"talkPage.init JSON top-level keys: {list(talk_data.keys()) if isinstance(talk_data, dict) else 'not a dict'}\n")
        
        meta = get_meta(talk_data)
        print(f"Meta: {json.dumps(meta, ensure_ascii=False, indent=2)}\n")
        
        paragraphs = extract_transcript(talk_data)
        print(f"Paragraphs: {len(paragraphs)}")
        for i, p in enumerate(paragraphs[:3]):
            text_preview = p["text"][:80] + "..." if len(p["text"]) > 80 else p["text"]
            print(f"  [{p['start_sec']}s] {text_preview}")
        
        if len(paragraphs) > 3:
            print(f"  ... and {len(paragraphs) - 3} more")
            
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        if e.code == 404:
            print("This talk does not exist on ted.com")
        sys.exit(1)
    except ValueError as e:
        print(f"Parse error: {e}")
        sys.exit(1)
