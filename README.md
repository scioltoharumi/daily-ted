# 引き継ぎ資料一覧 - Daily TED PWA

このフォルダはClaude Codeへの引き継ぎ用ドキュメント一式です。
**作業を開始する人(Claude含む)は、このREADMEから読んでください。**

---

## 引き継ぎ資料の使い方

### 1. まずこれを読む(順番に)
1. `README.md` (このファイル) - 全体マップ
2. `docs/project_guide.md` - プロジェクト固有のガイド、必読
3. `docs/requirements_v3.md` - 正式な要件定義書(SSoT)

### 2. 設計判断を確認する
- `steering/design_decisions.md` - 主要な意思決定とその背景
- `steering/lessons.md` - 失敗・教訓ログ(運用しながら追記)

### 3. データ仕様を確認する
- `docs/data_schema.md` - JSON構造の正式定義
- `docs/mockup_v5.html` - UI/UXモックアップ(ブラウザで開く)

### 4. Cloud Task登録時に使う
- `prompts/daily_batch.md` - メインプロンプト(Cloud Taskにそのまま登録)
- `prompts/word_classification.md` - 単語階層判定基準

### 5. Phase 1 PoCを始めるとき
- `docs/poc_phase1.md` - PoC手順書、各ステップの確認項目
- `scripts/fetch_rss.py` - YouTube RSS取得テスト用
- `scripts/slug_estimator.py` - slug推定テスト用
- `scripts/scrape_transcript.py` - スクレイピングテスト用

---

## ディレクトリ構成

```
ted-pwa-handover/
├── README.md                          # ←今ここ(引き継ぎ入口)
├── docs/
│   ├── project_guide.md               # プロジェクト固有のガイド
│   ├── requirements_v3.md             # 要件定義書 v3.0(SSoT)
│   ├── data_schema.md                 # JSON構造の正式定義
│   ├── poc_phase1.md                  # Phase 1 PoC手順書
│   └── mockup_v5.html                 # UI/UXモックアップ
├── prompts/
│   ├── daily_batch.md                 # Cloud Task用プロンプト
│   └── word_classification.md         # 単語階層判定基準
├── scripts/
│   ├── fetch_rss.py                   # YouTube RSS取得
│   ├── slug_estimator.py              # slug推定 + URL存在確認
│   └── scrape_transcript.py           # ted.com スクレイピング
└── steering/
    ├── design_decisions.md            # 主要設計判断ログ(D-001〜D-015)
    └── lessons.md                     # 失敗・教訓ログ(運用追記)
```

---

## このプロジェクトの本質を5分で理解するための要約

### やりたいこと
個人用の英語学習PWA。毎日のTED-Ed/TED Talkを動画で見ながら、
トランスクリプトの**全単語**にタップで意味・例文・背景・コロケーションが出る。

### どう作るか
- バックエンド:Claude Code Cloud Taskが毎朝6時に実行(MAXプラン)
- 処理:RSS取得 → ted.com スクレイピング → Claudeが全要素解説生成 → JSON commit
- フロント:Svelte PWAがJSONを読んで表示するだけ
- 動画:TED公式embedで埋め込み

### キーポイント
1. **配信ロジック**:平日 TED-Ed / 休日 TED Talks / 新作なしならスキップ
2. **事前生成徹底**:全単語×完全データを事前にJSON化、AI即時生成は使わない
3. **4階層強調**:basic/normal/key/frequentで重要度を視覚化(★frequentは黄色マーカー)
4. **冪等性**:同日のJSONがあれば即終了
5. **コスト・著作権度外視**:MAXプラン+私的利用前提

### 何が決まっていて、何が未確定か

**確定**:
- アーキテクチャ全体
- 配信ロジック・スキップポリシー
- データスキーマ
- UI/UX(モックアップで具体化済)
- 単語階層の判定基準

**未確定**(Phase 1 PoCで詰める):
- slug推定の的中率(実測必要)
- TEDサイトHTML構造の現状
- Cloud Taskの実環境動作
- 解説生成プロンプトのチューニング

---

## 始め方(推奨順)

### Step 0: 環境準備
1. GitHubでprivateリポジトリを作成
2. このフォルダの中身をリポジトリにコピー
3. Claude Codeで対象リポジトリを開く

### Step 1: PoC着手(`docs/poc_phase1.md` の手順)
1. **Step 1**: `python scripts/fetch_rss.py ted-ed` でRSS取得テスト
2. **Step 2**: 直近20本のTED-Edで `python scripts/slug_estimator.py` 実行、的中率測定
3. **Step 3**: `python scripts/scrape_transcript.py <slug>` で1本だけスクレイピング動作確認
4. **Step 4**: Cloud Taskに `prompts/daily_batch.md` を登録、手動実行で1日分試走
5. **Step 5**: 出力JSONの品質を確認、プロンプトをチューニング

### Step 2: PWA実装(Phase 2)
1. Svelte + Vite で初期化
2. モックアップ(`docs/mockup_v5.html`)を見ながらコンポーネント分解
3. 4階層スタイル、モーダル、お気に入り、エクスポート実装
4. PWA化(manifest, Service Worker)
5. GitHub Pagesデプロイ確認

### Step 3: 本運用開始
1. Cloud Taskのcronを `0 6 * * *` JSTで有効化
2. 数日運用してCloud Task成功率を観察
3. 問題があれば `steering/lessons.md` に記録、改善

---

## 困ったときの参照先

| 状況 | 見るべきドキュメント |
|---|---|
| 仕様の判断に迷った | `docs/requirements_v3.md` |
| 「なんでこう決めたんだっけ」 | `steering/design_decisions.md` |
| データ構造を確認したい | `docs/data_schema.md` |
| Cloud Taskプロンプトを編集したい | `prompts/daily_batch.md` |
| 単語階層判定の基準が知りたい | `prompts/word_classification.md` |
| UIの見た目を確認したい | `docs/mockup_v5.html` |
| PoCのチェックリスト | `docs/poc_phase1.md` |
| 過去の失敗・教訓 | `steering/lessons.md` |

---

## 連絡事項

- 開始日:2026-05-07
- 想定期間:Phase 1(1週間) + Phase 2(2-4週間) + 運用継続
- 著作権・コスト:私的利用 + MAXプランのため度外視

---

## 改訂履歴

- 2026-05-07: 初版作成、要件定義 v3.0 ベース
