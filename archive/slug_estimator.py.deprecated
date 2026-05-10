"""
YouTube動画タイトルから ted.com/talks の slug を推定するヘルパー

使い方:
    python scripts/slug_estimator.py "The fascinating reason you loved peek-a-boo" ted-ed
    → ted_ed_the_fascinating_reason_you_loved_peek_a_boo

実装ルール:
- 小文字化
- 英数字とスペース・ハイフン・アポストロフィのみ残す
- スペース・ハイフンをアンダースコアに置換
- アポストロフィは除去(don't → dont)
- 連続アンダースコアを1つに
- 前後のアンダースコア除去
- TED-Edの場合は "ted_ed_" プレフィックス追加
"""

import re
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


def estimate_slug(youtube_title: str, source: str = "ted-ed") -> str:
    """
    YouTubeタイトルからted.com slugを推定
    """
    s = youtube_title.lower()
    # アポストロフィ・引用符・特殊記号を除去
    s = re.sub(r"['""''`]", "", s)
    # 英数字・スペース・ハイフン以外を除去
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    # スペース・ハイフンを_に
    s = re.sub(r"[\s\-]+", "_", s)
    # 連続_を1つに
    s = re.sub(r"_+", "_", s)
    # 前後の_除去
    s = s.strip("_")
    
    if source == "ted-ed":
        s = "ted_ed_" + s
    return s


def estimate_slug_variants(youtube_title: str, source: str = "ted-ed") -> list[str]:
    """
    複数の推定パターンを返す(フォールバック用)
    """
    base = estimate_slug(youtube_title, source)
    variants = [base]
    
    # 冠詞除去版(a/an/the が先頭にある場合)
    title_no_articles = re.sub(r"^(a|an|the)\s+", "", youtube_title, flags=re.IGNORECASE)
    if title_no_articles != youtube_title:
        variants.append(estimate_slug(title_no_articles, source))
    
    return list(dict.fromkeys(variants))  # unique preserving order


def check_url_exists(slug: str) -> tuple[bool, int]:
    """
    ted.com/talks/{slug} にHEADリクエストして存在確認
    
    Returns:
        (exists, status_code)
    """
    url = f"https://www.ted.com/talks/{slug}"
    req = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            return (resp.status == 200, resp.status)
    except HTTPError as e:
        return (False, e.code)
    except URLError:
        return (False, 0)


def find_slug(youtube_title: str, source: str = "ted-ed") -> str | None:
    """
    複数バリアントを試して、200を返すslugを見つける
    全部404ならNone
    """
    variants = estimate_slug_variants(youtube_title, source)
    for slug in variants:
        exists, code = check_url_exists(slug)
        print(f"  Trying: {slug} → HTTP {code}")
        if exists:
            return slug
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slug_estimator.py <youtube_title> [ted-ed|ted-talks]")
        print("Example: python slug_estimator.py 'The fascinating reason you loved peek-a-boo' ted-ed")
        sys.exit(1)
    
    title = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else "ted-ed"
    
    print(f"Title: {title}")
    print(f"Source: {source}\n")
    
    print("Variants:")
    for v in estimate_slug_variants(title, source):
        print(f"  - {v}")
    
    print("\nChecking URLs:")
    found = find_slug(title, source)
    
    if found:
        print(f"\n✓ Found: https://www.ted.com/talks/{found}")
    else:
        print("\n✗ All variants returned 404. This Talk may not be on ted.com.")
        print("  → Skip this video for today's batch.")
