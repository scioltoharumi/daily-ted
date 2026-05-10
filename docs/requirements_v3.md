# TED英語学習PWA 要件定義書 v3.1

作成日:2026-05-07 / 改訂日:2026-05-10 / 作成者:匠 / 対象:Claude Code実装担当

---

## 0. 本書の位置付け

本書は、TED-Edを題材とした個人用英語学習PWAの正式な要件定義書である。Claude Code(Web版・Cloud Task / Scheduled Agent)による実装を前提とする。著作権上の論点は私的利用範囲として全て度外視する前提で記述している。

> **v3.1 重要変更点**: Phase 1 PoC(2026-05-10)で v3.0 の前提が崩壊したため、TED-Ed取得を YouTube 直結フローに変更し、TED Talks 配信は廃止した。
> 詳細は `steering/design_decisions.md` D-016 と `steering/lessons.md` を参照。
> 主要な変更:
>
> - **配信ソース**: 平日 TED-Ed / 休日 TED Talks → **TED-Ed のみ(毎日チェック)**
> - **新着取得**: YouTube RSS → **`youtube.com/@TEDEd/videos` の HTML スクレイピング(`ytInitialData` 抽出)**
> - **transcript 取得**: ted.com スクレイピング → **`youtube-transcript-api`**
> - **slug 推定**: 廃止(YouTube videoId を直接使う)
> - **興味分野フィルター**: 廃止(TED-Ed のみのため不要)
>
> 本文中の各セクション(特に 2.1 / 2.2 / 3 / 4.1 / 8 / 9)は v3.0 の記述が残っている箇所がある。実装時は本書冒頭の v3.1 変更点と D-016 を優先すること。詳細セクションの全面改訂は次回セッションで実施予定。

---

## 1. プロジェクト概要

### 1.1 目的
日次配信されるTED-EdおよびTED Talkを題材に、トランスクリプト上の単語・表現・構文をタップして解説を引き出しながら、英語を総合的に学習できるPWAを構築する。

### 1.2 学習者
1名(自分のみ)、中級〜上級英語学習者。スマホ・PC両用、主にスマホ。

### 1.3 学習方針
- 「読書型」学習体験。読みながらタップで調べる
- 語彙・表現・構文のバランス重視
- 復習(SRS)機能はMVP対象外、Phase 4以降

### 1.4 スコープ外(MVP)
- 復習機能・SRS・既習フラグ
- 進捗管理・学習履歴
- 多人数共有・SNS要素
- ネイティブアプリ化
- 過去ライブラリからの補完
- 動的「面白さ判定」

---

## 2. システムアーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────┐
│  Claude Code Cloud Task                      │
│  cron: 0 6 * * * (JST、Anthropic基盤)         │
│                                              │
│  1. 曜日判定                                  │
│     ├ 月〜金 → TED-Ed YouTube RSS             │
│     └ 土〜日 → TED Talks YouTube RSS          │
│                  + 興味分野フィルター         │
│                                              │
│  2. 過去24h以内の新作チェック                │
│     └ 候補0件 → スキップ終了                  │
│                                              │
│  3. ted.com/talks/{slug} 推定 + スクレイピング│
│     └ 404 → スキップ終了                      │
│                                              │
│  4. transcript抽出(HTML内JSON)                │
│  5. Claude(Opus 4.7)で全単語・全表現・全文を   │
│     事前生成 → JSON                           │
│  6. git commit & push                         │
└──────────────────┬──────────────────────────┘
                   │ push
        ┌──────────▼──────────┐
        │ GitHub repo (private)│
        │  /data/talks/*.json │
        │  /data/index.json   │
        └──────────┬──────────┘
                   │ auto-deploy
        ┌──────────▼──────────┐
        │ GitHub Pages         │
        │ (static PWA hosting) │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │ PWA (Svelte + Vite) │
        │  - JSON fetch       │
        │  - localStorage     │
        │    (お気に入り)      │
        └─────────────────────┘
```

### 2.2 技術スタック

| レイヤー | 採用 |
|---|---|
| バックエンド実行環境 | Claude Code Cloud Task |
| AIモデル | Claude Opus 4.7(品質優先・MAXプラン契約のため度外視) |
| ソース管理 | GitHub(privateリポジトリ) |
| ホスティング | GitHub Pages |
| フロントFW | Svelte + Vite |
| スタイル | Tailwind CSS |
| クライアント永続化 | localStorage |
| 動画埋め込み | TED公式embed iframe(`embed.ted.com/talks/{slug}`) |
| トランスクリプト取得 | ted.com/talks/{slug} スクレイピング |
| RSS取得 | YouTube公式RSS(`youtube.com/feeds/videos.xml?channel_id=...`) |

### 2.3 YouTube Channel ID

| ソース | Channel ID | RSS URL |
|---|---|---|
| TED Talks | `UCAuUUnT6oDeKwE6v1NGQxug` | `https://www.youtube.com/feeds/videos.xml?channel_id=UCAuUUnT6oDeKwE6v1NGQxug` |
| TED-Ed | `UCsooa4yRKGN_zEE8iknghZA` | `https://www.youtube.com/feeds/videos.xml?channel_id=UCsooa4yRKGN_zEE8iknghZA` |

---

## 3. 配信ルール

### 3.1 配信ソース

| 曜日 | ソース | 補足 |
|---|---|---|
| 月〜金 | TED-Ed のみ | 新作なしならスキップ |
| 土・日 | TED Talks のみ | 興味分野フィルター適用、該当なしならスキップ |

### 3.2 興味分野フィルター(休日TED Talks用)

- Science (physics, math, biology, chemistry, neuroscience, space)
- Technology (AI, computer science, engineering)
- Philosophy & Psychology
- Linguistics & Communication
- Economics & Finance
- Creativity & Storytelling

YouTube RSSにはタグ情報が含まれないため、**Claudeがタイトル・説明文を読んで判定**する方式を採用。

### 3.3 スキップポリシー

「新作あれば配信、なければスキップ」を確定方針とする。穴あきを容認。
冪等性のため、同日の/data/talks/YYYY-MM-DD.jsonが既存ならバッチは即終了。

### 3.4 slug推定ロジック(TED-Ed)

YouTube動画タイトルから ted.com/talks の slug を機械的に推定：
- TED-Edの場合、`ted_ed_<title-snake-case>` パターン
- 例：「The fascinating reason you loved peek-a-boo」 → `ted_ed_the_fascinating_reason_you_loved_peek_a_boo`
- 変換ルール:小文字化、空白を `_`、ハイフンを `_`、特殊文字を除去
- 推定URLにアクセス → 404ならスキップ、200なら次へ

---

## 4. 機能要件

### 4.1 バックエンド(Cloud Task)

| ID | 機能 | 詳細 |
|---|---|---|
| F-01 | 曜日判定 | JSTで実行日が平日/休日かを判定 |
| F-02 | YouTube RSS取得 | TED-Ed or TED Talksのチャンネルから直近動画を取得 |
| F-03 | 新作判定 | 過去24時間以内の動画を抽出、候補0件ならスキップ |
| F-04 | 興味分野フィルター(休日のみ) | Claudeがタイトル・概要から判定 |
| F-05 | slug推定 | YouTube動画タイトルからted.com/talksのURLを推定 |
| F-06 | スクレイピング | ted.com/talks/{slug}/transcript からHTML内 `q("talkPage.init", {...})` JSONを抽出 |
| F-07 | 解説事前生成 | 全単語・全表現・全文の解説をClaudeで生成 |
| F-08 | JSON出力 | /data/talks/YYYY-MM-DD.json に保存 |
| F-09 | index更新 | /data/index.json に追加(日付降順) |
| F-10 | git commit & push | "daily: YYYY-MM-DD <source> <title>" 形式 |

### 4.2 フロントエンド(PWA)

| ID | 機能 | 詳細 |
|---|---|---|
| F-11 | PWA配信 | スマホブラウザ・ホーム画面追加対応 |
| F-12 | Service Worker | オフライン閲覧キャッシュ |
| F-13 | カード一覧 | 直近Talkを日付順表示、本日カードを大きく |
| F-14 | スキップ日表示 | "— Mon, May 7 — no new release —" 形式で詰めて表示 |
| F-15 | ソース識別バッジ | 🎓 TED-Ed(琥珀)/ 🎤 TED(赤) |
| F-16 | 動画埋め込み | `<iframe src="https://embed.ted.com/talks/{slug}">` |
| F-17 | 背景情報カード | Talk冒頭に背景・関連分野・ナレーター情報、展開可 |
| F-18 | トランスクリプト表示 | タイムスタンプ付き、4階層強調 |
| F-19 | 単語タップ | basic/normal/key/frequentの4階層、全単語タップ可 |
| F-20 | 表現タップ | normal/frequentの2階層、青背景 |
| F-21 | 文タップ | 文末⌘アイコン、ホバーで対象範囲を紫の縦線で表示 |
| F-22 | モーダル表示 | 下からスライドアップ、4セクション(意味/例文/背景/コロケーション) |
| F-23 | 発音再生 | Web Speech APIによる音声読み上げ |
| F-24 | お気に入り登録 | ★ボタンでlocalStorageに保存 |
| F-25 | お気に入り一覧 | Talk別グルーピング、Words/Expressions/Sentences絞り込み |
| F-26 | エクスポート | Markdown/CSV/Anki(.apkg) |

---

## 5. 単語の階層定義

### 5.1 4階層の判定基準

| 階層 | 視覚 | 判定基準 |
|---|---|---|
| **basic** | 薄いグレードット下線(極小) | 固有名詞(国名・人名・地名)、冠詞、A1基本語の中でも使い回しが少ないもの |
| **normal** | 薄い琥珀ドット下線 | 一般的な学習対象語(A2-B1)で、特に頻出ではない語 |
| **key** | 濃い琥珀ドット下線 | 学習価値が特に高い語(B2以上、専門用語、ニュアンス豊富な語) |
| **★ frequent** | 黄色マーカー＋太字 | TOEFL/IELTS/英検準1級〜1級頻出語 + AWL(Academic Word List) + 日常応用が効く動詞・形容詞 |

### 5.2 表現の2階層

| 階層 | 視覚 | 判定基準 |
|---|---|---|
| **normal expression** | 青背景＋下線 | 専門用語・複合名詞・分野特定的な表現 |
| **★ frequent expression** | 濃い青背景＋枠線＋太字 | 日常英語で実用度が高い慣用句・イディオム・必修表現 |

### 5.3 階層判定の責務

階層判定は**Cloud Task内のClaudeが行う**。プロンプトに基準を明記し、各単語にtierフィールドを必ず付与する。

---

## 6. データモデル

### 6.1 Talk JSON

```json
{
  "id": "talk_2026-05-07",
  "date": "2026-05-07",
  "source": "ted-ed",
  "category": "Psychology",
  "slug": "ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  "title": "The fascinating reason you loved peek-a-boo",
  "speaker": "Alexandra Panzer",
  "duration_sec": 308,
  "video_url": "https://www.ted.com/talks/ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  "embed_url": "https://embed.ted.com/talks/ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  "background": {
    "summary": "「いないいないばあ」(peek-a-boo)は、ほぼ全文化に存在する乳児向けの遊び。本Talkは、なぜ赤ちゃんがこの単純な遊びを楽しむのかを発達心理学のキー概念「対象の永続性」から解説する。",
    "details": [
      "対象の永続性:ジャン・ピアジェが提唱した概念。生後8〜12ヶ月頃に獲得される認知能力。",
      "ナレーター:Alexandra Panzer (TED-Ed常連)。",
      "関連分野:発達心理学 / 認知発達 / Serve-and-return理論"
    ]
  },
  "transcript": [
    {
      "id": "p1",
      "start_sec": 0,
      "sentences": [
        {
          "id": "s1",
          "text": "In Italy, it's called il gioco del cucù.",
          "translation_ja": "イタリアでは il gioco del cucù と呼ばれる。",
          "structure": [
            { "label": "前置詞句", "content": "In Italy", "note": "場所を示す副詞句が文頭" },
            { "label": "S+V", "content": "it's called", "note": "受動態" },
            { "label": "C", "content": "il gioco del cucù", "note": "イタリア語の固有名詞句" }
          ],
          "tokens": [
            { "id": "t1", "surface": "In", "type": "skip" },
            { "id": "t2", "surface": "Italy", "type": "word", "tier": "basic", "ref": "italy" },
            { "id": "t3", "surface": ",", "type": "skip" },
            { "id": "t4", "surface": "it's", "type": "word", "tier": "basic", "ref": "it" },
            { "id": "t5", "surface": "called", "type": "word", "tier": "normal", "ref": "called" },
            { "id": "t6", "surface": "il gioco del cucù", "type": "foreign", "ref": "il_gioco" }
          ]
        }
      ]
    }
  ],
  "words": {
    "italy": {
      "tier": "basic",
      "surface": "Italy",
      "pos": "proper noun",
      "pron": "/ˈɪt.ə.li/",
      "meaning": "イタリア(ヨーロッパの国)",
      "example": {
        "en": "She studied art in <b>Italy</b>.",
        "ja": "彼女はイタリアで美術を学んだ。"
      },
      "context": "正式国名 Italian Republic、首都 Rome。",
      "collocations": ["go to Italy", "made in Italy"]
    },
    "fascinating": {
      "tier": "frequent",
      "surface": "fascinating",
      "pos": "adj · B1",
      "pron": "/ˈfæs.ɪ.neɪ.tɪŋ/",
      "meaning": "魅力的な、興味をそそる",
      "example": {
        "en": "It was a <b>fascinating</b> book.",
        "ja": "それは興味深い本だった。"
      },
      "context": "interestingより強い感情を伴う。fascinate(魅了する)の現在分詞形。",
      "collocations": ["fascinating story", "absolutely fascinating"]
    }
  },
  "expressions": {
    "might_as_well": {
      "tier": "frequent",
      "surface": "might as well",
      "pos": "idiom",
      "pron": "/maɪt æz wel/",
      "literal": "~するのも同様に良い",
      "meaning": "~したのも同じだ / ~してもよい(消極的提案)",
      "context": "仮定法と組み合わせて「事実上~である」を表す。日常会話で頻用される必修表現。",
      "collocations": ["might as well give up", "you might as well"]
    }
  }
}
```

### 6.2 Index JSON

```json
{
  "updated_at": "2026-05-07T06:30:00+09:00",
  "talks": [
    {
      "id": "talk_2026-05-07",
      "date": "2026-05-07",
      "source": "ted-ed",
      "category": "Psychology",
      "title": "The fascinating reason you loved peek-a-boo",
      "speaker": "Alexandra Panzer",
      "duration_sec": 308,
      "thumbnail_url": "https://..."
    }
  ],
  "skipped_dates": ["2026-05-06", "2026-05-05"]
}
```

### 6.3 お気に入り(localStorage)

```json
{
  "favorites": [
    {
      "id": "fav_001",
      "talk_id": "talk_2026-05-07",
      "type": "word",
      "ref": "fascinating",
      "surface": "fascinating",
      "ja": "魅力的な、興味をそそる",
      "saved_at": "2026-05-07T08:30:00Z"
    }
  ]
}
```

---

## 7. 非機能要件

| 項目 | 要件 |
|---|---|
| パフォーマンス | カード一覧表示<2秒、タップ応答<200ms |
| オフライン | Service Workerで一度開いた記事はキャッシュ |
| 対応ブラウザ | iOS Safari / Android Chrome 最新2世代、PC Chrome/Edge |
| 配信ホスティング | GitHub Pages |
| バックエンド | Claude Code Cloud Task(MAXプラン内) |
| データ永続化 | localStorage(端末1台前提、エクスポートでバックアップ可) |
| 冪等性 | バッチ再実行時、同日のJSON既存ならスキップ |
| 1Talk JSONサイズ | 500KB前後を想定(全単語事前生成、許容) |
| Cloud Task実行時間 | 30分以内に収める。実測でチューニング |

---

## 8. リスク・要検証事項

| ID | リスク | 影響 | 対応 |
|---|---|---|---|
| R-01 | YouTube RSS構造変更 | 中 | XMLパースを柔軟にする、エラー時は通知 |
| R-02 | TED-EdがTED.comに未掲載のケース | 高 | slug推定→404ならスキップ。比率を実測してフォールバック検討 |
| R-03 | TEDサイトのHTML構造変更(`talkPage.init`) | 中 | Claudeに柔軟にHTML解析させる、フォールバック実装 |
| R-04 | Cloud Task実行時間オーバー | 中 | 段落並列処理、または重要度が低い段落の解説簡略化 |
| R-05 | 興味分野フィルターのヒット率低下 | 中 | フィルター緩和、あるいはフィルター無効化オプション |
| R-06 | YouTube動画タイトルとted.comのslug不一致 | 中 | フォールバック:ted.comサイト内検索 |
| R-07 | Cloud Taskのリポジトリ書き込み権限 | 中 | 連携設定で書き込み許可、初回手動実行で検証 |
| R-08 | 解説精度のバラつき | 中 | プロンプトをスキーマ厳格化、リトライ実装 |

---

## 9. 開発フェーズ

### Phase 1:技術検証(3〜7日)
- TED-Ed YouTube RSS実構造確認
- ted.com/talks スクレイピング動作確認
- slug推定の的中率実測(直近20本)
- Cloud Task手動実行で1日分試走
- プロンプトチューニング1〜2回

### Phase 2:MVP実装(2〜4週間)
- Cloud Taskプロンプト本実装＋スケジュール登録
- PWA基本UI(Svelte + Tailwind)
- 4階層強調・モーダル・ソースバッジ実装
- お気に入り(localStorage)＋エクスポート

### Phase 3:運用安定化(継続)
- Cloud Task失敗通知
- プロンプト精度のチューニング
- 興味分野フィルター調整

### Phase 4以降:拡張
- SRS復習機能
- 既習フラグ
- 学習履歴ダッシュボード
- 単語音声読み上げの拡充

---

## 10. 成功指標

- 配信があった日の閲覧率80%以上
- 月の配信数15本以上(平日+休日のうち新作あり日)
- お気に入り登録月20件以上
- Cloud Task成功率95%以上
- バッチ起因のトラブルシュート時間月1時間以内

---

## 11. 参考:UI/UXモックアップ

最新版モックアップ:`docs/mockup_v5.html`(別添)

主要UI仕様:
- 動画は冒頭に16:9埋め込み、TED公式embedプレイヤー使用
- 背景情報カードは展開可、Talk冒頭に配置
- トランスクリプトは Fraunces (variable serif) で表示、行高1.85
- カラー:`--paper #fafaf7`、`--ed-amber #c4870a`、`--highlight-yellow #fff09c`、`--highlight-blue #e7f0ff`
- 文ホバー時に左側に紫の縦線、文末⌘アイコンが構文解析エントリポイント
- モーダルは下からスライドアップ、85vh max、ハンドル付き

---

## 12. 改訂履歴

- v1.0 (2026-05-07) 初版(GitHub Actions + Anthropic API構成)
- v2.0 (2026-05-07) Claude Code Cloud Task採用、コスト議論撤廃
- v2.1 (2026-05-07) ソース2系統化(TED-Ed + TED Talks)、平日/休日切替
- v3.0 (2026-05-07) 全単語事前生成、4階層強調、固有名詞basic化、UI/UX確定
- v3.1 (2026-05-10) D-016採用、TED-Ed YouTube直結フローに変更、TED Talks廃止、ted.com 経路廃止、`youtube-transcript-api` 依存追加。Phase 1 PoC で v3.0 の前提崩壊を確認。
