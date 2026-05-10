# Phase 1 PoC手順書

実装着手前の技術検証フェーズ(3〜7日)。各ステップの結果を `steering/lessons.md` に記録すること。

---

## 検証目的

1. **YouTube RSS** が想定通りの構造で取得できるか
2. **slug推定** がどの程度の的中率か(直近20本のTED-Edで実測)
3. **ted.com スクレイピング** で確実にトランスクリプトが取れるか
4. **Cloud Task** で上記が実環境で動くか
5. **Claude Opus 4.7** の解説生成品質が要求水準を満たすか
6. **1Talkあたりの処理時間** が30分以内に収まるか

---

## 検証ステップ

### Step 1: YouTube RSS の実構造確認

#### 手順
```bash
curl -s "https://www.youtube.com/feeds/videos.xml?channel_id=UCsooa4yRKGN_zEE8iknghZA" | head -100
```

#### 確認項目
- [ ] XMLが返る(HTMLランディングではない)
- [ ] `<entry>` タグに直近15本が含まれる
- [ ] 各entryに以下があることを確認:
  - `<title>` - 動画タイトル
  - `<published>` - 公開日時(ISO 8601)
  - `<yt:videoId>` - 動画ID
  - `<media:thumbnail>` - サムネイルURL
  - `<media:description>` - 動画概要
- [ ] TED Talks (`UCAuUUnT6oDeKwE6v1NGQxug`)も同様の構造か確認

#### 想定される問題と対応
- RSSがランディングにリダイレクトされる → User-Agent指定で回避
- 構造が変わっている → XMLパースを柔軟にする(BeautifulSoupのlxml)

---

### Step 2: slug推定の的中率測定

#### 手順
TED-Edの直近20本のYouTube動画タイトルを取得し、それぞれの slug を機械的に推定。実際にted.com/talks/{slug}にアクセスしてヒット率を測定する。

#### 推定アルゴリズム(初期版)
```python
import re

def estimate_slug(youtube_title: str, source: str) -> str:
    # 小文字化
    s = youtube_title.lower()
    # 特殊文字除去(英数字とスペース・ハイフンのみ残す)
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    # スペース・ハイフンをアンダースコアに
    s = re.sub(r"[\s\-]+", "_", s)
    # 連続アンダースコアを1つに
    s = re.sub(r"_+", "_", s)
    # 前後のアンダースコア除去
    s = s.strip("_")
    
    if source == "ted-ed":
        s = "ted_ed_" + s
    return s
```

#### 確認項目
- [ ] 直近20本のTED-Ed動画で、推定slugで200を返す比率を測定
- [ ] 200を返す:成功とカウント
- [ ] 404を返す:タイトル変換ルールにバグがある or ted.com未掲載
- [ ] 失敗ケースを分析:タイトルとted.com実URLを比較
- [ ] **目標的中率: 70%以上**(これ以下ならフォールバック実装が必要)

#### フォールバック案
- バリエーション試行:`ted_ed_a_<title>` (冠詞ありパターン), `ted_ed_<title-without-articles>` 等
- ted.comのサイト内検索APIまたは検索ページのスクレイピング
- Claudeに「このタイトルから ted.com の URL を予想して」と判定させる

---

### Step 3: ted.com スクレイピング動作確認

#### 手順
```bash
curl -s "https://www.ted.com/talks/ted_ed_the_fascinating_reason_you_loved_peek_a_boo" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | grep -o 'q("talkPage.init", {.*})' | head -1
```

#### 確認項目
- [ ] HTMLが返る(403/Cloudflare保護されていない)
- [ ] `q("talkPage.init", {...})` のJSON部分が抽出できる
- [ ] JSONをパースしてtranscript_paragraphs等のキーを発見できる
- [ ] paragraphにstart時刻と本文が含まれる
- [ ] 文単位の分割が必要か、TED側で既に分割済みか確認

#### 抽出スクリプト例(Python)
```python
import re
import json
import requests

def extract_transcript(slug: str) -> dict:
    url = f"https://www.ted.com/talks/{slug}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    
    # HTMLから q("talkPage.init", {...}) を抽出
    m = re.search(r'q\("talkPage\.init",\s*({.*?})\);', res.text, re.DOTALL)
    if not m:
        raise ValueError("talkPage.init not found")
    
    data = json.loads(m.group(1))
    return data
```

#### 注意点
- ted.com の HTML 構造は時々変わる。発見できなかった場合は変更があった可能性大
- レート制限に注意(1日数十回程度ならまず大丈夫)

---

### Step 4: Cloud Task 試走(手動実行)

#### 手順
1. claude.ai/code/scheduled で新規Cloud Task作成
2. リポジトリ連携(privateリポジトリ書き込み権限)
3. プロンプトに `prompts/daily_batch.md` の内容を貼る
4. cron は最初は無効化、**手動実行**で1回試す
5. 出力JSONを確認、PWAから読めるかチェック

#### 確認項目
- [ ] Cloud Taskから外部URL(YouTube・ted.com)を fetch できる
- [ ] BashコマンドでcurlやPythonスクリプト実行ができる
- [ ] Privateリポジトリに git push できる
- [ ] 実行時間が30分以内に収まる
- [ ] 失敗時のログがCloud Task UIで確認できる

#### 想定される問題
- ネットワーク制限でted.comに到達できない → Cloud Taskの仕様確認、別ホスト経由を検討
- Git push権限不足 → リポジトリ連携設定を見直す
- 30分超過 → 段落並列処理または重要度の低い解説を簡略化

---

### Step 5: 解説生成品質の評価

#### 手順
試走で生成された1日分のJSON(/data/talks/YYYY-MM-DD.json)を実際に確認:

#### 評価観点
- [ ] 全単語にtier分類が付与されている
- [ ] tier分類が妥当(基本語をfrequentに上げていないか)
- [ ] 例文の英語が自然
- [ ] 日本語訳が自然(直訳調になっていないか)
- [ ] 構文解析の S/V/O/C ラベルが正確
- [ ] 背景情報の事実が正確(歴史的事実・人名等)
- [ ] コロケーションが実際に使われている表現
- [ ] 表現の検出漏れがないか(明らかなイディオムが word扱いになっていないか)

#### 改善サイクル
1. 問題箇所をリストアップ
2. プロンプト(prompts/daily_batch.md, prompts/word_classification.md)を更新
3. 再試走
4. これを2-3回繰り返してチューニング

---

### Step 6: PWAスケルトンとJSON連携

#### 手順
1. Svelte + Vite でプロジェクト初期化
2. data/index.json と talks/YYYY-MM-DD.json を fetch して表示
3. モックアップ(docs/mockup_v5.html)のHTML/CSSをSvelteコンポーネントに分解
4. 4階層の単語スタイル、モーダル、お気に入りまで実装

#### 確認項目
- [ ] JSONが正しくパースされ、トランスクリプトが表示される
- [ ] tier別のCSSクラスが適用される
- [ ] タップでモーダルが下からスライドアップ
- [ ] お気に入りがlocalStorageに保存される
- [ ] PWA化:manifest.json, Service Worker, ホーム画面追加

---

## PoC完了の判定基準

以下が全て満たされたらPhase 2(MVP実装)に進む:

- [ ] YouTube RSS取得が安定動作
- [ ] slug推定的中率70%以上(またはフォールバック動作確認)
- [ ] ted.com スクレイピング動作確認
- [ ] Cloud Taskが実環境で1日分完走(30分以内)
- [ ] 生成された解説JSONの品質が許容レベル
- [ ] PWAスケルトンでJSON表示・タップ動作確認

---

## 学んだことの記録

各ステップで判明した事実・問題・対応を `steering/lessons.md` に追記すること。次回同じ問題に遭遇したときの参考になる。

例:
```
## 2026-05-08 PoC Step 1の学び
- YouTube RSSは User-Agent なしでもXMLを返す
- ただし `<media:description>` は最大500字で切れる
- 全文取得には別途 YouTube Data API が必要(今回は不要)
```
