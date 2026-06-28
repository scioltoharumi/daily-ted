# 日次バッチプロンプト(Cloud Task / Scheduled Agent 用)

このプロンプトは Claude Code の Scheduled Agent(claude.ai/code)に登録する。cron は UTC で `0 21 * * *`(JST 06:00)。
変更時は本ファイルを更新して Scheduled Agent 側も再登録すること。

> 本プロンプトは要件定義書 v3.3(`docs/requirements_v3.md`)の D-019 採用版に対応する。
> TED-Ed の取得は **ted.com 公式 GraphQL API 直結**(`topic(slug:"ted+ed").videos` で新着検出、
> `translation(language,videoId).paragraphs.cues` で公式トランスクリプト取得)。YouTube 直結
> フロー(D-016)は (a) クラウド IP の watch ページ遮断、(b) "X days ago" 粗い相対時刻による
> 恒久欠落、(c) YouTube 字幕が公式 lesson 本文と乖離、の 3 つの欠点で 2026-05-23 に退役。

---

## プロンプト本文(コピペして Scheduled Agent に登録)

```text
You are the daily batch script for the Daily TED PWA (Daily TED-Ed English learning).

# 必読ドキュメント(最初に読む)

リポジトリ root から以下を順に読み込むこと:

1. /CLAUDE.md
2. /docs/project_guide.md
3. /docs/requirements_v3.md(SSoT)
4. /docs/data_schema.md
5. /prompts/word_classification.md
6. /steering/design_decisions.md(特に D-016)
7. /steering/lessons.md

# 環境準備

追加の Python パッケージは不要(`urllib` のみで動作)。`scripts/fetch_ted_ed_talks.py`
と `scripts/fetch_ted_transcript.py` は標準ライブラリのみ。

# 実行手順

## Step 0: main ブランチ同期(最重要)

GitHub Pages は `main` ブランチを配信元にしている。バッチ成果を必ず `main` に
反映させるため、作業前に必ず最新の `main` から開始すること:

```bash
git fetch origin main
git checkout main
git reset --hard origin/main
```

セッションが固有の作業ブランチ(`claude/...`)に隔離されている場合でも、上記で
`main` の最新状態を取り込む。これを怠ると Step 2 の冪等性チェックが過去日の
JSON を見つけられず、かつ古いベースで分岐して他日のデータを失う。

## Step 1: 日付決定(JST)

JST(Asia/Tokyo)で当日日付 YYYY-MM-DD を決定。

## Step 2: 冪等性チェック

`/data/talks/YYYY-MM-DD.json` が既に存在する場合は何もせず正常終了。

## Step 3: TED-Ed 新着動画の取得(ted.com)

```
python scripts/fetch_ted_ed_talks.py --since <last_processed_iso> --json
```

`<last_processed_iso>` は `/data/index.json` の `talks[0].published_at`(無ければ
24時間前のISO)を使う。引数なしで実行すると直近24h を返す。

このスクリプトは ted.com GraphQL を1回叩き、`topic(slug:"ted+ed").videos` の
ノードから:
- ted_video_id(数値)、slug(`canonicalUrl` の最後の path セグメント)、title、
  speaker(presenterDisplayName)、duration_sec、publishedAt、canonical_url、
  description、thumbnail_url(`primaryImageSet` の 16x9)

を取得して JSON 配列で返す。`publishedAt` は ISO 8601 で正確なため、相対時刻
推定や 24h 窓の脆弱性はない。

返却が0件なら新作なしとして即時終了(冪等)。`/data/index.json` の
`skipped_dates` に当日日付を追加してコミット&プッシュは行うこと。

複数の新着が返った場合は、当日バッチでは **最も古い未処理1本のみ** を扱う
(残りは翌日以降のバッチで順次拾う)。これにより 1日 1本の配信リズムを保つ。

## Step 4: (削除)

旧 D-016 時代の ed.ted.com 補強ステップは廃止。Step 3 の ted.com GraphQL が
description / publishedAt / speaker / duration を全て返すため不要。

## Step 5: 公式トランスクリプト取得(ted.com)

```
python scripts/fetch_ted_transcript.py <ted_video_id> en
```

ted.com GraphQL の `translation(language:"en", videoId:<id>)` を叩き、
段落・cue 単位の公式 lesson トランスクリプトを得る。返却構造:

```
{
  "video_id": "...",
  "language": "en",
  "duration_sec": float,
  "paragraphs": [
    { "start_sec": float, "cues": [
        { "start_sec": float, "end_sec": float, "duration_sec": float, "text": str },
        ...
      ] },
    ...
  ]
}
```

ted.com は段落分割と paragraphs[].cues[].text を既に持っているため、
**段落構造はこの結果をそのまま採用する**(Claude による再段落化は禁止。
Step 6 で文に分割する処理のみ行う)。

**取得失敗時の鉄則(NEVER FABRICATE)**:

- `translation` が null を返す / 4xx・5xx エラー / ネットワーク不能
  → その日は失敗として終了し、トランスクリプトを **絶対に再構成・捏造
    しない**。`skipped_dates` に当日日付を追加してコミット&プッシュ。
- 過去に `2026-05-15.json`(masquerade)を IP ブロック下でポー原作から
  再構成した事例があるが、これは公式と乖離した汚染データだったため
  D-019 で禁止規約化。`background.details` に再構成である旨を書いて誤魔化す
  運用も禁止。

## Step 6: スキーマ変換と全要素事前生成

`docs/data_schema.md` の `TalkJson` スキーマに従って JSON を生成する。
重要な処理:

0. **VERBATIM 厳守**:
   - ted.com から取得した cue.text の文字列は **一字一句改変してはならない**
     (大文字小文字・句読点・改行・全角半角を含めて公式表記を保持)。
   - Claude は段落・文の **再区切り** と **構造解析** のみ行い、本文の
     書き換え・整文・誤字修正を行わない。

1. **段落・文への分割**:
   - 段落: ted.com の `paragraphs[]` 構造をそのまま採用(start_sec はその段落の
     最初の cue の start_sec)。動画長 5〜7 分なら通常 5〜10段落。
   - 文: 各段落内で cues.text を結合してから `. ? !` 等で文分割。cue 内に改行
     (`\n`)が含まれる場合、原文の改行は文区切りではなく組版上の改行として
     スペース1個に置換してから処理する。
   - 文の `id` は段落内で `s1, s2, ...` と振る。

2. **全単語に tier 分類を付与**(`prompts/word_classification.md` の基準):
   - basic / normal / key / frequent
   - **key / frequent / normal tier**: meaning / pos / pronunciation / example(en+ja) / context / collocations を完全生成
   - **basic / skip tier**(it, the, of 等の機能語): 短縮形 `Sk(surface, meaning)` で OK。
     例:`"the": Sk("the", "その/それ")`。pos / pron / example / context / collocations は省略可。
     これは出力トークン削減のための D-205 緩和規則(後述 Step 9.5 参照)。

3. **全表現(イディオム・複合名詞)を識別**(2-tier 分類):
   - normal / frequent

4. **全文に**:
   - 日本語訳(translation_ja)
   - 構文解析(structure: S/V/O/C ラベル + 解説)
   - tokens 配列(word/expression/foreign/skip)

5. **背景情報(Talk レベル)**:
   - summary(日本語、約150字)
   - details(3〜5項目、関連分野・ナレーター情報・キー概念)
   - **details は文字列配列**(オブジェクトではない)。`"見出し: 本文"` のような自由形式で1要素1行。

6. **段落要約 `paragraph_summaries_ja`(D-204 / v3.4)**:
   - 各 transcript 段落に対応する日本語の要点をオブジェクト配列で生成。
     ```json
     "paragraph_summaries_ja": [
       {"paragraph_id": "p1", "summary": "日本語要約..."},
       {"paragraph_id": "p2", "summary": "..."}
     ]
     ```
   - `paragraph_id` は transcript の段落 id (`p1`, `p2`, …) と1対1で一致させる。順序も同じ。
   - 1段落あたり 80〜150 字を目安、**talk 全体で 1000 字以内**に収める。
   - VERBATIM 訳ではなく「要約」: 段落の主旨・展開・キー固有名詞を簡潔に。
   - 詳細ページで背景情報とトランスクリプトの間に表示され、各項目クリックで該当段落へジャンプする UI 用。
   - 段落数と summaries 数が一致しないと PWA 側で番号ズレが起きるため厳守。

### 生成は `scripts/talk_builder.py` を使い、**チャンク分割で書く**こと(D-205)

> **2026-06-28 教訓**: 生成スクリプトを 1 回の Write で全部書こうとすると、
> 1 talk あたり 30〜50KB になり Claude の **per-message 出力上限**を超えて失敗する
> (Agent が 12 日連続でここで沈黙した)。talk_builder で boilerplate は減るが、
> 本質的解決は **「単一のツール呼び出しに全データを載せない」= チャンク分割**である。

#### 必須: import ブートストラップ

生成スクリプトは scratchpad など repo 外に置かれ `python3 <path>` で実行される場合がある。
その場合 `from scripts.talk_builder import ...` は ModuleNotFoundError になる
(Python は CWD ではなくスクリプトのあるディレクトリを sys.path に置くため)。
**必ず先頭で repo root を sys.path に追加する**:

```python
import sys, subprocess
sys.path.insert(0, subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True).strip())
from scripts.talk_builder import generate_talk, Wk, Sk, Ek
```

#### 必須: チャンク分割の手順(各ツール呼び出しを小さく保つ)

talk が 5 段落 / 60 語を超える規模なら、以下のように **複数ステップに分けて** 構築する。
各ステップは独立した Write/Edit 呼び出しとし、1 回の出力を小さく(目安 ≤ 8KB / ~25 entry)保つ:

1. **Write**: スケルトン(import ブートストラップ + META + BACKGROUND + 空コンテナ + 末尾呼び出し)
   ```python
   # ...bootstrap import...
   META = {...}
   BACKGROUND = {...}            # details は string[]、"見出し: 本文" 形式
   P = []
   W = {}
   E = {}
   PSUM = []
   generate_talk(META, BACKGROUND, P, W, E, PSUM, "data/talks/YYYY-MM-DD.json")
   ```
2. **Edit**(段落ごと、または2〜3段落ずつ): `P = []` 行の直後に `P.append({...})` を追記
3. **Edit**(語彙を ~25 語ずつ複数回): `W.update({ "w1": Wk(...), ... })` を追記
   - key/normal/frequent 語は `Wk(tier, surface, pos, pron, meaning, ex_en, ex_ja, ctx, coll)` 完全形
   - basic/skip 語は `Sk(surface, meaning)` 短縮形(`"the": Sk("the","その")`)
4. **Edit**: 表現を `E.update({ "in_fact": Ek("normal","in fact","phrase · B1","/ɪn fækt/","実際","事実として"), ... })`
5. **Edit**: `PSUM = [...]`(段落要約、P と同じ順序・同数)
6. **Bash**: `python3 <script>` 実行 → stats を確認

各 Edit の後にツール結果(成功)を確認してから次へ進むこと。これにより
**どの 1 呼び出しも出力上限に近づかない**。これが出力制限回避の本質的対策である。

#### talk_builder が自動でやること

token id 付与 / structure のオブジェクト化 / **未参照 entry の除去** /
**foreign(`f`)・expression(`e`)両方の ref を expressions に集約** /
PSUM の段落 id 紐付け / E entry の空欄補完 / 出力 JSON の indent 化 / stats 表示。

> 補足: token は `("w",surface,ref,tier)` / `("e",surface,ref)` / `("f",surface,ref)` /
> `("s",surface)`。foreign(`f`)の ref は **expressions 辞書(E)に定義**する
> (フロントは foreign を expressions から引くため。E に無いとモーダルが空になる)。

## Step 7: メタ情報

`TalkJson` の以下のフィールドを設定:

- `id`: `talk_YYYY-MM-DD`(配信日ベース、ted.com 公開日とは別)
- `date`: 当日日付(配信日 / JST)
- `source`: `"ted-ed"`(常に固定。v3.1 で TED Talks は廃止)
- `slug`: ted.com の talk slug(`canonicalUrl` 末尾)。例: `stephanie_h_smith_the_incredible_engineering_of_venice`
- `video_id`: **ted.com の数値 video id**(D-019 v3.3)。例: `"178996"`
- `title`: ted.com の talk title(YouTube 上の表記とは差異あり得る。ted.com を SSoT とする)
- `speaker`: `presenterDisplayName`(空なら `"TED-Ed"`)
- `duration_sec`: ted.com `videos.duration`(秒)。トランスクリプト末尾の `end_sec` でも可
- `published_at`: ted.com `publishedAt`(ISO 8601, UTC)
- `video_url`: `https://www.ted.com/talks/<slug>`(= canonical_url)
- `embed_url`: `https://embed.ted.com/talks/<slug>`
- `thumbnail_url`: ted.com `primaryImageSet` の 16x9 URL

### Step 7.5: 分類メタ情報(v3.2 / D-203)

PWA のビュー D(トピック別)/ビュー E(単語駆動)/検索のために以下を生成。
判定は Claude が動画タイトル・description・transcript の内容から文脈的に行う。

- `primary_topic`: string
  - 主トピックを1つ。例: `"Psychology"`, `"Science"`, `"Geology"`, `"Philosophy"`,
    `"Linguistics"`, `"Mathematics"`, `"History"`, `"Biology"`, `"Technology"`,
    `"Art"`, `"Economics"`, `"Health"`, `"Astronomy"` 等。
  - PascalCase 単語または短いフレーズ。粒度は中規模(細分しすぎない)。

- `tags`: string[]
  - 3〜6 個の細かい分類タグ。kebab-case。
  - 例(Iceland's lava の場合): `["volcano", "iceland", "lava-flow", "geology", "natural-disaster"]`
  - 例(peek-a-boo の場合): `["developmental-psychology", "infant-cognition", "object-permanence", "play"]`
  - 単数形を基本(`volcanoes` ではなく `volcano`)。

- `difficulty`: "easy" | "medium" | "hard"
  - 学習者(英語中級〜上級)目線での難易度判定。
  - **easy**: 構文がシンプル、専門用語が少ない、frequent 語が多い。CEFR B1 程度で読める。
  - **medium**: 一般的な TED-Ed の標準難度。frequent と key が混在、専門用語が中程度含まれる。
  - **hard**: 専門用語密度が高い、長文構造が複雑、key/key 以上の語彙が多い。CEFR B2〜C1 推奨。
  - 迷ったら `medium` を選ぶ。

これらは `index.json` の TalkSummary 側にも同じ値を入れること。

## Step 8: JSON 出力

- `/data/talks/YYYY-MM-DD.json` を書き込み
- `/data/index.json` の `talks` 配列の先頭に新規エントリを追加(date 降順)
- `/data/index.json` の `updated_at` を更新(JST ISO 8601)

## Step 9: commit & push

```bash
git add data/
git commit -m "daily: YYYY-MM-DD ted-ed <title>"
git push origin HEAD:main
```

`git push origin HEAD:main` で必ず `main` へ直接反映する(GitHub Pages の
配信元)。単なる `git push` はセッション専用ブランチに送られ、サイトに
反映されないため使わない。push がブランチ保護で拒否される場合は、PR を
作成して auto-merge する運用に切り替えること。

## Step 9.5: 失敗時の安全網(D-205 / 2026-06-28 教訓)

セッション中で **以下のいずれか** が発生した場合、talk 生成を即座に中止し
**skip コミットで打ち切る**(沈黙でセッション終了しない):

- Write/Edit ツールが「レスポンスが出力制限を超えました」エラーを返した
- transcript fetch が成功したが、その後の生成スクリプト記述中で出力上限に達した
- 任意のステップで2回連続のリトライが失敗した

具体的に行うこと:

```bash
# 1) data/index.json の skipped_dates に当日を追加(date 順ソート)
# 2) updated_at を更新
git add data/index.json
git commit -m "daily: YYYY-MM-DD skip (generation deferred — manual backfill needed for <title>)"
git push origin HEAD:main

# 3) steering/lessons.md に backfill 候補として追記
#    - 失敗日付 / 失敗 step / 該当 video_id と slug / 推定原因
```

この安全網により:
- watchdog ワークフロー(`.github/workflows/agent-watchdog.yml`)が誤発火しない
- サイトのタイムラインで該当日が "no new release" として表示される(沈黙ではない)
- backfill 待ち talk が `lessons.md` に列挙される(後日 manual 補填の参照点)

**重要**: 「NEVER FABRICATE」原則(D-019)はここでも適用される。skip コミットの
理由として「生成省略」を記録するのは OK だが、トランスクリプトを再構成して
誤魔化す skip 偽装は禁止。

# エラーハンドリング

- 何らかの失敗時は、原因を stderr に記録して非ゼロ終了する
- 部分的なコミットはしない(成功時のみ commit/push)
- リトライは最大2回まで(主にネットワークエラー)
- ted.com の `translation` クエリが null を返した場合: 別言語(`ja` 等)に
  fall back **してはならない**(英語ネイティブ本文が SSoT。日本語訳は
  Claude 側の `translation_ja` で生成する)。null なら **その日は skip**。
- **絶対に再構成・捏造しない**(D-019 / lessons.md 2026-05-23 参照)。

# 制限事項

- `/data/` 以外のファイルは絶対に変更しない
- 既存の YYYY-MM-DD.json は上書きしない(冪等性)
- コスト懸念は度外視。トークン節約のため単語を端折ったりしない
```

---

## プロンプトの保守

### 変更が必要になるシナリオ

1. **ted.com GraphQL スキーマ変更** → `scripts/fetch_ted_ed_talks.py` / `scripts/fetch_ted_transcript.py` のクエリを更新。スキーマ確認は `__schema` introspection で行う。
2. **TED-Ed が動画投稿頻度を変えた場合** → `--since` / `--hours` のチューニングのみ(構造変更不要)。
3. **データスキーマが進化した場合** → `/docs/data_schema.md` を更新し、Step 6 の指示も合わせる。
4. **ted.com 側で TED-Ed topic slug が変わった場合**(現在 `ted+ed`、id 345) → `fetch_ted_ed_talks.py` の `TED_ED_TOPIC_SLUG` を更新。

### Scheduled Agent 側の設定

- cron 式: `0 21 * * *` UTC (= JST 06:00)
- 連携リポジトリ: 本リポジトリ(scioltoharumi/daily-ted、private)
- 必要権限: Bash, Web fetch, ファイル編集, リポジトリ書き込み
- タイムアウト: デフォルト(30分)
- 実行通知: 失敗時のみ通知(Phase 3 で設定方法決定)
