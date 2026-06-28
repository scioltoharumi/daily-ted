"""Shared TalkJson builder used by daily_batch.md Step 6 and manual backfills.

このヘルパーを使うことで、per-talk 生成スクリプトの boilerplate を最小化し、
Claude セッションの per-message 出力トークン制限到達を回避する。
(2026-06-28 lessons.md: Agent が castle 生成中に出力制限に到達し12日間失敗した教訓から導入)

# 使い方(per-talk 生成スクリプトのテンプレ)

```python
from scripts.talk_builder import generate_talk, Wk, Sk, Ek

META = {
    "id": "talk_2026-MM-DD", "date": "2026-MM-DD", "source": "ted-ed",
    "primary_topic": "...", "tags": [...], "difficulty": "medium",
    "slug": "...", "video_id": "...", "title": "...", "speaker": "...",
    "duration_sec": 0, "published_at": "...Z",
    "video_url": "https://www.ted.com/talks/...",
    "embed_url": "https://embed.ted.com/talks/...",
    "thumbnail_url": "...",
}

BACKGROUND = {
    "summary": "150字程度の概要",
    "details": [
        "見出し: 本文(string[] であってオブジェクトではないことに注意)",
    ],
}

# 段落データ:start_sec と sentences のリスト
# sentences[i] = {"text": ..., "ja": ..., "structure": [...], "tokens": [...]}
P = [
    {"start_sec": 6.0, "sentences": [
        {
            "text": "English sentence.",
            "ja": "日本語訳。",
            "structure": [("S","subject",""),("V","verb",""),("O","object","")],
            "tokens": [
                ("w","English","english","key"),
                ("s"," "),
                ("w","sentence","sentence","skip"),
                ("s","."),
            ],
        },
    ]},
]

# 単語辞書(token.ref から参照)
W = {
    # 完全形: Wk(tier, surface, pos, pron, meaning, ex_en, ex_ja, ctx="", coll=[])
    "english": Wk("key","English","adj · A1","/ˈɪŋ.ɡlɪʃ/","英語の","English class.","英語の授業。"),
    # skip / basic は短縮形 Sk(surface, meaning) で OK
    "sentence": Sk("sentence", "文"),
}

# 表現辞書
E = {
    # 完全形: Ek(tier, surface, pos, pron, literal, meaning, ctx="", coll=[])
    # literal 省略時は meaning と同じ扱い
}

# D-204: 段落要約(P と同じ順序、p1..pN に対応)
PSUM = [
    "段落1の日本語要約(80-150字目安、talk 全体で1000字以内)。",
]

generate_talk(META, BACKGROUND, P, W, E, PSUM, "data/talks/2026-MM-DD.json")
```

# 短縮形のメリット(出力トークン削減)

```python
# 旧:基本語にも full フィールド(~90 chars/entry)
"the": Wk("skip","the","article · A1","/ðə/","その","The book.","その本。","",[]),

# 新:短縮形(~22 chars/entry、約 75% 減)
"the": Sk("the","その"),
```

talk 1 本あたり 30-50 個ある basic/skip 語をすべて短縮形にすると 5-8KB の出力削減が見込める。
"""
import json, os


def Wk(tier, surface, pos="", pron="", meaning="", ex_en="", ex_ja="", ctx="", coll=()):
    """Word entry tuple(9要素)を返す。

    順序: tier, surface, pos, pron, meaning, example.en, example.ja, context, collocations
    skip/basic 語は Sk() の方が短い。
    """
    return (tier, surface, pos, pron, meaning, ex_en, ex_ja, ctx, list(coll))


def Sk(surface, meaning=None):
    """Skip-tier 単語の短縮形。meaning 省略時は surface 自身を意味とする。

    `Sk("the", "その")` → ("skip", "the", "", "", "その", "", "", "", [])
    `Sk("water")`       → ("skip", "water", "", "", "water", "", "", "", [])
    """
    return ("skip", surface, "", "", meaning if meaning is not None else surface, "", "", "", [])


def Ek(tier, surface, pos="", pron="", literal="", meaning="", ctx="", coll=()):
    """Expression entry tuple(8要素)を返す。

    順序: tier, surface, pos, pron, literal, meaning, context, collocations
    meaning 空のとき literal が代用される。
    """
    return (tier, surface, pos, pron, literal, meaning, ctx, list(coll))


def _build_word(w):
    tier, surface, pos, pron, meaning, ex_en, ex_ja, context, collocations = w
    return {
        "tier": tier, "surface": surface, "pos": pos, "pron": pron, "meaning": meaning,
        "example": {"en": ex_en, "ja": ex_ja}, "context": context,
        "collocations": list(collocations),
    }


def _build_expr(e):
    tier, surface, pos, pron, literal, meaning, context, collocations = e
    return {
        "tier": tier, "surface": surface, "pos": pos, "pron": pron, "literal": literal,
        "meaning": meaning, "context": context, "collocations": list(collocations),
    }


def _build_sentence(sid, sd):
    """sentence dict (text/ja/structure/tokens) を TalkJson の Sentence 形式へ変換。"""
    structure = []
    for s in sd["structure"]:
        item = {"label": s[0], "content": s[1]}
        if len(s) > 2 and s[2]:
            item["note"] = s[2]
        structure.append(item)
    tokens = []
    tid = 1
    for t in sd["tokens"]:
        if t[0] == "s":
            tokens.append({"id": f"t{tid}", "type": "skip", "surface": t[1]})
        elif t[0] == "w":
            tokens.append({"id": f"t{tid}", "type": "word", "surface": t[1], "ref": t[2], "tier": t[3]})
        elif t[0] == "e":
            tokens.append({"id": f"t{tid}", "type": "expression", "surface": t[1], "ref": t[2]})
        elif t[0] == "f":
            tokens.append({"id": f"t{tid}", "type": "foreign", "surface": t[1], "ref": t[2]})
        else:
            continue
        tid += 1
    return {"id": sid, "text": sd["text"], "translation_ja": sd["ja"],
            "structure": structure, "tokens": tokens}


def _clean_tokens(P):
    """生成過程で混入した不正タプルを除去(authoring ミス耐性)。"""
    for p in P:
        for sd in p["sentences"]:
            sd["tokens"] = [t for t in sd["tokens"]
                            if isinstance(t, tuple) and len(t) >= 2 and t[0] in ("s", "w", "e", "f")]


def _normalize_E(E):
    """expression entry の長さ調整・default 補完。"""
    for k, v in list(E.items()):
        v = list(v)
        while len(v) < 8:
            v.append("")
        if not v[5]:
            v[5] = v[4]  # meaning 空なら literal を流用
        if not isinstance(v[7], list):
            v[7] = []
        E[k] = tuple(v)


def generate_talk(META, BACKGROUND, P, W, E, PSUM, out_path):
    """TalkJson を生成して out_path に書き出し、stats dict を返す。

    - 必須: META(配信メタ), BACKGROUND(背景情報), P(段落配列),
            W(単語辞書), E(表現辞書), PSUM(段落要約配列), out_path(出力 JSON path)
    - PSUM の長さは P と一致させること。一致しない場合は警告を stderr に出し、
      不足分は空文字で埋める。
    - words / expressions は P の tokens で実際に参照された ref のみ出力する。
      W/E に未参照の entry が含まれていても出力されない(掃除)。
    - tokens で参照されているが W/E に未定義の ref は WARN として stderr に出す。

    Returns: dict with file_bytes, paragraphs, sentences, tokens, words, expressions, summaries
    """
    _clean_tokens(P)
    _normalize_E(E)

    talk = {**META, "background": BACKGROUND}
    paragraphs = []
    for i, p in enumerate(P):
        sentences = [_build_sentence(f"s{j+1}", sd) for j, sd in enumerate(p["sentences"])]
        paragraphs.append({"id": f"p{i+1}", "start_sec": p["start_sec"], "sentences": sentences})

    # D-204: 段落要約
    psum = []
    for i in range(len(P)):
        summary = PSUM[i] if i < len(PSUM) else ""
        if i >= len(PSUM):
            print(f"WARN PSUM 不足: p{i+1} に対応する要約が無い(空文字補完)")
        psum.append({"paragraph_id": f"p{i+1}", "summary": summary})
    if len(PSUM) > len(P):
        print(f"WARN PSUM 超過: {len(PSUM)} 件あるが段落は {len(P)} 件しかない(余剰は無視)")
    talk["paragraph_summaries_ja"] = psum

    talk["transcript"] = paragraphs

    used_w, used_e = set(), set()
    for p in P:
        for sd in p["sentences"]:
            for t in sd["tokens"]:
                if t[0] == "w":
                    used_w.add(t[2])
                elif t[0] == "e":
                    used_e.add(t[2])
    missing_w = used_w - set(W)
    missing_e = used_e - set(E)
    if missing_w:
        print(f"WARN tokens に出るが W 辞書に無い refs: {sorted(missing_w)}")
    if missing_e:
        print(f"WARN tokens に出るが E 辞書に無い refs: {sorted(missing_e)}")

    talk["words"] = {k: _build_word(W[k]) for k in sorted(used_w)
                     if k in W and len(W[k]) == 9}
    talk["expressions"] = {k: _build_expr(E[k]) for k in sorted(used_e)
                           if k in E and len(E[k]) == 8}

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(talk, f, ensure_ascii=False, indent=2)

    n_sent = sum(len(p["sentences"]) for p in paragraphs)
    n_tok = sum(len(s["tokens"]) for p in paragraphs for s in p["sentences"])
    stats = {
        "file_bytes": os.path.getsize(out_path),
        "paragraphs": len(paragraphs),
        "sentences": n_sent,
        "tokens": n_tok,
        "words": len(talk["words"]),
        "expressions": len(talk["expressions"]),
        "summaries": len(talk["paragraph_summaries_ja"]),
    }
    print(f"Wrote {out_path}: {stats}")
    return stats
