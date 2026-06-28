"""skip トークンに埋もれた内容語を word トークンへ昇格する補強ツール(D-206)。

2026-06-28 教訓: 生成時に内容語を skip(クリック不可・訳なし)に埋めてしまい、
難語に訳が無いと苦情。本ツールは既存 talk JSON を壊さず、与えた語彙辞書に
含まれる語だけを skip から切り出して word トークン化し、辞書エントリを追加する。

# 使い方

```python
from scripts.retokenize import retokenize_talk

# {小文字surface: (tier, meaning, pos, pron[, ex_en, ex_ja, ctx])}
VOCAB = {
    "experiences": ("normal", "経験", "n · B1", "/ɪkˈspɪə.ri.ən.sɪz/"),
    "powerful":    ("normal", "強力な", "adj · B1", "/ˈpaʊ.ə.fəl/"),
    "grief":       ("key",    "深い悲しみ", "n · B2", "/ɡriːf/", "Grief overwhelmed her.", "悲しみが彼女を襲った。", "死別など喪失の悲嘆"),
}
stats = retokenize_talk("data/talks/2026-06-25.json", VOCAB)
print(stats)  # {'promoted': N, 'entries_added': M, 'skip_words_remaining': K}
```

- 大文字小文字は無視してマッチ(辞書キーは小文字)。token の surface は原文の表記を保持。
- 所有格 `Venice's` は `Venice`(word)+ `'s`(skip)に分割。
- 既存の word/expression/foreign トークンには一切触れない(skip のみ走査)。
- 単語境界を尊重(`art` は `start` 内にマッチしない)。
- 既に同じ ref が talk.words にあれば上書きしない(冪等)。
- 1 文字語・与えた辞書に無い語はそのまま skip に残す。
"""
import json
import re


def _entry_from_tuple(surface_lower, v):
    """VOCAB の値(tuple/dict)を WordEntry dict へ。"""
    if isinstance(v, dict):
        tier = v.get("tier", "normal")
        meaning = v.get("meaning", "")
        pos = v.get("pos", "")
        pron = v.get("pron", "")
        ex_en = v.get("ex_en", "") or v.get("example", {}).get("en", "")
        ex_ja = v.get("ex_ja", "") or v.get("example", {}).get("ja", "")
        ctx = v.get("context", "") or v.get("ctx", "")
        coll = v.get("collocations", []) or v.get("coll", [])
        surface = v.get("surface", surface_lower)
    else:
        v = list(v)
        # (tier, meaning, pos, pron, ex_en, ex_ja, ctx, coll) の前方一致
        tier = v[0] if len(v) > 0 else "normal"
        meaning = v[1] if len(v) > 1 else ""
        pos = v[2] if len(v) > 2 else ""
        pron = v[3] if len(v) > 3 else ""
        ex_en = v[4] if len(v) > 4 else ""
        ex_ja = v[5] if len(v) > 5 else ""
        ctx = v[6] if len(v) > 6 else ""
        coll = v[7] if len(v) > 7 else []
        surface = surface_lower
    return {
        "tier": tier, "surface": surface, "pos": pos, "pron": pron,
        "meaning": meaning, "example": {"en": ex_en, "ja": ex_ja},
        "context": ctx, "collocations": list(coll),
    }


def _split_skip_surface(surface, vocab):
    """skip トークンの surface 文字列を [(kind, text[, ref]), ...] に分割。

    kind は 'skip' か 'word'。word の場合は (‘word’, 原文表記, ref(小文字)).
    """
    out = []
    last = 0
    for m in re.finditer(r"[A-Za-z]+", surface):
        base = m.group(0).lower()
        if base in vocab:
            if m.start() > last:
                out.append(("skip", surface[last:m.start()]))
            out.append(("word", m.group(0), base))
            last = m.end()
    if last < len(surface):
        out.append(("skip", surface[last:]))
    # 連続 skip をマージ
    merged = []
    for item in out:
        if item[0] == "skip" and merged and merged[-1][0] == "skip":
            merged[-1] = ("skip", merged[-1][1] + item[1])
        else:
            merged.append(item)
    return merged


def retokenize_talk(talk_path, vocab, dry_run=False):
    """talk JSON の skip トークンを走査し、vocab の語を word トークンへ昇格。

    vocab: {小文字surface: tuple または dict}(_entry_from_tuple 参照)
    Returns: stats dict
    """
    vocab = {k.lower(): v for k, v in vocab.items()}
    d = json.load(open(talk_path, encoding="utf-8"))
    words = d.setdefault("words", {})

    promoted = 0
    added_refs = set()

    for p in d["transcript"]:
        for s in p["sentences"]:
            new_tokens = []
            for t in s["tokens"]:
                if t.get("type") != "skip":
                    new_tokens.append(t)
                    continue
                pieces = _split_skip_surface(t["surface"], vocab)
                if all(pc[0] == "skip" for pc in pieces):
                    new_tokens.append(t)  # 変化なし
                    continue
                for pc in pieces:
                    if pc[0] == "skip":
                        if pc[1]:
                            new_tokens.append({"type": "skip", "surface": pc[1]})
                    else:
                        _, orig_surface, ref = pc
                        if ref not in words:
                            words[ref] = _entry_from_tuple(ref, vocab[ref])
                            added_refs.add(ref)
                        tier = words[ref].get("tier", "normal")
                        new_tokens.append({
                            "type": "word", "surface": orig_surface,
                            "ref": ref, "tier": tier,
                        })
                        promoted += 1
            # token id 振り直し
            for i, t in enumerate(new_tokens, 1):
                t["id"] = f"t{i}"
            s["tokens"] = new_tokens

    # 残存 skip 内容語の数(参考)
    remaining = 0
    for p in d["transcript"]:
        for s in p["sentences"]:
            for t in s["tokens"]:
                if t.get("type") == "skip":
                    remaining += len(re.findall(r"[A-Za-z]{4,}", t["surface"]))

    if not dry_run:
        with open(talk_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    return {"promoted": promoted, "entries_added": len(added_refs),
            "skip_words_remaining_4plus": remaining}
