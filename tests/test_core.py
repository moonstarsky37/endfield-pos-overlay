import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from endfield_pos_overlay import i18n
from endfield_pos_overlay.core import (
    FONT_MAX, FONT_MIN, MIN_H, MIN_W, SAMPLE_FRAME, DEFAULT_FONT_SIZE, Frame, Prefs, State,
    clamp_geometry, compose_view, default_geometry, font_size_for_height, format_coords,
    height_for_font_size, load_prefs, ordered_triple, parse_frame, parse_geometry, prefs_from_dict,
    save_prefs, to_blender,
)
from endfield_pos_overlay.osutil import pick_font
from endfield_pos_overlay.server import RelayServer, make_handler, origin_allowed


class ParseTests(unittest.TestCase):
    def test_sample_1012(self):
        frame = parse_frame(SAMPLE_FRAME)
        self.assertEqual(frame.kind, "pos")
        self.assertEqual((frame.pos.x, frame.pos.y, frame.pos.z), (505.20776, 234.22778, 1100.9303))
        self.assertEqual((frame.pos.map_id, frame.pos.level_id, frame.pos.is_online), ("map02", "map02_lv010", True))
        self.assertEqual(parse_frame(SAMPLE_FRAME.encode("utf-8")), frame)

    def test_orders(self):
        self.assertEqual(to_blender(1, 2, 3), (1, 3, 2))
        pos = parse_frame(SAMPLE_FRAME).pos
        self.assertEqual(ordered_triple(pos, "raw"), (505.20776, 234.22778, 1100.9303))
        self.assertEqual(ordered_triple(pos, "blender"), (505.20776, 1100.9303, 234.22778))

    def test_format(self):
        self.assertEqual(format_coords((505.20776, 1100.9303, 234.22778)), "505.21, 1100.93, 234.23")
        self.assertEqual(format_coords((-314.0, 323.0, 400.0)), "-314.00, 323.00, 400.00")
        self.assertEqual(i18n.format_age(0.42, "zh"), "0.4 秒前")
        self.assertEqual(i18n.format_age(65.0, "zh"), "1 分 5 秒前")
        self.assertEqual(i18n.format_age(0.42, "en"), "0.4 s ago")
        self.assertEqual(i18n.format_age(65.0, "en"), "1 min 5 s ago")
        self.assertEqual(i18n.format_age(-1.0, "en"), "0.0 s ago")

    def test_garbage_ignored(self):
        for bad in ('{"type":1,"data":{"token":"x"}}', '{"type":"1012","data":{}}', '{"type":true}',
                    '{"type":1012,"data":{"pos":{"x":"a","y":1,"z":2}}}', '{"type":1012,"data":{"pos":{"x":1,"y":2}}}',
                    '{"type":1012,"data":{"pos":{"x":1,"y":2,"z":NaN}}}', '{"type":1012,"data":null}',
                    "[1,2,3]", '"hello"', "not json", b"\xff\xfe", ""):
            self.assertIsNone(parse_frame(bad), bad)

    def test_control_frames(self):
        self.assertEqual(parse_frame('{"type":1011,"data":{}}'), Frame("init"))
        self.assertEqual(parse_frame('{"type":1013}'), Frame("off"))
        self.assertEqual(parse_frame('{"type":"relay","event":"open"}'), Frame("relay", event="open"))
        self.assertEqual(parse_frame('{"type":"relay","event":"close"}'), Frame("relay", event="close"))
        self.assertIsNone(parse_frame('{"type":"relay","event":"bogus"}'))
        self.assertIsNone(parse_frame('{"type":"relay"}'))


class StateTests(unittest.TestCase):
    def test_lifecycle(self):
        state = State()
        pos_frame = parse_frame(SAMPLE_FRAME)
        v0 = compose_view(state.snapshot(), 100.0, "raw", "zh")
        self.assertEqual(v0.status, "等待網頁同步位置…")
        self.assertFalse(v0.has_pos)
        state.apply(pos_frame, 100.0)
        v1 = compose_view(state.snapshot(), 100.4, "raw", "zh")
        self.assertTrue(v1.online)
        self.assertEqual(v1.status, "0.4 秒前")
        self.assertEqual(v1.values, ("505.21", "234.23", "1100.93"))
        self.assertEqual(v1.header, "武陵 · 祀的畫")
        self.assertEqual(compose_view(state.snapshot(), 100.4, "blender", "zh").values, ("505.21", "1100.93", "234.23"))
        self.assertEqual(compose_view(state.snapshot(), 100.4, "raw", "en").header, "Wuling · map02_lv010")
        self.assertTrue(compose_view(state.snapshot(), 106.0, "raw", "zh").stale)
        state.apply(parse_frame('{"type":"relay","event":"close"}'), 101.0)
        v2 = compose_view(state.snapshot(), 101.5, "raw", "en")
        self.assertFalse(v2.online)
        self.assertTrue(v2.status.startswith("Page offline"))
        state.apply(parse_frame('{"type":"relay","event":"open"}'), 102.0)
        state.apply(pos_frame, 102.0)
        self.assertTrue(compose_view(state.snapshot(), 102.1, "raw", "zh").online)
        state.apply(parse_frame('{"type":1013}'), 103.0)
        self.assertFalse(compose_view(state.snapshot(), 103.1, "raw", "zh").online)
        state.apply(pos_frame, 104.0)
        self.assertTrue(compose_view(state.snapshot(), 104.1, "raw", "zh").online)
        state.apply(parse_frame(SAMPLE_FRAME.replace('"isOnline":true', '"isOnline":false')), 105.0)
        self.assertFalse(compose_view(state.snapshot(), 105.1, "raw", "zh").online)
        self.assertEqual(state.snapshot().frames, 7)


class I18nTests(unittest.TestCase):
    def test_names_fallback(self):
        self.assertEqual(i18n.level_name("map01_lv001", "zh"), "樞紐區")
        self.assertEqual(i18n.level_name("map09_lv999", "zh"), "map09_lv999")
        self.assertEqual(i18n.level_name("map01_lv001", "en"), "map01_lv001")
        self.assertEqual(i18n.place_header("", "", "zh"), "")

    def test_resolve_lang(self):
        self.assertEqual(i18n.resolve_lang("zh"), "zh")
        self.assertEqual(i18n.resolve_lang("en"), "en")
        self.assertEqual(i18n.resolve_lang("auto", "zh_TW.UTF-8"), "zh")
        self.assertEqual(i18n.resolve_lang("auto", "en_US"), "en")
        self.assertEqual(i18n.resolve_lang("auto", ""), "en")

    def test_same_keys(self):
        self.assertEqual(set(i18n.STRINGS["zh"]), set(i18n.STRINGS["en"]))


class GeometryPrefsTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(parse_geometry("340x150+120+120"), (340, 150, 120, 120))
        self.assertEqual(parse_geometry("340x150-10+5"), (340, 150, -10, 5))
        self.assertIsNone(parse_geometry("garbage"))
        screen = (-1920, 0, 3840, 1080)
        self.assertEqual(clamp_geometry(340, 150, 5000, 5000, screen), (340, 150, 1580, 930))
        self.assertEqual(clamp_geometry(340, 150, -9999, -9999, screen), (340, 150, -1920, 0))
        self.assertEqual(clamp_geometry(10, 10, 0, 0, screen)[:2], (MIN_W, MIN_H))
        self.assertEqual(font_size_for_height(height_for_font_size(20)), 20)
        self.assertEqual(font_size_for_height(height_for_font_size(20, 2.0), 2.0), 20)
        self.assertTrue(FONT_MIN <= font_size_for_height(10) <= FONT_MAX)
        self.assertEqual(default_geometry()[:2], (340, height_for_font_size(DEFAULT_FONT_SIZE)))
        self.assertEqual(default_geometry(2.0)[0], 510)

    def test_prefs(self):
        self.assertEqual(Prefs().order, "raw")
        self.assertEqual(prefs_from_dict("junk"), Prefs())
        self.assertEqual(prefs_from_dict({"geometry": "bad", "font_size": 999, "alpha": "x", "order": "weird",
                                          "lang": "fr"}), Prefs())
        p = prefs_from_dict({"geometry": "400x200+1+2", "font_size": 30, "alpha": 0.7, "order": "blender", "lang": "en"})
        self.assertEqual(p, Prefs("400x200+1+2", 30, 0.7, "blender", "en"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "state.json"
            self.assertEqual(load_prefs(path), Prefs())
            self.assertIsNone(save_prefs(path, p))
            self.assertEqual(load_prefs(path), p)

    def test_pick_font(self):
        self.assertEqual(pick_font({"menlo", "Arial"}, ("Consolas", "Menlo")), "menlo")
        self.assertEqual(pick_font(set(), ("Consolas",)), "TkDefaultFont")


class ServerTests(unittest.TestCase):
    def test_origin_rule(self):
        for ok in (None, "", "chrome-extension://abc", "moz-extension://x-y", "https://game.skport.com", "null"):
            self.assertTrue(origin_allowed(ok), ok)
        for bad in ("https://evil.example", "http://127.0.0.1:8000", "https://game.skport.com.evil.example"):
            self.assertFalse(origin_allowed(bad), bad)

    def test_http(self):
        state = State()
        server = RelayServer(("127.0.0.1", 0), make_handler(state, time.monotonic))
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

        def req(method, path, body=None, headers=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            data = resp.read()
            conn.close()
            return resp.status, data

        try:
            self.assertEqual(req("POST", "/pos", SAMPLE_FRAME.encode(), {"Content-Type": "application/json"})[0], 204)
            self.assertEqual(req("POST", "/pos", b'{"type":"relay","event":"close"}',
                                 {"Origin": "chrome-extension://abc"})[0], 204)
            self.assertEqual(req("POST", "/pos", b"garbage")[0], 204)
            self.assertEqual(req("POST", "/pos", SAMPLE_FRAME.encode(), {"Origin": "https://evil.example"})[0], 403)
            self.assertEqual(req("OPTIONS", "/pos")[0], 405)
            status, data = req("GET", "/health")
            self.assertEqual(status, 200)
            health = json.loads(data)
            self.assertTrue(health["ok"])
            self.assertEqual(health["frames"], 2)
            self.assertIsInstance(health["last_update_age_s"], float)
            self.assertEqual(req("GET", "/nope")[0], 404)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
