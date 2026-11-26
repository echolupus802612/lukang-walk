"""在桌面 WebKit 用模擬的 iOS 訊息測試實際打包頁面。

測試依賴：pip install playwright==1.49.1，接著執行 playwright install webkit。
用法：python tools/test_ios_bridge.py
"""
import json
import unittest
from datetime import datetime, timezone
from math import degrees
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ENTRY = (ROOT / "docs/index.html").as_uri()
# 固定選點亂數為零。從資料第一處以北約 220 公尺選「近」，必定選到該處（鹿港資料排在全台資料前面）。
PLACE = json.loads((ROOT / "data/lukang.json").read_text(encoding="utf-8"))[0]
ORIGIN = (PLACE["lat"] + 0.002, PLACE["lng"])
DESTINATION = (PLACE["lat"], PLACE["lng"])
TAIWAN = json.loads((ROOT / "data/taiwan.json").read_text(encoding="utf-8"))
NANTOU = next(p for p in TAIWAN if p["id"] == 1001)
# 由資料最北點沿經線繼續往北，最近距離可獨立算出，不依賴選點程式。
NORTHERNMOST = max(TAIWAN, key=lambda p: p["lat"])


def north_of_edge(meters):
    return (NORTHERNMOST["lat"] + degrees(meters / 6_371_000), NORTHERNMOST["lng"])

BRIDGE = """
    window.nativeMessages = [];
    window.webkit = {messageHandlers: {lukangWalk: {
        postMessage(message) { window.nativeMessages.push(structuredClone(message)); }
    }}};
    window.lukangInitialStore = {ver: 2, voice: false, drawn: 4, sim_drawn: 7};
    Math.random = () => 0;
"""


class WalkBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.webkit.launch()
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 390, "height": 844})
        self.addCleanup(self.page.context.close)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.add_init_script(BRIDGE)
        self.page.clock.install(time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.page.clock.pause_at(datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc))
        self.page.goto(ENTRY, wait_until="domcontentloaded")

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def click(self, selector):
        button = self.page.locator(selector)
        self.assertTrue(button.is_visible() and button.is_enabled(), selector)
        button.click(force=True)

    def label(self, selector):
        return self.page.locator(selector).inner_text()

    def messages(self, action):
        return self.page.evaluate(
            "action => window.nativeMessages.filter(m => m.action === action)", action
        )

    def writes(self):
        return [m["values"] for m in self.messages("store")]

    def start(self):
        self.click('#bands [data-b="0"]')
        self.click("#go")
        return self.messages("start")[-1]["session"]

    def send(self, event, session, **fields):
        detail = dict(type=event, session=session, **fields)
        self.page.evaluate(
            "detail => dispatchEvent(new CustomEvent('lukangNative', {detail}))", detail
        )

    def fix(self, session, point, age=0, accuracy=5):
        timestamp = self.page.evaluate("Date.now()") - age
        self.send("position", session, timestamp=timestamp, coords={
            "latitude": point[0], "longitude": point[1], "accuracy": accuracy, "speed": 0
        })

    def assert_simulated(self, session, reason):
        self.assertEqual(self.label("#mode"), "模擬行走")
        self.assertIn(reason, self.label("#foot"))
        self.assertTrue(self.page.locator("#stepTo").is_visible())
        self.assertIn({"sim_drawn": 8}, self.writes())
        self.assertEqual(self.messages("stop"), [{"action": "stop", "session": session}])
        self.assertNotIn(PLACE["name"], self.label("body"))

    def test_ready_and_credits_do_not_request_sensors(self):
        self.page.clock.fast_forward(15000)
        self.assertEqual(self.messages("start"), [])
        self.assertFalse(self.page.locator("#walkrow").is_visible())
        self.assertIn("出發過 4 次", self.label("#sub"))
        self.click("#credits")
        self.assertEqual(self.messages("credits"), [{"action": "credits"}])
        self.assertEqual(self.page.url, ENTRY)
        self.assertEqual(self.messages("start"), [])

    def test_denied_and_stale_callbacks(self):
        session = self.start()
        self.send("error", session, reason="denied")
        self.assert_simulated(session, "未取得定位權限")
        self.fix(session, DESTINATION)
        self.send("heading", session, degrees=180)
        self.assertEqual(self.label("#mode"), "模擬行走")
        self.assertEqual(self.messages("arrived"), [])

    def test_approximate_location(self):
        session = self.start()
        self.send("error", session, reason="approximate")
        self.assert_simulated(session, "大概位置")

    def test_far_from_any_place(self):
        session = self.start()
        self.fix(session, (ORIGIN[0] + 1, ORIGIN[1]))
        self.assert_simulated(session, "5 公里內還沒有收錄")

    def test_nantou_real_walk_reveals_and_saves_national_place(self):
        session = self.start()
        destination = (NANTOU["lat"], NANTOU["lng"])
        self.fix(session, (NANTOU["lat"] + 0.002, NANTOU["lng"]), age=750)
        self.assertIn({"drawn": 5}, self.writes())
        self.assertEqual(self.label("#mode"), "GPS（無指南針）")
        self.assertFalse(self.page.locator("#stepTo").is_visible())
        self.assertNotIn(NANTOU["name"], self.label("body"))
        self.fix(session, destination, age=500)
        self.assertEqual(self.messages("arrived"), [])
        self.fix(session, destination)
        self.page.clock.fast_forward(1800)
        self.assertEqual(self.label("#cname"), NANTOU["name"])
        self.assertEqual(self.label("#cdesc"), NANTOU["desc"])
        photo = self.page.locator("#cph")
        self.assertTrue(photo.is_visible())
        self.assertEqual(photo.get_attribute("src"), f"photos/{NANTOU['id']}.webp")
        self.assertGreater(photo.evaluate("async image => { await image.decode(); return image.naturalWidth; }"), 0)
        self.assertIn({"seen": [NANTOU["id"]], "recent": [NANTOU["id"]]}, self.writes())
        self.assertFalse(any("sim_drawn" in v or "sim_seen" in v for v in self.writes()))

    def test_just_inside_5km_waits_for_consent_to_walk_farther(self):
        point = north_of_edge(4999)
        session = self.start()
        self.fix(session, point)
        self.assertEqual(self.label("#go"), "那就走遠一點")
        self.assertIn("5.0 公里", self.label("#hint"))
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.messages("stop"), [{"action": "stop", "session": session}])
        self.assertFalse(self.messages("awake")[-1]["enabled"])
        self.assertFalse(self.page.locator("#stepTo").is_visible())
        self.click("#go")
        second = self.messages("start")[-1]["session"]
        self.assertNotEqual(second, session)
        self.fix(second, point)
        self.assertEqual(self.label("#mode"), "GPS（無指南針）")
        self.assertTrue(self.page.locator("#stop").is_visible())
        self.assertIn({"drawn": 5}, self.writes())

    def test_just_outside_5km_falls_back_to_lukang_simulation(self):
        session = self.start()
        self.fix(session, north_of_edge(5001))
        self.assert_simulated(session, "鹿港天后宮前模擬")
        self.assertFalse(any("drawn" in v for v in self.writes()))

    def test_permission_lost_while_walking_draws_in_separate_book(self):
        session = self.start()
        self.fix(session, ORIGIN)
        self.assertIn({"drawn": 5}, self.writes())
        self.send("error", session, reason="denied")
        self.assert_simulated(session, "定位中斷")
        self.assertFalse(any("seen" in v or "sim_seen" in v for v in self.writes()))
        self.click("#stop")
        second = self.start()
        self.fix(second, ORIGIN)
        self.assertIn({"drawn": 6}, self.writes())
        self.assertEqual(self.label("#mode"), "GPS（無指南針）")

    def test_timeout_after_twelve_seconds(self):
        session = self.start()
        self.page.clock.fast_forward(11999)
        self.assertFalse(self.page.locator("#stepTo").is_visible())
        self.assertEqual(self.writes(), [])
        self.page.clock.fast_forward(1)
        self.assert_simulated(session, "拿不到目前位置")

    def test_simulated_hold_and_arrival(self):
        session = self.start()
        self.send("error", session, reason="denied")
        step = self.page.locator("#stepTo")
        self.assertTrue(step.is_visible())
        before = self.label("#dist")
        step.dispatch_event("pointerdown")
        for _ in range(10):
            self.page.clock.fast_forward(100)
        step.dispatch_event("pointerup")
        after = self.label("#dist")
        self.assertNotEqual(before, after)
        self.page.clock.fast_forward(500)
        self.assertEqual(self.label("#dist"), after)

        step.dispatch_event("pointerdown")
        # 「近」至多 500 公尺；逐個計時器區間推進，保留長按的完整事件序列。
        for _ in range(25):
            for _ in range(20):
                self.page.clock.fast_forward(100)
            if self.messages("arrived"):
                break
        step.dispatch_event("pointerup")
        self.page.clock.fast_forward(1800)
        self.assertTrue(self.page.locator('#veil [role="dialog"]').is_visible())
        # App 版尚未接上相機與原生分享，地點卡不顯示「拍一張留念」
        self.assertFalse(self.page.locator("#snap").is_visible())
        self.assertEqual(len(self.messages("arrived")), 1)
        saved, = [v for v in self.writes() if "sim_seen" in v]
        self.assertEqual(saved["sim_seen"], saved["sim_recent"])
        self.assertEqual(len(saved["sim_seen"]), 1)
        self.assertFalse(any("drawn" in v or "seen" in v for v in self.writes()))
        self.assertFalse(self.messages("awake")[-1]["enabled"])
        self.click("#again")
        self.assertTrue(self.page.locator("#go").is_visible())

    def test_real_arrival_requires_two_distinct_fresh_accurate_fixes(self):
        session = self.start()
        self.fix(session, ORIGIN, age=1000)
        self.assertEqual(self.label("#mode"), "GPS（無指南針）")
        self.assertIn("沒有指南針", self.label("#sub"))
        self.assertNotIn(PLACE["name"], self.label("body"))
        self.assertIn({"drawn": 5}, self.writes())
        self.send("heading", session, degrees=15)
        self.assertEqual(self.label("#mode"), "GPS 實走")
        self.send("heading", session, degrees=None)
        self.assertIn("沒有指南針", self.label("#sub"))
        self.page.clock.fast_forward(4000)  # 過期定位仍比上一筆新，獨立檢查兩秒門檻。
        self.fix(session, DESTINATION, age=3000)
        self.assertIn("沒有指南針", self.label("#sub"))
        self.fix(session, DESTINATION, age=850)
        self.assertIn("確認位置", self.label("#sub"))
        self.fix(session, DESTINATION, age=850)
        self.assertEqual(self.messages("arrived"), [])
        self.fix(session, DESTINATION, age=700, accuracy=65)
        self.assertIn("等定位準一點", self.label("#sub"))
        self.fix(session, DESTINATION, age=600)
        self.assertEqual(self.messages("arrived"), [])
        self.send("pause", session)
        self.fix(session, DESTINATION, age=500)
        self.assertEqual(self.messages("arrived"), [])
        self.fix(session, DESTINATION, age=400)
        self.assertEqual(len(self.messages("arrived")), 1)
        self.assertFalse(self.page.locator("#walkrow").is_visible())
        self.page.clock.fast_forward(1799)
        self.assertFalse(self.page.locator("#veil").is_visible())
        self.page.clock.fast_forward(1)
        self.assertEqual(self.label("#cname"), PLACE["name"])
        self.assertTrue(self.page.locator("#again").is_visible())
        self.assertIn({"seen": [PLACE["id"]], "recent": [PLACE["id"]]}, self.writes())
        self.assertEqual(self.messages("stop"), [{"action": "stop", "session": session}])
        self.assertFalse(self.messages("awake")[-1]["enabled"])
        self.fix(session, DESTINATION)
        self.assertEqual(len(self.messages("arrived")), 1)

        self.click("#again")
        second = self.start()
        self.assertNotEqual(second, session)
        self.send("error", session, reason="denied")
        self.fix(second, ORIGIN)
        self.assertTrue(self.page.locator("#redraw").is_visible())
        self.click("#redraw")
        self.assertIn({"drawn": 7}, self.writes())
        self.click("#voice")
        self.assertIn({"voice": True}, self.writes())
        self.click("#stop")
        self.assertEqual(self.label("#mode"), "已收工")
        self.assertEqual(self.messages("stop")[-1]["session"], second)
        self.assertFalse(self.messages("awake")[-1]["enabled"])
        self.send("error", second, reason="denied")
        self.assertEqual(self.label("#mode"), "已收工")
        self.send("storeError", None)
        self.assertIn("還沒存好", self.label("#storageWarning"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
