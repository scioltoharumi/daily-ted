# 設計判断ログ

このプロジェクトで下した主要な設計判断と、その背景・トレードオフを記録する。
新たな依頼・実装時は、まずここを確認して既存方針との整合を取ること。

---

## D-001: バックエンドにClaude Code Cloud Taskを採用

**日付**: 2026-05-07
**判断**: GitHub Actions + Anthropic API ではなく Cloud Task に統一

**理由**:
- MAXプラン契約のため、Cloud Task内のClaude推論は実質無料
- API key管理・GH PAT管理が不要
- Cloud Task がリポジトリのfresh cloneを取得・git push まで完結
- 認証情報の漏洩リスクをほぼゼロにできる

**トレードオフ**:
- Cloud Taskの仕様変更に依存する(機能廃止リスク)
- スケジュール許容誤差が最大30分(日次なら許容)
- 単一実行30分上限(処理量に上限)

---

## D-002: 著作権論点を度外視

**日付**: 2026-05-07
**判断**: 私的利用前提で著作権関連の対応を全て省略

**理由**:
- 学習者1名のみの私的利用
- リポジトリはprivateで運用
- 法的リスクが実質的に発生しない範囲

**保留事項**:
- 公開化や他者への共有を始める場合は要再検討

---

## D-003: ソース2系統(平日TED-Ed / 休日TED Talks)

**日付**: 2026-05-07
**判断**: 平日と休日でソースを切り替える

**理由**:
- 平日(隙間時間):TED-Edの5〜7分が学習負荷的に最適
- 休日(まとまった時間):TED Talksの10〜18分でじっくり
- TED-Edは構文が整っていて学習向き、TEDは生きた表現が学べる
- 両方の長所を時間帯で使い分け

**実装影響**:
- バッチが曜日判定で分岐
- カードに🎓/🎤バッジで識別

---

## D-004: 「新作なければスキップ」の徹底

**日付**: 2026-05-07
**判断**: 配信なし日は穴あきを容認、補完しない

**理由**:
- 過去ライブラリから補完すると単調になる
- ロジックがシンプルになり、バッチが冪等
- 「今日は読まない日」があっても継続性に支障なし

**実装影響**:
- バッチ:候補なし→即終了、何もコミットしない
- PWA:カード一覧で「— no new release —」プレースホルダー表示

---

## D-005: 全単語事前生成、AI即時生成フォールバックなし

**日付**: 2026-05-07
**判断**: トランスクリプトの全単語・全表現・全文を事前にClaudeで解析、PWA側は静的JSONを表示するだけ

**理由**:
- タップ時のレスポンスが即時(200ms未満)
- PWA側のロジックがシンプル(API呼び出しなし)
- MAXプランでコスト懸念なし

**トレードオフ**:
- 1Talk JSONサイズが500KB前後に膨らむ(許容)
- Cloud Task処理時間が10〜25分(30分上限内)

---

## D-006: 単語の4階層強調(basic/normal/key/frequent)

**日付**: 2026-05-07
**判断**: 単語を4階層に分け、視覚的強調度を変える

**階層定義**:
- `basic`: 固有名詞・冠詞等(目立たない)
- `normal`: 一般的な学習対象語(薄い琥珀ドット)
- `key`: 学習価値高い語(濃い琥珀ドット)
- `frequent`: 必修頻出語(★黄色マーカー＋太字)

**理由**:
- スクロール時に「特に覚えるべき語」が一瞥でわかる
- 普通の語は読書を邪魔しない控えめさ
- 固有名詞などは視覚ノイズにならない

**判定責務**:
- Cloud Task内のClaude(プロンプトで基準提示)
- ハードコードリストは作らない

---

## D-007: 表現の2階層強調(normal/frequent)

**日付**: 2026-05-07
**判断**: イディオム・表現も2階層

- `normal expression`: 専門用語・複合名詞(青背景)
- `frequent expression`: 必修慣用句(濃い青背景＋太字)

**例**:
- normal: developmental milestone, cognitive leap
- frequent: out of sight out of mind, might as well, take shape

---

## D-008: 文範囲の可視化(紫の縦線)

**日付**: 2026-05-07
**判断**: 文末の⌘アイコンに加え、ホバー時に文の左側に紫の縦線で範囲を示す

**理由**:
- 文末アイコンだけだと「どこからどこまでが対象か」が不明瞭
- 縦線で対象範囲が一目瞭然
- 紫色は単語(琥珀)・表現(青)と被らない

---

## D-009: 動画はTED公式embedで埋め込み

**日付**: 2026-05-07
**判断**: 記事冒頭にTED公式のembed iframeを配置

```html
<iframe src="https://embed.ted.com/talks/{slug}"></iframe>
```

**理由**:
- ライセンス的にもクリーン(公式embed)
- TED-EdもTED Talksも同じURL構造でembed可能
- 動画コントロール、字幕等は公式プレイヤーに任せられる

---

## D-010: トランスクリプトはted.comスクレイピング(ted-edではなくted.comから)

**日付**: 2026-05-07
**判断**: TED-Edの場合も `ted.com/talks/ted_ed_*` 経由でトランスクリプトを取得

**理由**:
- ed.ted.comのlessonページにはトランスクリプトがない(TED公式FAQで明記)
- ted.com に掲載されているTED-Edはトランスクリプト付き
- ted.com経由なら統一スクレイピングロジックでTED-Ed/TED Talks両対応
- HTML内の `q("talkPage.init", {...})` JSONから抽出可能

**slug推定ルール**:
- TED-Ed: `ted_ed_<youtube-title-snake-case>`
- 例: "The fascinating reason you loved peek-a-boo" → `ted_ed_the_fascinating_reason_you_loved_peek_a_boo`

**フォールバック**:
- 推定slugが404 → その日はスキップ(全TED-EdがTED.comに掲載されるとは限らない)

---

## D-011: お気に入りはTalk別グルーピング

**日付**: 2026-05-07
**判断**: お気に入り一覧をTalk別にグループ化、種別(words/expr/sent)で絞り込み可能

**理由**:
- 単独単語より文脈ごと覚えた方が定着する(SLA研究の知見)
- 「あのTalkで出てきた表現」として思い出しやすい
- 種別タブで集中復習も可能

**エクスポート形式**:
- Markdown(汎用)
- CSV(他ツール連携)
- Anki(.apkg、将来のSRS対応への布石)

---

## D-012: ホスティングはGitHub Pages

**日付**: 2026-05-07
**判断**: Cloudflare Pages等の選択肢の中からGitHub Pagesを採用

**理由**:
- private repo + privateホスティングをCloudflare Accessで構築する複雑性を避ける
- 著作権論点を度外視するため、認証保護は不要
- GitHub Pagesは無料、自動デプロイ、十分高速

**注意**:
- GitHub Pagesでprivate repo配信するにはPro以上のGitHubプラン必要
- 課金状況によってはCloudflare Pagesに切り替え

---

## D-013: フロントFWはSvelte

**日付**: 2026-05-07
**判断**: React/Vue/Svelteの中からSvelteを選択

**理由**:
- バンドルサイズが小さい(PWAに最適)
- Svelte + Tailwind の組み合わせが書きやすい
- 一人開発でランタイム複雑度が低い方が良い

**代替案だったもの**:
- React + Next.js: 過剰、SSR不要
- Vue 3: 良い選択肢だが個人的好み
- Vanilla JS: 状態管理が辛くなる

---

## D-014: 復習機能(SRS)はMVPに含めない

**日付**: 2026-05-07
**判断**: Phase 4以降に先送り

**理由**:
- まず「読む・タップする」体験を完成させる
- SRSは設計が深く、実装も大きい
- お気に入りエクスポート(Anki形式)で当面は代替

---

## D-015: 興味分野フィルターはClaudeが文脈判定

**日付**: 2026-05-07
**判断**: YouTube RSSにタグ情報がないため、Claudeにタイトル・説明文を読ませて分野判定

**理由**:
- YouTube RSSのcategory情報は不正確・不揃い
- ハードコードのキーワードリストは網羅性に欠ける
- Cloudで動くClaudeなら自然言語判定が容易

**初期分野**:
1. Science (physics, math, biology, chemistry, neuroscience, space)
2. Technology (AI, computer science, engineering)
3. Philosophy & Psychology
4. Linguistics & Communication
5. Economics & Finance
6. Creativity & Storytelling

**運用**:
- 実運用しながらヒット率に応じて分野を追加・削除

**v3.1 で撤回**: D-016 採用に伴い TED Talks 配信は廃止、興味分野フィルターも不要となった。

---

## D-016: TED-Ed のみ配信、取得は YouTube 直結に変更(案H)

**日付**: 2026-05-10
**判断**: TED-Ed のみを配信ソースとし、新着取得は `youtube.com/@TEDEd/videos` の HTML スクレイピング(`ytInitialData` 抽出)、トランスクリプト取得は `youtube-transcript-api` 経由に変更する。ted.com / ed.ted.com 経由のフローは廃止。

**経緯(2026-05-10 PoC で判明した事実)**:

1. YouTube TED-Ed チャンネルの RSS フィード(`/feeds/videos.xml?channel_id=UCsooa4yRKGN_zEE8iknghZA`)は 404 を返す。Made for Kids 設定下で RSS が無効化されている可能性が高い(MIT OpenCourseWare 等、教育系で同症状)。
2. ted.com の talks RSS(`/talks/rss`、2696件)を分析した結果、TED-Ed は 2件しか含まれず、最新公開日も 2021-04-17。**ted.com には TED-Ed がほぼ存在しない**ことが判明。
3. ed.ted.com には新着 lesson 一覧 + 詳細ページの JSON-LD で uploadDate が取れるが、編集者おすすめ順かつ YouTube 全動画が網羅されない(直近30日で 0 件)ため新着判定の主軸にできない。
4. ed.ted.com lesson ページにはトランスクリプトは含まれていない(/transcript サブパスも 404)。
5. **`youtube-transcript-api` で TED-Ed 動画の高品質字幕(タイムスタンプ付き)を取得できることを確認**。
6. **`youtube.com/@TEDEd/videos` の HTML から `ytInitialData` を抽出し、各動画の videoId / title / `publishedTimeText`("2 days ago" 等)/ duration / thumbnail を取得できることを確認**。

**新フロー**:

```text
1. youtube.com/@TEDEd/videos の HTML を取得 → ytInitialData JSON 抽出
2. 各動画の publishedTimeText を timedelta に変換し、24時間以内のみ抽出
3. 候補があれば、その videoId を youtube-transcript-api に渡して transcript snippets 取得
4. (任意)ed.ted.com の lesson 詳細ページ JSON-LD から uploadDate / description / publisher を補強
5. snippets を Claude Opus 4.7 で段落・文・token 構造に再構成 + 全要素解説生成
6. /data/talks/YYYY-MM-DD.json + index.json 更新
7. git commit & push
```

**TED Talks 廃止の理由(マスター方針)**:

- 学習者(マスター)の英語レベル(初学者寄り)に対し、TED Talks の 10〜18分尺・専門用語密度が過剰
- TED-Ed の 5〜7分・構文整理されたアニメ lesson の方が学習負荷的に最適

**配信頻度の見立て**:

- 直近7日で TED-Ed YouTube 投稿は 2本(2026-05-08、2026-05-06)
- → 平日のみ配信ロジック(D-003)は不要、毎日チェックで「新作あればスキップなし」運用
- D-004(新作なければスキップ)の方針はそのまま継続

**撤回・修正される過去判断**:

- D-003(平日 TED-Ed / 休日 TED Talks)→ 全曜日 TED-Ed のみ
- D-010(TED-Ed transcript も ted.com 経由)→ youtube-transcript-api 経由に変更
- D-015(興味分野フィルター)→ 不要(TED-Ed はそもそも教育目的のみ)

**新依存**:

- `youtube-transcript-api`(pip パッケージ)。Cloud Task / Scheduled Agent 内で `pip install youtube-transcript-api` を実行する。

**新リスク**:

- YouTube の channel videos ページ UI が変わると `lockupViewModel` 抽出ロジックが壊れる(R-01改)
- youtube-transcript-api の実装変更や YouTube 側の字幕配信仕様変更(R-03改)
- いずれも対応:エラー時は通知、リトライ実装、構造変更時は手動修正

---

## D-017: Phase 概念撤廃、初回 PWA で全機能網羅

**日付**: 2026-05-10
**判断**: 要件定義書 v3.1 の「9. 開発フェーズ」(Phase 1〜4 段階開発)を撤廃し、初回 PWA リリースで全 5 ビュー(タイムライン/月次/カレンダー/トピック/単語駆動)+ 補助機能(検索/既読/お気に入り集約/ストリーク/エクスポート)を全部入れる。

**理由**:

- 段階リリースで整合維持コストが累積する
- 機能間連携(検索が全ビューで効く、お気に入りがビュー横断で表示される等)を最初から織り込む方が設計が一貫
- 1 名運用のためリリース回数を抑える効率の方が高い

**範囲外(次期議論)**:

- SRS(間隔反復学習)・学習履歴ダッシュボード・既習フラグ・忘却度推定
  → 数ヶ月分のデータ蓄積後に設計する方が合理的

**関連スキーマ拡張(v3.2)**:

- TalkJson / TalkSummary に `primary_topic` / `tags` / `difficulty` を追加(D ビュー・E ビューのために必須)
- 詳細は `docs/data_schema.md` v3.2 を参照

**詳細ノート**: `00_admin/steering/20260510-pwa-ui-direction/`(親プロジェクト側)に requirements / design / tasklist / decisions を保存済み。Phase 2 着手時はそこから走り出す。

**期間目安**: 6〜10 週間

---

## D-019: 取得経路を ted.com 公式 GraphQL API に切替(D-016 を撤回)

**日付**: 2026-05-23
**判断**: 新着検出も公式トランスクリプト取得も `https://www.ted.com/graphql` に統一する。YouTube 直結フロー(D-016 / 案H)は退役。

**経緯**: 運用2週間(2026-05-09〜05-18)で D-016 経由の収集に重大な3欠陥が顕在化した。

1. **クラウド IP の YouTube 遮断**(lessons.md 2026-05-15)。`youtube-transcript-api` を含むあらゆる YouTube watch ページアクセスが 429/CAPTCHA リダイレクトに遭い、字幕取得が恒常的に失敗する日が発生。
2. **24h 相対時刻ウィンドウの恒久欠落**。`fetch_ted_ed_videos.py` は YouTube の "X days ago" 粒度の `publishedTimeText` を 24h で足切りしていたため、バッチが1日でも失敗すると該当動画は二度と窓に入らず永久欠落する。実際 05-16 / 05-17 / 05-18 が `skip (no new TED-Ed upload)` と記録されているが、ted.com 側では 05-19(rabid animal)・05-21(Venice)など複数の新作があった。
3. **YouTube 字幕と公式 lesson 本文の乖離**。`youtube-transcript-api` が返すのは YouTube のキャプション(自動生成/手動配信どちらもあり得る)で、ted.com / ed.ted.com の lesson 公式トランスクリプトと語句・句読点・行分割が一致しない事例が散見された。さらに 05-15(masquerade)では IP ブロック下で **ポー原作テキストから字幕を再構成**して保存しており、公式と全く違う文章を「正しい字幕」として配信していた(2026-05-15.json の background.details に注記あり)。

**再検証で判明した事実**(D-016 当時の前提が誤りだった部分):

- D-016 は「TED-Ed は ted.com にほぼ存在しない(2件のみ、2021年で停止)」と結論したが、その根拠は `/talks/rss`(curated feed)のみ。実機確認したところ `https://www.ted.com/talks?topics[0]=ted-ed` は **1376件** の TED-Ed talk を返し、最新作も網羅されている。RSS の限界をカタログ全体の限界と取り違えていた。
- ted.com には公式 GraphQL エンドポイント `https://www.ted.com/graphql` があり、`topic(slug:"ted+ed").videos(first:N).nodes` で TED-Ed の最新一覧(正確な `publishedAt` 付き)、`translation(language,videoId).paragraphs.cues` で **公式 lesson トランスクリプト**(段落分割済み、ms 精度のタイムスタンプ付き)を返す。
- このエンドポイントはクラウド IP からブロックされていない(2026-05-23 時点で 200 応答を確認)。

**新フロー**:

```text
1. ted.com graphql に topic(slug:"ted+ed").videos クエリ → 最新 N 件取得
2. publishedAt ≥ 前回処理時刻 をフィルタ。複数あれば最古の未処理1本のみ採用
3. translation(language:"en", videoId:<id>) → 公式トランスクリプト取得
4. paragraphs[] 構造をそのまま採用し、cues.text は verbatim 保持
5. Claude が文分割 / token tier / structure / 単語・表現解説を生成
6. /data/talks/YYYY-MM-DD.json + index.json 更新 → git commit & push
```

**重要規約**:

- **NEVER FABRICATE**: GraphQL `translation` が null / エラーを返した場合、トランスクリプトを再構成・推定・原作テキストからの再現で代替してはならない。その日は skip。
- **VERBATIM**: cue.text の英文本文は一字一句改変しない(大文字・句読点・改行を含む)。
- **段落構造尊重**: ted.com の `paragraphs[]` をそのまま採用(Claude による再段落化禁止)。

**撤回・修正される過去判断**:

- D-016(YouTube 直結フロー)→ 全廃止。`fetch_ted_ed_videos.py` と `fetch_youtube_transcript.py` を `archive/` に退避。
- D-010(TED-Ed transcript も ted.com 経由)→ 実質復活。slug はタイトル推定ではなく ted.com `canonicalUrl` から確定取得するため slug 推定不要。

**新依存**: なし(Python 標準ライブラリ `urllib` のみ)。

**新リスク**:

- ted.com GraphQL スキーマの破壊的変更(`Translation.language` が文字列 → AcmeLanguage オブジェクトに変わった事例あり)。対応: スキーマ introspection で確認し、エラー時は手動修正。
- ted.com 側の TED-Ed topic slug 変更。現在 `ted+ed`(id 345)。対応: `fetch_ted_ed_talks.py` の `TED_ED_TOPIC_SLUG` を更新。

**汚染データの後始末**: D-016 期に取得した 4 件(2026-05-09 / 05-12 / 05-13 / 05-15)は、(a) 05-15 が完全捏造、(b) 05-09 が概算タイムスタンプ、(c) 05-12 が ted.com TED-Ed に存在しない 2018年再アップロードの誤検出、(d) 05-13 が YouTube 字幕乖離、の理由で全て再生成済み。

---

## D-018: PWA は hash-based routing + Svelte + Vite

**日付**: 2026-05-10
**判断**: PWA は Svelte + Vite(SvelteKit ではなく)+ 自前 hash router で実装。

**理由**:

- GitHub Pages は SPA の history API を扱えずリロード時に 404 になるため、hash routing(`#/calendar` 等)が安全
- Cloudflare Pages 等に切り替えても hash routing は移植性が高い
- 自前 router は数十行で書けるため SvelteKit のオーバーヘッドを避けられる
- PWA がシンプル(SSR 不要、データは静的 JSON)

**ホスティング判断**: PWA 完成時に GitHub Pro($4/月)/ Cloudflare Pages(無料)/ Vercel / ローカル のいずれかを選ぶ(D-103 の保留事項を引き継ぐ)。
