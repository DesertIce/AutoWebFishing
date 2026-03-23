from pathlib import Path
from unittest.mock import patch

import numpy as np

import AutoWebFishing as awf


class DummyAutomation:
    def __init__(self):
        self.actions = []

    def press(self, key):
        self.actions.append(("press", key))

    def click(self, x=None, y=None):
        self.actions.append(("click", x, y))

    def mouseDown(self, x=None, y=None):
        self.actions.append(("mouseDown", x, y))

    def mouseUp(self, x=None, y=None):
        self.actions.append(("mouseUp", x, y))

    def size(self):
        return (1920, 1080)


class DummyWindowBackend:
    def __init__(self):
        self.calls = []
        self.window_handle = 42
        self.frame = np.zeros((360, 640, 3), dtype=np.uint8)
        self.window_info = [
            {
                "hwnd": self.window_handle,
                "title": "Fish! (On the WEB!)",
                "exe_name": "webfishing.exe",
                "file_description": "Fish! (On the WEB!)",
            }
        ]

    def find_window(self, target):
        self.calls.append(("find_window", target))
        for info in self.window_info:
            if target.matches(info):
                return info["hwnd"]
        return None

    def get_client_size(self, hwnd):
        self.calls.append(("get_client_size", hwnd))
        return (640, 360)

    def capture_window(self, hwnd):
        self.calls.append(("capture_window", hwnd))
        return self.frame

    def click(self, hwnd, x, y):
        self.calls.append(("click", hwnd, x, y))

    def mouse_down(self, hwnd, x, y):
        self.calls.append(("mouse_down", hwnd, x, y))

    def mouse_up(self, hwnd, x=None, y=None):
        self.calls.append(("mouse_up", hwnd, x, y))

    def press_key(self, hwnd, key):
        self.calls.append(("press_key", hwnd, key))

    def key_down(self, hwnd, key):
        self.calls.append(("key_down", hwnd, key))

    def key_up(self, hwnd, key):
        self.calls.append(("key_up", hwnd, key))

    def is_window(self, hwnd):
        self.calls.append(("is_window", hwnd))
        return hwnd == self.window_handle


class DummyControlMonitor:
    def __init__(self, pause_events=None, stop_events=None):
        self.pause_events = list(pause_events or [])
        self.stop_events = list(stop_events or [])

    def consume_pause_toggle(self):
        return self.pause_events.pop(0) if self.pause_events else False

    def consume_stop_request(self):
        return self.stop_events.pop(0) if self.stop_events else False


class DummyDiagnostics:
    def __init__(self):
        self.snapshots = []

    def save_snapshot(self, reason, frame=None):
        self.snapshots.append(reason)
        return f"{reason}.png"


def test_all_configured_images_exist():
    image_paths = [
        awf.start_image,
        awf.catch_image,
        awf.stop_image,
        awf.reel1_image,
        awf.reel2_image,
        awf.wormx_image,
        awf.worm0_image,
        awf.cricketx_image,
        awf.cricket0_image,
        awf.leechx_image,
        awf.leech0_image,
        awf.minnowx_image,
        awf.minnow0_image,
        awf.squidx_image,
        awf.squid0_image,
        awf.nautilusx_image,
        awf.nautilus0_image,
        awf.shopWorm_image,
        awf.shopCricket_image,
        awf.shopLeech_image,
        awf.shopMinnow_image,
        awf.shopSquid_image,
        awf.shopNautilus_image,
        awf.sell_image,
    ]

    missing = [path for path in image_paths if not Path(path).is_file()]

    assert missing == []


def test_find_image_on_screen_returns_none_for_oversized_template():
    screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
    reference = np.zeros((20, 20), dtype=np.uint8)

    with patch.object(awf.pyautogui, "screenshot", return_value=screenshot), patch.object(
        awf.cv2, "imread", return_value=reference
    ):
        assert awf.find_image_on_screen("ignored.jpg") is None


def test_find_image_on_screen_matches_scaled_template_for_higher_resolution():
    rng = np.random.default_rng(1234)
    reference = rng.integers(0, 256, size=(12, 12), dtype=np.uint8)

    scaled_reference = awf.cv2.resize(reference, None, fx=1.35, fy=1.35, interpolation=awf.cv2.INTER_NEAREST)
    screenshot = np.zeros((80, 80, 3), dtype=np.uint8)
    top = 20
    left = 30
    screenshot[top : top + scaled_reference.shape[0], left : left + scaled_reference.shape[1], :] = scaled_reference[:, :, None]

    with patch.object(awf.pyautogui, "screenshot", return_value=screenshot), patch.object(
        awf.cv2, "imread", return_value=reference
    ):
        assert awf.find_image_on_screen("ignored.jpg", threshold=0.95) == (
            left + scaled_reference.shape[1] // 2,
            top + scaled_reference.shape[0] // 2,
        )


def test_cast_line_uses_screen_center_for_1440p():
    class LargeDummyAutomation(DummyAutomation):
        def size(self):
            return (2560, 1440)

    automation = LargeDummyAutomation()
    bot = awf.FishingBot(automation=automation, sleeper=lambda _: None, logger=lambda _: None)

    bot.cast_line()

    assert automation.actions == [
        ("mouseDown", 1280, 720),
        ("mouseUp", None, None),
    ]


def test_find_image_on_screen_uses_custom_screenshot_provider():
    screenshot = np.zeros((20, 20, 3), dtype=np.uint8)
    reference = np.zeros((4, 4), dtype=np.uint8)
    reference[1:3, 1:3] = 255
    screenshot[8:12, 6:10, :] = reference[:, :, None]

    with patch.object(awf.cv2, "imread", return_value=reference):
        assert (
            awf.find_image_on_screen(
                "ignored.jpg",
                threshold=0.99,
                screenshot_provider=lambda: screenshot,
                scale_factors=(1.0,),
            )
            == (8, 10)
        )


def test_window_automation_targets_named_window_for_input_and_capture():
    backend = DummyWindowBackend()
    automation = awf.WindowAutomation(
        awf.WindowTarget(executable_name="webfishing.exe"),
        backend=backend,
        logger=lambda _: None,
    )

    assert automation.size() == (640, 360)
    frame = automation.screenshot()
    automation.press("e")
    automation.click(100, 150)
    automation.mouseDown(200, 210)
    automation.mouseUp()

    assert frame is backend.frame
    assert backend.calls[0] == ("find_window", awf.WindowTarget(executable_name="webfishing.exe"))
    assert ("get_client_size", 42) in backend.calls
    assert ("capture_window", 42) in backend.calls
    assert ("press_key", 42, "e") in backend.calls
    assert ("click", 42, 100, 150) in backend.calls
    assert ("mouse_down", 42, 200, 210) in backend.calls
    assert ("mouse_up", 42, 200, 210) in backend.calls


def test_window_automation_releases_mouse_at_last_press_coordinates():
    backend = DummyWindowBackend()
    automation = awf.WindowAutomation(
        awf.WindowTarget(executable_name="webfishing.exe"),
        backend=backend,
        logger=lambda _: None,
    )

    automation.mouseDown(200, 210)
    automation.mouseUp()

    assert ("mouse_down", 42, 200, 210) in backend.calls
    assert ("mouse_up", 42, 200, 210) in backend.calls


def test_window_target_matches_executable_name_and_file_description():
    target = awf.WindowTarget(
        executable_name="webfishing.exe",
        file_description="Fish! (On the WEB!)",
    )

    assert target.matches(
        {
            "title": "anything",
            "exe_name": "WebFishing.exe",
            "file_description": "Fish! (On the WEB!)",
        }
    )


def test_create_default_automation_prefers_webfishing_identifiers():
    backend = DummyWindowBackend()
    logs = []

    with patch.object(awf, "Win32WindowBackend", return_value=backend), patch.dict(
        awf.os.environ,
        {},
        clear=True,
    ):
        automation = awf.create_default_automation(logger=logs.append)

    assert isinstance(automation, awf.WindowAutomation)
    assert automation.size() == (640, 360)
    assert backend.calls[0] == (
        "find_window",
        awf.WindowTarget(
            title_substring="WEBFISHING",
            executable_name="webfishing.exe",
            file_description="Fish! (On the WEB!)",
        ),
    )


def test_window_automation_reacquires_invalid_window_handle():
    class ReacquireBackend(DummyWindowBackend):
        def __init__(self):
            super().__init__()
            self.window_handle = 84
            self.handles = [42, 84]

        def find_window(self, target):
            self.calls.append(("find_window", target))
            return self.handles.pop(0)

        def is_window(self, hwnd):
            self.calls.append(("is_window", hwnd))
            return hwnd == 84

    backend = ReacquireBackend()
    automation = awf.WindowAutomation(
        awf.WindowTarget(executable_name="webfishing.exe"),
        backend=backend,
        logger=lambda _: None,
        refresh_interval=0.0,
    )

    assert automation.size() == (640, 360)
    assert automation.size() == (640, 360)
    assert [call for call in backend.calls if call[0] == "find_window"] == [
        ("find_window", awf.WindowTarget(executable_name="webfishing.exe")),
        ("find_window", awf.WindowTarget(executable_name="webfishing.exe")),
    ]


def test_load_bot_config_reads_environment_overrides():
    with patch.dict(
        awf.os.environ,
        {
            "AWF_IDLE_TIMEOUT": "99",
            "AWF_JITTER_FRACTION": "0.0",
            "AWF_PAUSE_HOTKEY": "F10",
            "AWF_FALLBACK_TO_DESKTOP": "1",
        },
        clear=True,
    ):
        config = awf.load_bot_config()

    assert config.idle_timeout == 99.0
    assert config.jitter_fraction == 0.0
    assert config.pause_hotkey == "F10"
    assert config.fallback_to_desktop_on_window_failure is True


def test_handle_control_events_toggles_pause_and_stop():
    bot = awf.FishingBot(
        sleeper=lambda _: None,
        logger=lambda _: None,
        control_monitor=DummyControlMonitor(pause_events=[True, True], stop_events=[False, True]),
    )

    assert bot.handle_control_events() == "paused"
    assert bot.paused is True
    assert bot.handle_control_events() == "stop_requested"
    assert bot.stop_requested is True


def test_run_step_saves_debug_snapshot_after_prolonged_idle():
    now = {"value": 0.0}
    diagnostics = DummyDiagnostics()
    bot = awf.FishingBot(
        sleeper=lambda _: None,
        clock=lambda: now["value"],
        logger=lambda _: None,
        diagnostics=diagnostics,
        config=awf.BotConfig(idle_timeout=60.0, debug_snapshot_after=10.0, debug_snapshot_cooldown=30.0),
    )
    bot.last_progress_at = 0.0
    bot.is_visible = lambda image_path, threshold=0.8: False
    bot.is_any_visible = lambda image_paths, threshold=0.8: False
    bot.capture_debug_frame = lambda: np.zeros((10, 10, 3), dtype=np.uint8)

    now["value"] = 11.0
    assert bot.run_step() == "idle"
    assert diagnostics.snapshots == ["idle_no_match"]


def test_ensure_bait_returns_false_when_restock_shop_cannot_be_verified():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    calls = []

    bot.select_bait_from_inventory = lambda: calls.append("select") or False
    bot.restock_bait = lambda: calls.append("restock") or False

    assert bot.ensure_bait() is False
    assert calls == ["select", "restock"]


def test_create_default_automation_raises_when_window_targeting_fails_and_fallback_disabled():
    with patch.object(
        awf,
        "WindowAutomation",
        side_effect=awf.WindowLookupError("missing"),
    ), patch.dict(
        awf.os.environ,
        {"AWF_FALLBACK_TO_DESKTOP": "0"},
        clear=True,
    ):
        try:
            awf.create_default_automation(logger=lambda _: None)
        except awf.WindowLookupError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("expected WindowLookupError")


def test_select_bait_from_inventory_prefers_highest_priority_available_bait():
    automation = DummyAutomation()
    responses = {
        awf.nautilus0_image: (1, 1),
        awf.squid0_image: (1, 1),
        awf.minnow0_image: None,
        awf.minnowx_image: (300, 400),
    }

    bot = awf.FishingBot(
        automation=automation,
        finder=lambda image_path, threshold=0.8: responses.get(image_path),
        sleeper=lambda _: None,
        logger=lambda _: None,
    )

    assert bot.select_bait_from_inventory() is True
    assert automation.actions == [
        ("press", "b"),
        ("click", 300, 400),
        ("press", "b"),
    ]


def test_ensure_bait_retries_after_restock():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    calls = []

    def fake_select():
        calls.append("select")
        return calls.count("select") == 2

    bot.select_bait_from_inventory = fake_select
    bot.restock_bait = lambda: calls.append("restock") or True

    assert bot.ensure_bait() is True
    assert calls == ["select", "restock", "select"]


def test_handle_hooked_fish_releases_mouse_if_catch_prompt_never_appears():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    events = []

    bot.hold_left_button = lambda: events.append("hold") or True
    bot.release_left_button = lambda: events.append("release")
    bot.wait_for_any_visible = lambda image_paths, timeout: None

    assert bot.handle_hooked_fish() is False
    assert events == ["hold", "release"]


def test_run_step_recovers_after_idle_timeout():
    now = {"value": 0.0}
    bot = awf.FishingBot(
        sleeper=lambda _: None,
        clock=lambda: now["value"],
        config=awf.BotConfig(idle_timeout=10.0),
        logger=lambda _: None,
    )
    bot.last_progress_at = 0.0
    bot.is_visible = lambda image_path: False
    bot.is_any_visible = lambda image_paths: False

    recovered = []
    bot.recover_from_idle = lambda: recovered.append("recover")

    now["value"] = 11.0

    assert bot.run_step() == "recovered_idle"
    assert recovered == ["recover"]


def test_handle_hooked_fish_does_not_cast_again_when_catch_dialog_stays_visible():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    events = []

    bot.hold_left_button = lambda: events.append("hold") or True
    bot.release_left_button = lambda: events.append("release")
    bot.wait_for_any_visible = lambda image_paths, timeout: awf.catch_image
    bot.dismiss_catch_dialog = lambda: events.append("dismiss")
    bot.is_visible = lambda image_path, threshold=0.8: image_path == awf.catch_image
    bot.cast_line = lambda: events.append("cast")
    bot.ensure_bait = lambda: events.append("bait")

    assert bot.handle_hooked_fish() is False
    assert events == ["hold", "release", "dismiss"]


def test_run_step_does_not_cast_when_bait_is_still_unavailable():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    events = []

    bot.is_visible = lambda image_path, threshold=0.8: image_path == awf.stop_image
    bot.is_any_visible = lambda image_paths, threshold=0.8: False
    bot.ensure_bait = lambda: False
    bot.cast_line = lambda: events.append("cast")

    assert bot.run_step() == "bait_unavailable"
    assert events == []


def test_run_step_recovers_immediately_after_hook_timeout():
    bot = awf.FishingBot(sleeper=lambda _: None, logger=lambda _: None)
    events = []

    bot.is_visible = lambda image_path, threshold=0.8: False
    bot.is_any_visible = lambda image_paths, threshold=0.8: True
    bot.handle_hooked_fish = lambda: False
    bot.recover_from_idle = lambda: events.append("recover")

    assert bot.run_step() == "hook_timeout_recovered"
    assert events == ["recover"]


def test_is_any_visible_checks_multiple_templates_against_one_captured_frame():
    rng = np.random.default_rng(4321)
    missing_reference = rng.integers(0, 256, size=(6, 6), dtype=np.uint8)
    present_reference = rng.integers(0, 256, size=(6, 6), dtype=np.uint8)

    first_frame = np.zeros((40, 40, 3), dtype=np.uint8)
    first_frame[14:20, 18:24, :] = present_reference[:, :, None]
    second_frame = np.zeros((40, 40, 3), dtype=np.uint8)

    class AlternatingScreenshotAutomation(DummyAutomation):
        def __init__(self):
            super().__init__()
            self.capture_count = 0

        def screenshot(self):
            self.capture_count += 1
            return first_frame if self.capture_count == 1 else second_frame

    references = {
        "missing.jpg": missing_reference,
        "present.jpg": present_reference,
    }
    automation = AlternatingScreenshotAutomation()
    bot = awf.FishingBot(automation=automation, sleeper=lambda _: None, logger=lambda _: None)

    with patch.object(awf.cv2, "imread", side_effect=lambda path, _: references[path]):
        assert bot.is_any_visible(["missing.jpg", "present.jpg"], threshold=0.99) is True

    assert automation.capture_count == 1
