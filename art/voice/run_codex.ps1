# 交給 Codex 重新配音（在背景跑，輸出記錄在 art/voice/）
$x = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin\5449c1f0f26f1f98\codex.exe'
$P = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path   # 專案根目錄
Get-Content (Join-Path $P 'art\prompts\voice_v2.txt') -Raw -Encoding utf8 | & $x exec --skip-git-repo-check --ephemeral -s workspace-write -c 'sandbox_workspace_write.network_access=true' -C $P -o (Join-Path $P 'art\voice\codex_last.txt') - *> (Join-Path $P 'art\voice\codex_run.txt')
