"""产生配音任务清单 art/voice/jobs.json（台词、表演指令、输出档名）。页面的 LINES 也以此为准。

用法：python -I -B tools/voice_jobs.py <项目根目录>
"""
import json, re, sys
from pathlib import Path

ROLE = "你是一個活潑、有點黏人又很貼心的狼耳少年嚮導，正陪著對方在鹿港老街散步，像熟朋友在身邊說話，自然口語，不要像在朗讀。"
LINES = {
    "greet":  (["這一支，我替你抽好了。跟著我。", "走吧，有個地方在等你。"], "語氣雀躍、帶著期待，像拉著朋友出門。"),
    "far":    (["還有一段路，慢慢來。", "不急，我們慢慢走。"], "輕鬆、陪伴感，語速稍慢。"),
    "half":   (["走一半了。", "過半了，你走得不錯。"], "輕快地鼓勵對方，帶一點笑意。"),
    "near":   (["快到了，抬頭看看。", "就在這附近了。"], "興奮但壓低聲音，有點神秘，像要揭曉驚喜。"),
    "behind": (["在你後面啦，轉個身。", "方向反了，往回一點。"], "有點著急、帶點撒嬌地嘟嘴，像拉著對方的袖子往回拖。"),
    "idle":   (["停下來了？歇一下也好。", "我在這，等你。"], "溫柔、關心，聲音放軟。"),
    "weak":   (["訊號不太好，先站一下。"], "關心、輕聲提醒，不慌張。"),
    "bye":    (["今天就走到這吧。", "下次再一起抽一支。"], "依依不捨，聲音軟、語速慢，句尾輕輕收住。"),
}
ARRIVED = ("到了！是{name}。", "非常開心地歡呼，像跳起來宣布答案，名字說得清楚。")


def spoken(name):
    """念出來用的地名：去括号、去「鹿港」前缀、太长的缩短、异体字换常用字。"""
    fix = {"中央廣播電臺鹿港分臺暨周遭廣播設施地景文化景觀": "中央廣播電臺鹿港分臺",
           "福興鄉農會碾米廠暨穀倉": "福興鄉農會碾米廠"}
    n = fix.get(name, name)
    n = re.sub(r"[（(].*?[)）]", "", n).replace("舘", "館")
    if n.startswith("鹿港") and len(n) > 4:
        n = n[2:]
    return n


def main(root):
    places = json.loads((root / "data" / "lukang.json").read_text(encoding="utf-8"))
    jobs = []
    for ev, (texts, mood) in LINES.items():
        for i, t in enumerate(texts):
            jobs.append({"file": f"{ev}_{i}.mp3", "event": ev, "text": t, "instructions": ROLE + mood})
    for p in places:
        jobs.append({"file": f"arrived_{p['id']}.mp3", "event": "arrived", "place_id": p["id"],
                     "text": ARRIVED[0].format(name=spoken(p["name"])), "instructions": ROLE + ARRIVED[1]})
    out = root / "art" / "voice" / "jobs.json"
    out.write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(jobs), "句 →", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
