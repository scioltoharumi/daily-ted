# 日次バッチプロンプト(Cloud Task / Scheduled Agent 用)

このプロンプトは Claude Code の Scheduled Agent(claude.ai/code)に登録する。cron は UTC で `0 21 * * *`(JST 06:00)。
変更時は本ファイルを更新して Scheduled Agent 側も再登録すること。

> 本プロンプトは要件定義書 v3.1(`docs/requirements_v3.md`)の D-016 採用版に対応する。
> TED-Ed の取得は YouTube 直結フロー(channel HTML スクレイピング + youtube-transcript-api)。

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

最初に Python パッケージをインストール:
```
pip install --quiet youtube-transcript-api
```

# 実行手順

## Step 1: 日付決定(JST)

JST(Asia/Tokyo)で当日日付 YYYY-MM-DD を決定。

## Step 2: 冪等性チェック

`/data/talks/YYYY-MM-DD.json` が既に存在する場合は何もせず正常終了。

## Step 3: TED-Ed 新着動画の取得

`python scripts/fetch_ted_ed_videos.py 24` を実行。

このスクリプトは:
- `https://www.youtube.com/@TEDEd/videos` の HTML を取得
- 埋め込まれた `ytInitialData` JSON から各動画の videoId / title /
  publishedTimeText / duration / thumbnail を抽出
- "X hours ago" / "X days ago" 等の表記から直近24時間以内のみを返す

返却が0件なら、その日は新作なしとして即座に終了(冪等)。`/data/index.json` の
`skipped_dates` に当日日付を追加してコミット&プッシュは行うこと。

## Step 4: TED-Ed lesson 詳細メタデータの補強(任意)

任意で `https://ed.ted.com/lessons` の JSON-LD を読み、
今回の動画 title と一致する lesson の uploadDate / description / publisher を補強。
一致しない場合は YouTube 側の情報のみで進める。

## Step 5: トランスクリプト取得

各 videoId について `python scripts/fetch_youtube_transcript.py <video_id>` 相当の処理を実行
(または直接 youtube-transcript-api を呼ぶ)。

得られる snippets:
```
[{ "start_sec": float, "duration_sec": float, "text": str }, ...]
```

## Step 6: スキーマ変換と全要素事前生成

`docs/data_schema.md` の `TalkJson` スキーマに従って JSON を生成する。
重要な処理:

1. **段落・文への再構成**:
   - youtube-transcript-api の snippets は短い(2〜4秒)単位なので、これを
     意味的にまとまる段落(start_sec を保持)と文(. ? ! 等で区切る)に再構成する
   - 1段落 = 数文。動画長 5〜7 分なら通常 5〜10段落程度

2. **全単語に tier 分類を付与**(`prompts/word_classification.md` の基準):
   - basic / normal / key / frequent
   - 全ての単語(it, the 等の基本語を含む)に対して
     meaning / pos / pronunciation / example(en+ja) / context / collocations を生成

3. **全表現(イディオム・複合名詞)を識別**(2-tier 分類):
   - normal / frequent

4. **全文に**:
   - 日本語訳(translation_ja)
   - 構文解析(structure: S/V/O/C ラベル + 解説)
   - tokens 配列(word/expression/foreign/skip)

5. **背景情報(Talk レベル)**:
   - summary(日本語、約150字)
   - details(3〜5項目、関連分野・ナレーター情報・キー概念)

## Step 7: メタ情報

`TalkJson` の以下のフィールドを設定:

- `id`: `talk_YYYY-MM-DD`
- `date`: 当日日付
- `source`: `"ted-ed"`(常に固定。v3.1 で TED Talks は廃止)
- `slug`: 動画タイトルから snake_case で生成(参照用、識別子として)
- `title`: YouTube 動画タイトル
- `speaker`: タイトル末尾(" - 著者名" の形式)から抽出、なければ "TED-Ed"
- `duration_sec`: snippets の最後の start_sec + duration_sec
- `video_url`: `https://www.youtube.com/watch?v=<videoId>`
- `embed_url`: `https://www.youtube.com/embed/<videoId>`
- ※ 旧フィールド(ted.com URL)は使わない

## Step 8: JSON 出力

- `/data/talks/YYYY-MM-DD.json` を書き込み
- `/data/index.json` の `talks` 配列の先頭に新規エントリを追加(date 降順)
- `/data/index.json` の `updated_at` を更新(JST ISO 8601)

## Step 9: commit & push

```bash
git add data/
git commit -m "daily: YYYY-MM-DD ted-ed <title>"
git push
```

# エラーハンドリング

- 何らかの失敗時は、原因を stderr に記録して非ゼロ終了する
- 部分的なコミットはしない(成功時のみ commit/push)
- リトライは最大2回まで(主にネットワークエラー)
- youtube-transcript-api がエラーを返した場合は、別の言語を試す
  (例: 英語が無ければ自動生成英語字幕でも可)

# 制限事項

- `/data/` 以外のファイルは絶対に変更しない
- 既存の YYYY-MM-DD.json は上書きしない(冪等性)
- コスト懸念は度外視。トークン節約のため単語を端折ったりしない
```

---

## プロンプトの保守

### 変更が必要になるシナリオ

1. **YouTube channel ページの UI 変更** で `lockupViewModel` 構造が変わった場合 → `scripts/fetch_ted_ed_videos.py` の抽出ロジックを更新
2. **youtube-transcript-api の API 変更** → スクリプトを更新
3. **TED-Ed が動画投稿頻度を変えた場合** → 新着検出 hours 値を調整
4. **データスキーマが進化した場合** → `/docs/data_schema.md` を更新し、Step 6 の指示も合わせる

### Scheduled Agent 側の設定

- cron 式: `0 21 * * *` UTC (= JST 06:00)
- 連携リポジトリ: 本リポジトリ(scioltoharumi/daily-ted、private)
- 必要権限: Bash, Web fetch, ファイル編集, リポジトリ書き込み
- タイムアウト: デフォルト(30分)
- 実行通知: 失敗時のみ通知(Phase 3 で設定方法決定)
