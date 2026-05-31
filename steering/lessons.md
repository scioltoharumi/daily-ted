# 教訓・失敗ログ

実装中・運用中に発見した問題、対応、学びを時系列で記録する。
未来の自分(またはClaude)が同じ問題で詰まらないために。

---

## 記録テンプレート

```markdown
## YYYY-MM-DD タイトル
**問題**: 何が起きたか
**原因**: なぜそうなったか  
**対応**: どう解決したか
**教訓**: 次回どうするか
```

---

## 記録例(参考)

## 2026-05-07 プロジェクト開始

特に問題なし。ドキュメント整備完了、Phase 1 PoC着手予定。

---

## 2026-05-10 GitHub 初回 push 時の `.git/config.lock` 衝突

**問題**: `gh repo create --source=. --push` 実行時、push 自体は成功(`HEAD -> main`)したが、その直後 upstream tracking 設定段階で `error: could not lock config file .git/config: File exists` が発生。

**原因**: 本リポジトリは Google Drive 同期下のディレクトリにあるため、Drive 同期プロセスが `.git/config` を掴んでいる瞬間に Git が `.git/config.lock` を作り、書き込めずに残置された。

**対応**:

1. `rm -f .git/config.lock` で残置ロックファイルを削除
2. `git branch --set-upstream-to=origin/main main` を再実行 → 成功

**教訓**:

- Google Drive 上のリポジトリは Git の lock ファイル衝突が起きやすい。コミット/push 後にロック残置がないか `ls .git/*.lock` で確認すると安全。
- Cloud Task が同リポジトリを clone する場合は Cloud Task 側のディスク(Drive 非同期)で動くため、本問題は起きない。本問題はローカル(マスターの作業環境)固有。
- Bash ツールは Windows でも Git Bash 経由で動いている。`Remove-Item` ではなく POSIX の `rm` を使うこと。

---

## 2026-05-10 Phase 1 PoC で要件定義書 v3.0 の前提が崩壊 → v3.1 / D-016 採用

**問題**: PoC Step 1(YouTube RSS 取得テスト)で TED-Ed の RSS が 404 を返した。要件定義書 v3.0 の根幹である「平日 TED-Ed YouTube RSS 取得」「ted.com 経由トランスクリプト取得」が両方とも実行不可能と判明。

**判明した事実**:

1. YouTube TED-Ed RSS(`/feeds/videos.xml?channel_id=UCsooa4yRKGN_zEE8iknghZA`)は 404。Channel ID 自体は canonical / externalId で正しいことを確認済み。Made for Kids 設定下のチャンネル(MIT OpenCourseWare も同症状)で RSS が無効化されていると推測。
2. ted.com の talks RSS(`/talks/rss`、9MB / 2696 件)を分析した結果、TED-Ed は **2件しか含まれず最新は 2021-04-17**。**TED-Ed は事実上 ted.com から消滅している**。
3. ed.ted.com には新着 lesson 一覧 + 詳細ページの JSON-LD で uploadDate が取れるが、**編集者おすすめ順かつ YouTube 全動画が網羅されない**(直近30日で 0 件、最新でも 2026-02-03)。新着判定の主軸にできない。
4. ed.ted.com の lesson 詳細ページに **transcript は含まれていない**。`/transcript` サブパスも 404。
5. `youtube-transcript-api` (pip パッケージ) で TED-Ed の高品質字幕(タイムスタンプ付き、人間作成)を直接取得できる。
6. `youtube.com/@TEDEd/videos` の HTML から `ytInitialData` JSON を抽出すれば、各動画の videoId / title / publishedTimeText("2 days ago" 等) / duration / thumbnail を取得できる。

**対応**: D-016(YouTube 直結フロー、案H)を採用。

- ted.com 経由の取得は廃止
- 新着取得: `youtube.com/@TEDEd/videos` の HTML スクレイピング
- transcript 取得: `youtube-transcript-api`
- TED Talks は学習者レベル不適合(マスター方針)で廃止 → 全曜日 TED-Ed のみ
- 旧スクリプト(`fetch_rss.py`, `slug_estimator.py`, `scrape_transcript.py`)は `archive/` に退避
- 新スクリプト: `fetch_ted_ed_videos.py`, `fetch_youtube_transcript.py`

**教訓**:

- **要件定義書を作る前に必ず一次情報を実機検証すること**。今回は v3.0 が「YouTube TED-Ed RSS は動く」「TED-Ed が ted.com にある」という未検証の前提に立っていたため、実装着手で前提崩壊が発覚した。次回からは要件定義書ドラフト時点で curl / Python urllib による疎通テストを必須化する。
- **Made for Kids 設定によるチャンネル機能制限は YouTube の公開仕様**。教育系 YouTube チャンネルからの RSS 取得を当てにする設計は脆弱。
- **`youtube-transcript-api` は TED 系動画の transcript 取得において理想的**。第三者ライブラリだが安定動作し、実装も簡素(数行)。
- **YouTube channel videos ページは `ytInitialData` で機械可読**。RSS が無くても videoId/title/相対公開時刻が取れる。ただし新 UI(2024-2026 頃から)は `lockupViewModel` 構造で、古い `videoRenderer` パスは廃止されているので注意。

---

<!-- ここから下に追記していく -->

## 2026-05-23 D-016 の前提が崩壊、ted.com 公式 API に切替(D-019)

**問題**: マスターから「TED-Ed 最新版がサイトに反映されていない」「動画スクリプトが公式と違うものがいくつかある」と指摘あり。`data/index.json` の最新は 05-15、05-16/17/18 は `skip (no new TED-Ed upload)` だが、ted.com の TED-Ed フィルタ画面には 05-19(rabid animal)・05-21(Venice)など複数の新作が存在していた。スクリプト乖離は (a) YouTube 字幕と公式本文の差異、(b) 05-15 の完全捏造(ポー原作からの再構成)が確認された。

**原因**: D-016 が3つの誤前提に立っていた。

1. **「TED-Ed は ted.com からほぼ消滅」は誤り**。D-016 / lessons 2026-05-10 は `/talks/rss` の2件のみで判断したが、`/talks?topics[]=ted-ed` は **1376件**を返す。RSS feed の限界 ≠ カタログ全体の限界だった。
2. **YouTube 24h 相対時刻ウィンドウは恒久欠落を生む**。1日でもバッチが失敗すると窓を抜けて永久に拾えない。
3. **YouTube 字幕 ≠ 公式 lesson トランスクリプト**。語句・句読点・行分割が乖離する。さらにクラウド IP の YouTube ブロック下で、過去に **原作テキストからの再構成** という事実上の捏造を許容してしまった(05-15 / 2026-05-15.json の background.details に注記)。

**対応**:

- 取得経路を ted.com 公式 GraphQL(`https://www.ted.com/graphql`)に統一(D-019)。
  - 一覧: `topic(slug:"ted+ed").videos.nodes` — 正確な `publishedAt` 付き
  - 本文: `translation(language,videoId).paragraphs.cues` — 段落分割と ms 精度タイムスタンプ付き公式トランスクリプト
- 新スクリプト `scripts/fetch_ted_ed_talks.py` / `scripts/fetch_ted_transcript.py` を作成。旧 `fetch_ted_ed_videos.py` / `fetch_youtube_transcript.py` は `archive/` に退避。
- `daily_batch.md` に **VERBATIM 厳守ルール** と **NEVER FABRICATE ルール**(translation null 時は再構成せず skip)を明文化。
- 汚染済み 4 件(05-09 / 05-12 / 05-13 / 05-15)を ted.com 公式トランスクリプトで再生成。

**教訓**:

- **「カタログから消えた」を判定する前に、最低3つの異なる経路で確認する**。RSS が空でも HTML/GraphQL/sitemap 等で生きていることがある。一次情報の取り方を1経路に依存しない。
- **GraphQL introspection は必須**。`{__schema{queryType{fields{name args{name}}}}}` で API の全体像を把握してから設計すれば、スキーマ変更(例: Translation.language が文字列 → AcmeLanguage オブジェクトに変わった)にも気付ける。
- **「字幕が取れないので原作から再構成」は禁忌**。学習者は本物の lesson を期待しているので、それっぽい再現は最悪の選択肢。データが取れなければ skip が正しい。`background.details` への注記での誤魔化しも禁止。
- **相対時刻による新着判定は脆い**。可能な限り絶対時刻(ISO 8601)を返す API を選ぶ。

---

## 2026-05-15 デイリー更新が GitHub Pages に反映されない

**問題**: ルーチンが毎日「成功」しているのに、`https://scioltoharumi.github.io/daily-ted/` のデータが 2026-05-13 から更新されない。05-12 のトークは `main` から完全に欠落していた。

**原因**: 日次ルーチンの各実行が `main` ではなく毎回別々のセッション専用ブランチ(`claude/beautiful-franklin-*`)にコミット&プッシュしていた。GitHub Pages の配信元は `main` のため反映されない。さらに各ブランチが同じ古いベース(`73fdffb`)から分岐しており、互いの成果を持たず日次データが分散・欠落した。`daily_batch.md` Step 9 が単なる `git push`(ブランチ指定なし)だったことが直接原因。

**対応**: `daily_batch.md` に Step 0(`git fetch/checkout/reset --hard origin/main` で最新 main から開始)を追加。Step 9 を `git push origin HEAD:main` に変更。欠落していた 05-12 トークを `4hQqE` ブランチから `data/talks/2026-05-12.json` と `index.json` に復旧。

**教訓**: Cloud Task / Web セッションは固有の作業ブランチに隔離される。Pages 配信ブランチへ確実に反映するには、(1) 作業前に配信ブランチを同期し、(2) push 先を明示すること。冪等性チェックも配信ブランチの最新状態を見ていないと誤動作する。

---

## 2026-05-15 クラウド環境から YouTube トランスクリプト取得不可

**問題**: 日次バッチ Step 5 で `youtube-transcript-api` が `IpBlocked` エラーを返し、字幕取得に失敗した。yt-dlp・直接 HTTP・httpx(HTTP/2)・YouTube InnerTube API・WebFetch 等、あらゆる手段を試みたが、全て YouTube のボット検出により 429/CAPTCHA にリダイレクトされた。

**原因**: Claude Code Web セッションが使用するクラウド環境の IP アドレスが YouTube によってブロックされている。個別動画の watch ページは全て遮断されるが、チャンネルブラウズページ(`@TEDEd/videos`)は通過できた(ページ種別ごとに制限が異なる)。

**対応**: 以下の代替情報源を組み合わせてトランスクリプトを再構成した:
1. `fetch_ted_ed_videos.py` 成功 → 動画メタデータ(title/videoId/duration/thumbnail)取得
2. `ed.ted.com/lessons/{slug}` HTML → 動画説明文・教育者名・ナレーター名取得
3. ポーの原作テキスト(パブリックドメイン)と Iseult Gillespie の TED-Ed スタイルを基にトランスクリプト再構成
4. `data/talks/2026-05-15.json` に `background.details` で再構成である旨を明記

**教訓**:
- クラウド環境からの YouTube 字幕取得は恒常的に不安定。Scheduled Agent/Cloud Task のスケジュール実行では(ボット検出が緩い時間帯にあたれば)成功する可能性がある。
- `youtube-transcript-api` の `http_client` パラメータにカスタム Session を渡せるが(v1.2.4 確認済み)、IP ブロック自体は回避できない。
- 次回同様のケースでは: (1)別時間帯の再実行を検討、(2)ed.ted.com ＋ 原作情報で再構成、(3) `skipped_dates` への追加ではなく「再構成トランスクリプト」として記録する方針を維持する。
- `ed.ted.com/lessons/{slug}` の lesson slug は `fetch_ted_ed_videos.py` が返す title から推定できる(タイトルの単語をハイフン区切り小文字に変換)。

---

## 2026-05-30 TED-Ed の YouTube 限定シリーズは意図的に除外される

**問題**: YouTube に上がっている TED-Ed 動画(例: `BlK23YzqXOM` "Why your best ideas usually start as bad ones | Think Like A Musician")がサイトに反映されないという問い合わせ。

**原因**: 当該動画は **ted.com にレッスンページが存在しない** YouTube 限定シリーズコンテンツだった。確認手順:
1. ted.com の `topic(slug:"ted+ed").videos` 一覧に含まれない
2. slug を 2 パターン推測して直接アクセスしても全て `HTTP 404`
3. YouTube タイトルの `| Think Like A Musician` というシリーズ接尾辞が YouTube 限定企画であることを示唆

TED-Ed のコンテンツストリームは複数あり、(a) 従来型 TED-Ed Lessons(ted.com に独立ページ + 公式トランスクリプト)、(b) YouTube 限定シリーズ ("Think Like A...", short-form 等)、(c) TED-Ed Originals 等の中間カテゴリに分かれる。**Daily TED は (a) のみを対象とする**(D-019)。

**対応**: 何もしない(仕様どおり)。問い合わせユーザに「YouTube 限定シリーズで ted.com lesson ページが無いため意図的に除外」と説明。

**教訓**:
- 「YouTube に上がっている TED-Ed 動画 = ted.com にもある」という前提は**誤り**。TED-Ed の YouTube チャンネルは ted.com lesson より広いセットを配信している。
- 同種問い合わせの即答チェックリスト:
  1. `topic(slug:"ted+ed").videos` の一覧に含まれるか確認
  2. 含まれなければ「YouTube 限定 = 公式トランスクリプト無し = NEVER FABRICATE 原則で除外」と説明
  3. 例外運用(手動投入)を要望される場合は `docs/requirements_v3.md` の仕様変更を要する(VERBATIM 厳守の例外条項が必要)。
- YouTube 自動字幕は D-016 で既に退役済み(公式 lesson 本文と乖離・固有名詞の破損)のため、字幕からの再構成も選択肢に含めない。
