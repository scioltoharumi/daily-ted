# archive/

役目を終えたスクリプト・ドキュメントの退避場所。

## 退避済みファイル

### 2026-05-10 案H採用に伴う退避

要件定義書 v3.1 改訂(D-016 採用、TED-Ed パスを YouTube 直結に変更)に伴い、以下のスクリプトを退避した。詳細は `steering/design_decisions.md` D-016 と `steering/lessons.md` を参照。

- `fetch_rss.py.deprecated` — YouTube RSS 取得スクリプト。TED-Ed の YouTube RSS フィードが Made for Kids 設定下で 404 を返すため使用不可。TED Talks では動作するが本プロジェクトは TED-Ed のみ配信する方針(D-016)になったため退役。
- `slug_estimator.py.deprecated` — YouTube タイトルから ted.com slug を推定するスクリプト。ted.com 統一(D-010)を撤回し YouTube 直結に変更したため不要。
- `scrape_transcript.py.deprecated` — ted.com の `q("talkPage.init", ...)` JSON からトランスクリプトを抽出するスクリプト。同上の理由で不要。なお、ted.com 側のページ構造も既に変わっており現状動作しない疑いあり(未検証)。

### 2026-05-23 D-019 採用に伴う退避

D-019(YouTube 直結 → ted.com 公式 API 切替)に伴い、案H で導入した
YouTube 直結スクリプトを退避した。詳細は `steering/design_decisions.md`
D-019 と `steering/lessons.md` 2026-05-23 を参照。

- `fetch_ted_ed_videos_youtube.py` — `youtube.com/@TEDEd/videos` の HTML から
  `ytInitialData` を抽出し videoId / 相対公開時刻を取得していた旧スクリプト。
  廃止理由: (a) "X days ago" 相対表記の粒度が粗く 24h 窓で恒久欠落を
  生む / (b) クラウド IP が YouTube に遮断されると検出すら破綻、ほか。
- `fetch_youtube_transcript.py` — `youtube-transcript-api` 経由で YouTube
  字幕を取得していた旧スクリプト。廃止理由: (a) 字幕本文が公式 lesson
  トランスクリプトと語句・句読点・行分割で乖離 / (b) クラウド IP の
  watch ページ遮断で恒常的に失敗。

## 復活させる場合

将来的に ted.com の GraphQL API が破壊的変更を受けて利用できなくなった
場合のバックアップ参考実装。

## 削除しない理由

- 設計判断の経緯を残すため
- 取得経路変更の歴史的記録として
