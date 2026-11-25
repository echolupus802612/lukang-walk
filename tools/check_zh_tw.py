"""檢查常見簡體字與已確認的用詞；地名、人名與新用詞仍須依來源審閱。"""
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TEXT = {".md", ".html", ".csv", ".tsv", ".json", ".txt", ".swift", ".plist", ".py",
        ".yml", ".yaml", ".strings", ".xcstrings", ".xcscheme", ".pbxproj", ".css", ".js"}
# 對照表的左側以 Unicode 碼位表示，避免檢查程式的原始檔本身出現待替換文字。
REPLACEMENTS = {
    "\u8fd9": "這",
    "\u4eec": "們",
    "\u8bf4": "說",
    "\u8bf7": "請",
    "\u5bfc": "導",
    "\u4f53": "體",
    "\u663e": "顯",
    "\u56fe": "圖",
    "\u89c8": "覽",
    "\u9875": "頁",
    "\u5f00": "開",
    "\u5173": "關",
    "\u8bbe": "設",
    "\u9009": "選",
    "\u6570": "數",
    "\u8d44": "資",
    "\u8bef": "誤",
    "\u8fbe": "達",
    "\u5904": "處",
    "\u952e": "鍵",
    "\u94ae": "鈕",
    "\u673a": "機",
    "\u70b9": "點",
    "\u53d1": "發／髮",
    "\u8bed": "語",
    "\u7b80": "簡",
    "\u95e8": "門",
    "\u7ebf": "線",
    "\u95f4": "間",
    "\u6807": "標",
    "\u8bb0": "記",
    "\u6743": "權",
    "\u7801": "碼",
    "\u9a91": "騎",
    "\u7f51": "網",
    "\u8f6f": "軟",
    "\u58f0": "聲",
    "\u6587\u6a94": "文件",
    "\u97f3\u983b\u6a94": "音檔",
    "\u8996\u983b": "影片",
    "\u6578\u64da\u5eab": "資料庫",
    "\u670d\u52d9\u5668": "伺服器",
    "\u8edf\u4ef6": "軟體",
    "\u786c\u4ef6": "硬體",
    "\u6587\u4ef6\u593e": "資料夾",
    "\u9ed8\u8a8d\u503c": "預設值",
    "\u9f20\u6a19": "滑鼠",
    "\u97f3\u6a94\u6642\u9577": "音檔長度",
    "\u9a0e\u884c\u8def\u7dda": "自行車路線",
    "\u55ae\u8eca\u9a0e\u884c": "騎單車",
    "\u9a0e\u884c\u6587\u5316": "自行車文化",
    "\u9a0e\u884c\u9014\u4e2d": "騎車途中",
    "\u6563\u6b65\u6216\u9a0e\u884c": "散步或騎單車",
}
PATTERN = re.compile("|".join(sorted(REPLACEMENTS, key=len, reverse=True)))


def project_files():
    if (ROOT / ".git").exists():
        result = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
        )
        return [ROOT / name for name in result.decode("utf-8").split("\0") if name]
    # 解壓縮的原始碼也能離線檢查。
    return (path for path in ROOT.rglob("*") if "build" not in path.relative_to(ROOT).parts)


def main():
    issues = 0
    for path in project_files():
        if path.suffix.lower() not in TEXT or not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            for found in set(PATTERN.findall(line)):
                print(f"{path.relative_to(ROOT)}:{number}　{found} → {REPLACEMENTS[found]}")
                issues += 1
    if issues:
        print(f"找到 {issues} 處需要核對的文字。")
    else:
        print("常見簡體字與專案用詞檢查通過。")
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
