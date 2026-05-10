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
