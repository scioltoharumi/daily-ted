# プロジェクトガイド - Daily TED PWA

このプロジェクト(Daily TED)で作業を始めるときに読むガイド。
新しいセッションを開始する際は、このファイルと `docs/requirements_v3.md` を最初に読むこと。

---

## プロジェクト概要

**Daily TED** - TED-Ed/TED Talkを題材にした個人用英語学習PWA

- 学習者:1名(自分のみ)
- ホスティング:GitHub Pages
- バックエンド:Claude Code Cloud Task(日次バッチ)
- フロント:Svelte + Vite + Tailwind CSS
- データ:JSON静的ファイル + localStorage

詳細は `docs/requirements_v3.md` を参照。

---

## ディレクトリ構成(目標)

```
.
├── README.md                  # リポジトリ概要
├── docs/
│   ├── project_guide.md       # ←本ファイル(プロジェクト固有のガイド)
│   ├── requirements_v3.md     # 要件定義書(SSoT)
│   ├── data_schema.md         # JSON構造の正式定義
│   ├── poc_phase1.md          # Phase 1 PoC手順書
│   └── mockup_v5.html         # UI/UXモックアップ
├── prompts/                   # Cloud Task用プロンプト
│   ├── daily_batch.md         # 日次バッチのメインプロンプト
│   └── word_classification.md # 単語階層判定基準
├── scripts/                   # ヘルパースクリプト
│   ├── fetch_rss.py           # YouTube RSS取得
│   ├── scrape_transcript.py   # ted.com スクレイピング
│   └── slug_estimator.py      # YouTubeタイトル → ted.com slug推定
├── data/                      # Cloud Taskが生成するJSON(コミット対象)
│   ├── index.json             # Talk一覧
│   └── talks/
│       └── YYYY-MM-DD.json    # 各Talkの全データ
├── src/                       # PWAソース(Svelte)
│   ├── App.svelte
│   ├── lib/
│   │   ├── components/
│   │   ├── stores/
│   │   └── utils/
│   └── routes/
├── public/                    # PWA静的アセット
│   ├── manifest.json
│   └── icons/
├── steering/                  # プロジェクト方針メモ
│   ├── design_decisions.md    # 主要な意思決定の記録
│   └── lessons.md             # 失敗・教訓・改善点
└── package.json
```

---

## 重要な意思決定(必ず守ること)

### 配信ロジック
- **平日(月〜金)**: TED-Edのみ配信
- **休日(土日)**: TED Talksのみ配信、興味分野フィルター適用
- **新作なし**: スキップ。穴あきを容認。補完しない
- **同日にJSON既存**: 即時終了(冪等性)

### データ生成方針
- **全単語事前生成**: トランスクリプト中の全単語・全表現・全文を解説生成
- **AI即時生成は廃止**: PWA側にフォールバック処理を作らない
- **JSONサイズ膨らみは許容**: 1Talk 500KB前後

### 単語の4階層
- `basic`: 固有名詞・冠詞・基本語(視覚的に最も控えめ)
- `normal`: 一般的な学習対象語
- `key`: 学習価値が特に高い語(B2以上、専門用語)
- `frequent`: TOEFL/IELTS頻出 + AWL + 日常応用度高い語(★最も強調・黄色マーカー)

### 表現の2階層
- `normal`: 専門用語・複合名詞(青背景)
- `frequent`: 日常英語の必修慣用句(濃い青背景＋枠線＋太字)

### 階層判定責務
階層判定は**Cloud Task内のClaudeが行う**。ハードコードのリストは作らず、文脈と判定基準から都度決定する。

### コスト
MAXプラン契約のため**度外視**。モデル選定もOpus 4.7優先。プロンプト圧縮等の節約最適化は不要。

### 著作権
私的利用前提のため**度外視**。リポジトリは念のためprivateにするが、それ以外の対応は不要。

---

## 作業フロー

### 日次バッチ実行時(Cloud Task)
1. `prompts/daily_batch.md` を読む
2. プロンプトに従って RSS取得 → スクレイピング → 解説生成 → JSON出力 → commit & push を実行
3. 失敗時は理由をログに残す。部分コミットはしない

### コード変更時(Web版・Terminal版)
1. **最初に必ず `docs/requirements_v3.md` を読む**(SSoT)
2. 影響範囲のあるコードを確認
3. 既存の意思決定は `steering/design_decisions.md` で確認
4. 変更後、関連ドキュメントの更新も忘れない
5. 大きな仕様変更は `docs/requirements_v3.md` を更新し、改訂履歴を残す

### 実装中の判断
- 不明点があったら**勝手に決めずに必ず聞く**(特に仕様の解釈)
- 既存方針と矛盾する依頼があったら、矛盾を指摘して確認
- 「とりあえず動く実装」より「方針通りの正しい実装」優先
- 早すぎる最適化はしない

---

## 三層ルーティング(出力先の使い分け)

| 用途 | 出力先 | 例 |
|---|---|---|
| 設計判断・方針 | `docs/` | 要件定義、データスキーマ |
| 実装コード | `src/`, `scripts/` | Svelteコンポーネント、Pythonヘルパー |
| プロジェクト方針メモ | `steering/` | 失敗の教訓、判断基準のメモ |

---

## よくある間違い(避けてほしいこと)

1. **「とりあえず簡略化」しない**: 全単語事前生成方針を勝手に「重要語のみ」に変えるのはNG
2. **AIフォールバックを足さない**: PWA側で動的にAI呼び出しはしない(事前生成のみ)
3. **「コスト最適化」を勝手にしない**: MAXプラン前提なので不要
4. **基本語にも完全データ**: 固有名詞や`it's`等にも意味/発音/例文/コロケーション全部つける
5. **冪等性を破らない**: 同日のJSONがあるのに上書きしない
6. **ハードコードのデータを作らない**: 単語リスト・分類リスト等はプロンプトで判定、コード内固定値にしない

---

## 開発の現在地(更新する)

**Phase**: Phase 0(設計完了 → Phase 1 PoC着手予定)

**直近のTODO**:
- [ ] GitHubリポジトリ作成(private)
- [ ] Phase 1 PoC実施(`docs/poc_phase1.md`)
  - [ ] YouTube RSS実取得テスト
  - [ ] slug推定の的中率測定(直近20本)
  - [ ] ted.com スクレイピング動作確認
  - [ ] Cloud Task手動実行で1日分試走
- [ ] プロンプトチューニング(1〜2サイクル)
- [ ] PWAスケルトン構築
- [ ] Cloud Task本登録(cron 0 6 * * * JST)

---

## 連絡事項・運用ルール

- コミットメッセージ:`daily: YYYY-MM-DD <source> <title>` (バッチ)、`feat:`, `fix:`, `docs:`, `refactor:` (実装)
- ブランチ:基本mainで、大きな仕様変更時のみfeature branch
- ドキュメント更新:仕様変更があったら必ず `docs/requirements_v3.md` を更新し改訂履歴を残す

---

## 関連リソース

- 要件定義: `docs/requirements_v3.md`
- データスキーマ: `docs/data_schema.md`
- バッチプロンプト: `prompts/daily_batch.md`
- 単語分類基準: `prompts/word_classification.md`
- PoC手順: `docs/poc_phase1.md`
- UIモックアップ: `docs/mockup_v5.html`
- 設計判断ログ: `steering/design_decisions.md`
- 教訓ログ: `steering/lessons.md`
