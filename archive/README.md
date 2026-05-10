# archive/

役目を終えたスクリプト・ドキュメントの退避場所。

## 退避済みファイル

### 2026-05-10 案H採用に伴う退避

要件定義書 v3.1 改訂(D-016 採用、TED-Ed パスを YouTube 直結に変更)に伴い、以下のスクリプトを退避した。詳細は `steering/design_decisions.md` D-016 と `steering/lessons.md` を参照。

- `fetch_rss.py.deprecated` — YouTube RSS 取得スクリプト。TED-Ed の YouTube RSS フィードが Made for Kids 設定下で 404 を返すため使用不可。TED Talks では動作するが本プロジェクトは TED-Ed のみ配信する方針(D-016)になったため退役。
- `slug_estimator.py.deprecated` — YouTube タイトルから ted.com slug を推定するスクリプト。ted.com 統一(D-010)を撤回し YouTube 直結に変更したため不要。
- `scrape_transcript.py.deprecated` — ted.com の `q("talkPage.init", ...)` JSON からトランスクリプトを抽出するスクリプト。同上の理由で不要。なお、ted.com 側のページ構造も既に変わっており現状動作しない疑いあり(未検証)。

## 復活させる場合

将来的に YouTube TED-Ed の RSS が復活する、もしくは ted.com に TED-Ed が再掲載されるようになった場合は、ここから戻して再評価する。

## 削除しない理由

- 設計判断の経緯を残すため
- 将来的に YouTube channel HTML スクレイピング(`fetch_ted_ed_videos.py`)が UI 変更で動かなくなった場合のバックアップ参考実装として
