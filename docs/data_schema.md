# データスキーマ仕様

PWAが読み込むJSONの正式定義。Cloud Taskが生成し、PWAが消費する。

---

## ファイル構成

```
/data/
├── index.json              # Talk一覧(PWAが最初に読む)
└── talks/
    └── YYYY-MM-DD.json     # 各Talkの完全データ
```

---

## /data/index.json

```typescript
interface IndexJson {
  updated_at: string;        // ISO 8601 (e.g., "2026-05-07T06:30:00+09:00")
  talks: TalkSummary[];      // 配信されたTalk一覧(date降順)
  skipped_dates: string[];   // YYYY-MM-DD形式、可視化用(任意)
}

interface TalkSummary {
  id: string;                // "talk_YYYY-MM-DD"
  date: string;              // YYYY-MM-DD
  source: "ted-ed";          // v3.1 で TED Talks 廃止 (D-016)、現在は "ted-ed" 固定
  category?: string;         // 旧フィールド(D-015 で TED Talks 用、現在は使用しない)

  // v3.2 (D-203) 追加:PWA のビュー D / E のため必須
  primary_topic: string;     // 主トピック (例: "Psychology", "Science", "Geology")
  tags: string[];            // 細かい分類 (例: ["volcano", "iceland", "lava-flow"])
  difficulty: "easy" | "medium" | "hard";  // 学習難易度の Claude 判定

  title: string;
  speaker: string;
  duration_sec: number;
  thumbnail_url?: string;    // ted.com の primaryImageSet (16x9) URL
  published_at?: string;     // v3.3 (D-019): ted.com publishedAt (ISO 8601 / UTC)
}
```

### 例

```json
{
  "updated_at": "2026-05-07T06:30:00+09:00",
  "talks": [
    {
      "id": "talk_2026-05-07",
      "date": "2026-05-07",
      "source": "ted-ed",
      "title": "The fascinating reason you loved peek-a-boo",
      "speaker": "Alexandra Panzer",
      "duration_sec": 308,
      "thumbnail_url": "https://i.ytimg.com/vi/XXX/maxresdefault.jpg"
    },
    {
      "id": "talk_2026-05-04",
      "date": "2026-05-04",
      "source": "ted-talks",
      "category": "Philosophy",
      "title": "Why the future of AI depends on philosophy",
      "speaker": "Jane Smith",
      "duration_sec": 684
    }
  ],
  "skipped_dates": ["2026-05-06", "2026-05-05"]
}
```

---

## /data/talks/YYYY-MM-DD.json

```typescript
interface TalkJson {
  // メタ情報
  id: string;
  date: string;
  source: "ted-ed";                   // v3.1 で TED Talks 廃止、"ted-ed" 固定
  category?: string;                  // 旧フィールド(使用しない)

  // v3.2 (D-203) 追加
  primary_topic: string;              // 主トピック
  tags: string[];                     // 細かい分類
  difficulty: "easy" | "medium" | "hard";

  slug: string;                       // v3.3 (D-019): ted.com の talk slug (canonicalUrl 末尾)
  video_id: string;                   // v3.3 (D-019): ted.com の数値 video id ("178996" 等)。v3.1 の YouTube videoId からセマンティクス変更
  title: string;
  speaker: string;
  duration_sec: number;
  published_at?: string;              // v3.3: ted.com publishedAt (ISO 8601 / UTC)
  video_url: string;                  // v3.3: https://www.ted.com/talks/{slug}
  embed_url: string;                  // v3.3: https://embed.ted.com/talks/{slug}
  thumbnail_url?: string;             // v3.3: ted.com primaryImageSet 16x9
  
  // 背景情報(Talk冒頭に表示)
  background: {
    summary: string;                  // 150字程度の概要(日本語)
    details: string[];                // 3-5個の詳細項目(日本語、"見出し: 本文" 等の自由文字列)
  };

  // v3.4 / D-204: 段落単位の日本語要約(背景とトランスクリプトの間に表示)
  // transcript の paragraphs と paragraph_id で 1対1 対応。順序も一致させる。
  // 合計 1000 字以内、各段落 80-150 字目安。
  paragraph_summaries_ja: Array<{
    paragraph_id: string;             // "p1", "p2", ... — transcript.Paragraph.id と一致
    summary: string;                  // 該当段落の日本語要約
  }>;

  // トランスクリプト(段落・文・トークンの3階層)
  transcript: Paragraph[];
  
  // 単語の解説辞書(token.refから参照)
  words: { [refKey: string]: WordEntry };
  
  // 表現の解説辞書(token.refから参照)
  expressions: { [refKey: string]: ExpressionEntry };
}

interface Paragraph {
  id: string;                         // "p1", "p2", ...
  start_sec: number;                  // 段落開始時刻(秒)
  sentences: Sentence[];
}

interface Sentence {
  id: string;                         // "s1", "s2", ...
  text: string;                       // 文全体の英語テキスト
  translation_ja: string;             // 日本語訳
  structure: SyntaxElement[];         // 構文解析
  tokens: Token[];                    // トークン列
}

interface SyntaxElement {
  label: string;                      // "S", "V", "O", "C", "副詞句", "関係節" 等
  content: string;                    // 該当する英語フレーズ
  note?: string;                      // 解説(任意)
}

interface Token {
  id: string;                         // "t1", "t2", ...
  surface: string;                    // 表面形(コンマ・ピリオド等の記号も含む)
  type: "word" | "expression" | "foreign" | "skip";
  // type === "word" or "expression" or "foreign": refで辞書参照
  ref?: string;                       // wordsまたはexpressionsのキー
  tier?: "basic" | "normal" | "key" | "frequent";  // wordのみ
}

interface WordEntry {
  tier: "basic" | "normal" | "key" | "frequent";
  surface: string;                    // 表面形(複数形・過去形など、本文の見たまま)
  pos: string;                        // 品詞 + CEFRレベル "adj · B2"
  pron: string;                       // 発音記号 IPA
  meaning: string;                    // 日本語意味
  example: {
    en: string;                       // 英語例文(該当語を<b>...</b>で囲む)
    ja: string;                       // 日本語訳
  };
  context: string;                    // 背景・ニュアンス・派生語等(日本語)
  collocations: string[];             // よく使う組み合わせ
}

interface ExpressionEntry {
  tier: "normal" | "frequent";
  surface: string;                    // 本文中の表面形
  pos: string;                        // "idiom", "phrasal verb", "noun phrase" 等
  pron: string;                       // 発音記号
  literal: string;                    // 直訳(日本語)
  meaning: string;                    // 意訳・実際の意味(日本語)
  context: string;                    // 背景・文化(日本語)
  collocations: string[];             // 関連表現
}
```

### 完全な例(抜粋)

```json
{
  "id": "talk_2026-05-07",
  "date": "2026-05-07",
  "source": "ted-ed",
  "slug": "ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  "video_id": "177595",
  "title": "The fascinating reason you loved peek-a-boo",
  "speaker": "TED-Ed",
  "duration_sec": 308,
  "published_at": "2026-04-30T15:31:20Z",
  "video_url": "https://www.ted.com/talks/ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  "embed_url": "https://embed.ted.com/talks/ted_ed_the_fascinating_reason_you_loved_peek_a_boo",
  
  "background": {
    "summary": "「いないいないばあ」(peek-a-boo)は、ほぼ全文化に存在する乳児向けの遊び。本Talkは、なぜ赤ちゃんがこの単純な遊びを楽しむのかを発達心理学のキー概念「対象の永続性」から解説する。",
    "details": [
      "対象の永続性:ジャン・ピアジェが提唱した概念。生後8〜12ヶ月頃に獲得される認知能力で、「物が見えなくなっても存在し続けている」と理解できるようになる発達上のマイルストーン。",
      "ナレーター:Alexandra Panzer (TED-Edの常連ナレーター。聞き取りやすい標準英語)",
      "アニメーション:Homework Studio",
      "関連分野:発達心理学 / 認知発達 / Serve-and-return理論"
    ]
  },

  "paragraph_summaries_ja": [
    {"paragraph_id": "p1", "summary": "イタリア語の cucù、パレスチナの ba''éno、日本の「いないいないばあ」── 言語は違えど世界中の乳児が同じく笑う。最初に遊ぶこのおどけたゲームの魅力とは?"},
    {"paragraph_id": "p2", "summary": "1936年ピアジェが乳児発達を初めて体系化。現代では境界は流動的とされるが、彼が特定した初期段階こそ peek-a-boo を理解する鍵となる。"}
  ],

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
            { "id": "t3", "surface": ", ", "type": "skip" },
            { "id": "t4", "surface": "it's", "type": "word", "tier": "basic", "ref": "it_s" },
            { "id": "t5", "surface": " ", "type": "skip" },
            { "id": "t6", "surface": "called", "type": "word", "tier": "normal", "ref": "called" },
            { "id": "t7", "surface": " ", "type": "skip" },
            { "id": "t8", "surface": "il gioco del cucù", "type": "foreign", "ref": "il_gioco" },
            { "id": "t9", "surface": ".", "type": "skip" }
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
      "context": "正式国名 Italian Republic、首都 Rome。形容詞形 Italian、人は the Italians。",
      "collocations": ["go to Italy", "made in Italy", "northern Italy"]
    },
    "fascinating": {
      "tier": "frequent",
      "surface": "fascinating",
      "pos": "adj · B1",
      "pron": "/ˈfæs.ɪ.neɪ.tɪŋ/",
      "meaning": "魅力的な、興味をそそる、心を奪うような",
      "example": {
        "en": "It was a <b>fascinating</b> book.",
        "ja": "それは興味深い本だった。"
      },
      "context": "interestingより強い感情を伴う。fascinate(魅了する)の現在分詞形。語源はラテン語のfascinare(魔法をかける)。",
      "collocations": ["fascinating story", "absolutely fascinating", "fascinating to watch"]
    }
  },
  
  "expressions": {
    "il_gioco": {
      "tier": "normal",
      "surface": "il gioco del cucù",
      "pos": "Italian phrase",
      "pron": "/il ˈdʒɔ.ko del kuˈku/",
      "literal": "「カッコウのゲーム」",
      "meaning": "(イタリア語)「いないいないばあ」",
      "context": "il = 男性定冠詞 the、gioco = game、del = of the、cucù = カッコウ(鳥または「ばあ!」の擬音)。",
      "collocations": []
    },
    "might_as_well": {
      "tier": "frequent",
      "surface": "might as well",
      "pos": "idiom",
      "pron": "/maɪt æz wel/",
      "literal": "~するのも同様に良い",
      "meaning": "~したのも同じだ / ~してもよい(消極的提案)",
      "context": "仮定法と組み合わせて「事実上~である」を表す。日常会話で「(他に選択肢ないし)~するか」の意でも極めて頻用。必修表現。",
      "collocations": ["might as well give up", "might as well try", "you might as well"]
    }
  }
}
```

---

## 設計上のポイント

### なぜtokens配列を使うのか
- HTMLレンダリング時に1トークンずつ要素生成できる
- type="skip"でスペースや句読点を非タップ要素として扱える
- type="foreign"で外国語(イタリア語等)も解説可能

### なぜwords/expressionsを辞書として分離するのか
- 同じ単語が複数回出現してもデータ重複を避けられる
- 例文・解説のメンテが容易

### tier情報をどこに置くか
- token側にも置く(tier)→ レンダリング時のCSSクラス決定で使う
- words/expressions側にも置く(tier)→ モーダル表示時のタグ決定で使う
- 重複だがアクセス性能を優先

---

## バージョニング

スキーマに破壊的変更が入った場合:
1. `requirements_v3.md` の改訂履歴に記載
2. 既存JSONとの互換性を保つか、移行スクリプトを書くか判断
3. PWA側のパース処理も合わせて更新

現在のスキーマバージョン:**v3.3** (2026-05-23)

## 改訂履歴(スキーマ)

- **v3.0** (2026-05-07) 初版
- **v3.1** (2026-05-10) D-016 採用に伴い、`source` を "ted-ed" 固定に。`video_id` 追加(YouTube videoId)。`video_url` / `embed_url` を YouTube ベースに変更。`slug` は識別子に降格(ted.com URL の一部ではなくなる)。
- **v3.2** (2026-05-10) D-017 / D-203 採用に伴い、`primary_topic` / `tags` / `difficulty` を TalkJson と TalkSummary に追加。PWA のビュー D(トピック)/ ビュー E(単語駆動)/ 検索フィルタの基盤。
- **v3.3** (2026-05-23) D-019 採用に伴い、取得経路を ted.com 公式 GraphQL API に統一。`slug` を ted.com talk slug に格上げ(D-010 復活、D-016 撤回)。`video_id` のセマンティクスを **ted.com 数値 video id** に変更(YouTube videoId は廃止)。`video_url` / `embed_url` を ted.com / embed.ted.com に戻す。`published_at`(ted.com publishedAt)を TalkJson / TalkSummary に追加。
