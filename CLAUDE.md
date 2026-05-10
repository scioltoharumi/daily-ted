# CLAUDE.md

Daily TED PWA リポジトリのエージェント向けエントリポイント。Claude Code(Web版/Cloud Task/ローカル)からこのリポジトリを開いた際に最初に読むべき場所。

## 最初に読む

1. `docs/project_guide.md` — プロジェクト固有の運用ガイド(必読)
2. `docs/requirements_v3.md` — 要件定義書(SSoT)
3. `prompts/word_classification.md` — 単語階層判定基準

## 主要ディレクトリ

- `docs/` — 要件定義・データスキーマ・PoC 手順・UI モックアップ
- `prompts/` — Cloud Task / Scheduled Agent 用プロンプト(`daily_batch.md`)
- `scripts/` — Python ヘルパー
  - `fetch_ted_ed_videos.py` — YouTube TED-Ed channel HTML スクレイピングで新着取得
  - `fetch_youtube_transcript.py` — youtube-transcript-api で動画字幕取得
- `archive/` — 退役したスクリプト(D-016 で TED-Ed パスを YouTube 直結に変更したため、ted.com / RSS 関連スクリプトを退避)
- `data/` — Cloud Task が生成する JSON(`index.json`, `talks/YYYY-MM-DD.json`)
- `src/`, `public/` — Phase 2 で着手する PWA 実装ディレクトリ(現時点では未作成)
- `steering/` — 設計判断ログ・教訓ログ

## 入口

### 日次バッチ実行(Cloud Task / Scheduled Agent)

`prompts/daily_batch.md` の指示に厳密に従う。Step 1〜9 を順に実行し、成功時のみ commit & push する。

### 実装変更(Web版・ローカル)

1. `docs/requirements_v3.md` を読む(SSoT)
2. `steering/design_decisions.md` で既存方針を確認
3. 変更後、関連ドキュメントの更新も忘れない
4. 大きな仕様変更は `docs/requirements_v3.md` を更新し改訂履歴を残す

## 主要制約

- **配信ロジック**(D-016, v3.1): TED-Ed のみ毎日チェック / 新作なしならスキップ。TED Talks は学習者レベル不適合のため廃止
- **取得経路**(D-016): YouTube TED-Ed channel HTML スクレイピング + youtube-transcript-api。ted.com / RSS は使わない(TED-Ed は ted.com にほぼ存在せず、YouTube RSS は Made for Kids 設定で 404)
- **冪等性**: 同日の `data/talks/YYYY-MM-DD.json` 既存なら即終了
- **全単語事前生成**: PWA 側に AI フォールバック処理を作らない
- **コスト・著作権度外視**: MAX プラン + 私的利用前提
- **データ生成方針**: ハードコードのリストは作らない、Claude が文脈判定

## コミット規則

- 日次バッチ: `daily: YYYY-MM-DD <source> <title>`
- 実装: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

## トラブル時

- `steering/lessons.md` を確認 → 過去同パターンの記録があるか
- 解決後は同ファイルに追記して次回に備える
