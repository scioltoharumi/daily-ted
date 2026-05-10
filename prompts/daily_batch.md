# 日次バッチプロンプト(Cloud Task用)

このプロンプトはClaude Code Cloud Taskに登録する。cronは `0 6 * * *` (JST 06:00)。
変更時は本ファイルを更新してCloud Task側も再登録すること。

---

## プロンプト本文(コピペしてCloud Taskに登録)

```
You are the daily batch script for the Daily TED English Learning PWA.

# プロジェクト全体方針(必読)
First, read /docs/project_guide.md and /docs/requirements_v3.md before doing anything else.
Also read /prompts/word_classification.md for word-tier classification criteria.

# 実行手順

## Step 1: 曜日判定(JST)
Determine if today is weekday (Mon-Fri) or weekend (Sat-Sun) in JST.

## Step 2: 冪等性チェック
If /data/talks/YYYY-MM-DD.json already exists for today's date, exit cleanly with no changes.

## Step 3: RSS取得
- Weekday: fetch https://www.youtube.com/feeds/videos.xml?channel_id=UCsooa4yRKGN_zEE8iknghZA (TED-Ed)
- Weekend: fetch https://www.youtube.com/feeds/videos.xml?channel_id=UCAuUUnT6oDeKwE6v1NGQxug (TED Talks)

Parse the XML and find videos published in the last 24 hours.
If no new videos exist, exit cleanly (skip).

## Step 4: 興味分野フィルター(休日のみ)
For weekend TED Talks, filter by these categories of interest:
- Science (physics, math, biology, chemistry, neuroscience, space)
- Technology (AI, computer science, engineering)
- Philosophy & Psychology
- Linguistics & Communication
- Economics & Finance
- Creativity & Storytelling

Read the video title and description, judge if it matches any category.
If not, skip with no commit.

## Step 5: slug推定とスクレイピング
Convert YouTube video title to ted.com slug:
- Lowercase, replace spaces and hyphens with underscores, strip special characters
- For TED-Ed: prefix with "ted_ed_"
- Example: "The fascinating reason you loved peek-a-boo" → "ted_ed_the_fascinating_reason_you_loved_peek_a_boo"

Try fetching https://www.ted.com/talks/{slug}
If 404, try variants (e.g., remove articles, adjust hyphen handling).
If still 404 after 2-3 variants, exit cleanly (skip).

## Step 6: トランスクリプト抽出
From the HTML of ted.com/talks/{slug}, find the script tag containing:
  q("talkPage.init", { ... JSON ... })

Extract the JSON. The transcript is typically under:
  data.talks[0].player_talks[0].transcript_paragraphs
or similar path. Adapt as needed based on actual HTML structure.

Each paragraph has:
- start time (seconds)
- text (with sentences inside)

## Step 7: 解説生成(全単語・全表現・全文)

For the entire transcript, generate JSON following the schema in /docs/data_schema.md.

KEY REQUIREMENTS:
1. **All words must be classified into one of 4 tiers** (basic/normal/key/frequent)
   - Refer to /prompts/word_classification.md for detailed criteria
   - Every word, including basic ones like "it" or "the", needs full data:
     - meaning, pos, pronunciation, example (with English+Japanese), context, collocations
2. **All idioms/multi-word expressions must be identified** and tagged
   - 2-tier classification (normal/frequent)
3. **Every sentence must have**:
   - Japanese translation
   - Syntactic structure breakdown (S/V/O/C labels with explanatory notes)
4. **Background information** at the talk level:
   - 1-paragraph summary (Japanese, ~150 chars)
   - 3-5 detail bullets (key concepts, narrator info, related fields)

Output format: STRICTLY follow /docs/data_schema.md.
DO NOT skip words to save tokens. Cost is not a concern.

## Step 8: JSON出力
Write to /data/talks/YYYY-MM-DD.json
Update /data/index.json by:
- Adding the new talk to the "talks" array (sorted by date desc)
- Updating "updated_at" timestamp

## Step 9: commit & push
git add /data/
git commit -m "daily: YYYY-MM-DD {ted-ed|ted-talks} {title}"
git push

# エラーハンドリング
- 何らかの失敗時は、原因をstderrに記録して非ゼロ終了
- 部分的なコミットはしない(成功時のみcommit/push)
- リトライは最大2回まで(主にネットワークエラー)

# 制限事項
- /data/ 以外のファイルは絶対に変更しない
- 既存のJSONを上書きしない(冪等性)
```

---

## プロンプトの保守

### 変更が必要になるシナリオ

1. **YouTube RSSの構造が変わった**: Step 3のXMLパース部分を更新
2. **TEDサイトのHTML構造が変わった**: Step 6のscript tag抽出ロジックを更新
3. **興味分野を追加・変更したい**: Step 4のカテゴリリストを更新
4. **データスキーマが進化した**: `/docs/data_schema.md` を更新し、Step 7の指示も合わせる

### Cloud Task側の設定

- cron式: `0 6 * * *` (JST 06:00)
- 連携リポジトリ: 本リポジトリ(private)
- 必要権限: Bash, Web fetch, ファイル編集, リポジトリ書き込み
- タイムアウト: デフォルト(30分)
- 実行通知: 失敗時のみ通知(設定方法はPhase 3で決定)
