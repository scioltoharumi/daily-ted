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

<!-- ここから下に追記していく -->
