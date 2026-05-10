# 単語階層判定基準

Cloud Task内のClaudeが、各単語をどの階層(tier)に分類するかの基準を示す。

---

## 4階層の定義

### 1. `basic` - 装飾なし、目立たない
**何を入れるか**:
- 固有名詞:国名(Italy, Japan)、地名、人名(Jean Piaget)、組織名、商標
- 数字・序数(one, first, twice)
- 冠詞(the, a, an)とその変形
- 代名詞(it, this, that, he, she, you等)
- 短縮形(it's, don't, you're)
- 助動詞の基本形(do, does, did, can, will等)
- 前置詞の超基本(of, to, in, on)
- A1レベルでも頻出すぎて学習対象になりにくい語(thing, get, go, come, make, take)
  - ただしこれら基本動詞でも、**特殊な意味で使われている文脈**ではnormalまたはkeyに上げる

**視覚**:薄いグレーのドット下線。装飾を最小化。

### 2. `normal` - 一般的な学習対象
**何を入れるか**:
- A2-B1レベルの一般的な語彙
- 標準的な動詞・形容詞・名詞
- 学習者が見て「あ、これはちゃんと意味を確認したい」と思うレベル
- 例:source, laughter, blanket, exist, hidden, disappear, answer, months

**視覚**:薄い琥珀ドット下線。

### 3. `key` - 学習価値が特に高い
**何を入れるか**:
- B2以上の語彙
- 専門用語・学術用語(psychologist, cognition, object permanence)
- ニュアンスや文化背景の理解が必要な語(consequential, persists)
- 微妙な意味差を持つ語(famously, ceased)
- C1以上の難語
- 専門分野で重要な複合名詞

**視覚**:濃い琥珀ドット下線。

### 4. `frequent` - 必修頻出 ★最も強調
**何を入れるか**:
- TOEFL/IELTS頻出語
- 英検準1級〜1級レベルで応用度が高い語
- AWL(Academic Word List)に含まれる語
- 日常会話・ビジネス文書・記事すべてで頻用される必修動詞・形容詞
- 例:involve, fascinating, seem, operate, principle, shift, marks, cognitive, suddenly, connection, explain

**視覚**:黄色マーカー＋太字。**スクロール時に最も目に飛び込んでくる**。

---

## 判定の優先順位ルール

複数の階層に該当する場合の優先順位:

1. 文脈上のニュアンス/特殊用法 > 基本意味
2. 学習者の応用可能性 > 単純な頻度
3. 「絶対に覚えるべき」感 > 「知っていると便利」感

例:`makes` が "marks the beginning" のように特殊な意味で使われている場合、basicではなくfrequentに上げる。

---

## 表現(expressions)の2階層

### `normal expression` - 専門・複合的
- 専門用語の複合名詞:`developmental milestone`, `cognitive leap`, `quantum entanglement`
- 分野特定的な表現
- 字面通りの意味だが2語以上で1つの概念を表す

**視覚**:青背景＋下線

### `frequent expression` - 必修慣用句 ★最も強調
- 日常英語の必修イディオム:`out of sight, out of mind`, `might as well`, `take shape`
- 字面と意味が大きく乖離する慣用句
- 学習者が知っていれば英語の表現力が一気に上がる表現
- 句動詞の中でも特に頻用されるもの

**視覚**:濃い青背景＋枠線＋太字

---

## 表現の検出基準

以下のパターンで「表現として扱うか」判定:

1. **2語以上の固定的な組み合わせ**で、構成要素の和ではない意味を持つ
2. **コロケーション辞書・イディオム辞書に載る**レベルのもの
3. **句動詞**で、特殊な意味を持つもの(take off, get over等)
4. **諺・格言**(out of sight out of mind, when in Rome等)

単なる単語の並び(例:"a beautiful day")は表現ではなく、各単語をword扱い。

---

## 判定例(本文「The fascinating reason you loved peek-a-boo」より)

| 単語/表現 | tier | 判定理由 |
|---|---|---|
| Italy | basic | 固有名詞 |
| it's | basic | 短縮形 |
| Jean Piaget | basic | 固有名詞(人名) |
| Peek-a-boo | basic | 固有的な遊び名 |
| called | normal | 一般動詞 |
| source | normal | 一般名詞、複数の意味あり |
| infants | key | 医学・心理学用語、babyとの差を学ぶ価値あり |
| goofy | key | B2、ニュアンスが豊富 |
| consequential | key | C1、importantとの差を学ぶ価値 |
| psychologist | key | 専門用語、psychiatristとの混同防止 |
| ceased | key | やや文語的、stopとの差 |
| famously | key | 副詞の修辞用法、文中挿入の作法 |
| persists | key | continueとの差、意志的ニュアンス |
| **fascinating** | **frequent** | TOEFL頻出、interestingからのアップグレード語 |
| **involves** | **frequent** | TOEFL頻出、論文・ビジネス必修 |
| **seem** | **frequent** | 会話・記述で必須の修辞動詞 |
| **operate** | **frequent** | 多義語で応用範囲広い |
| **principle** | **frequent** | アカデミック頻出 |
| **shift** | **frequent** | paradigm shift等、ビジネス頻出 |
| **cognitive** | **frequent** | 心理・教育・脳科学で頻出 |
| **suddenly** | **frequent** | 修辞副詞、必須 |
| **explains** | **frequent** | 必須動詞 |
| **marks** | **frequent** | 抽象用法で頻出 |
| **connection** | **frequent** | 多義語、必須 |

---

## 判定原則

- **迷ったら一段下げる**(frequentにすべきか迷ったらkey、keyか迷ったらnormal)
- **黄色マーカーが多すぎると視覚的にうるさい**ので、frequentは慎重に選ぶ
- 1段落あたりfrequentは2-4個程度が適切な密度
- 判定基準は実運用で見直す前提。記事ごとに完璧を求めない
