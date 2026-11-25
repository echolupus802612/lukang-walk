# 交給 Codex 濃縮全台地點簡介（在背景跑，輸出記錄在 art/desc/）
$x = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin\5449c1f0f26f1f98\codex.exe'
$P = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path   # 專案根目錄
Get-Content (Join-Path $P 'art\prompts\desc_tw.txt') -Raw -Encoding utf8 | & $x exec --skip-git-repo-check --ephemeral -s workspace-write -C $P -o (Join-Path $P 'art\desc\codex_last.txt') - *> (Join-Path $P 'art\desc\codex_run.txt')
