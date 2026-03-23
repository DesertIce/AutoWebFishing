import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import random
import time

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab


BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "Screenshots"


def screenshot_path(filename):
    return str(SCREENSHOTS_DIR / filename)


# Path to reference images
# stuff related to fishing
start_image = screenshot_path("start.jpg")
catch_image = screenshot_path("catch.jpg")
stop_image = screenshot_path("stop.jpg")
reel1_image = screenshot_path("reel1.jpg")
reel2_image = screenshot_path("reel2.jpg")

# stuff related to inventory
wormx_image = screenshot_path("Wormsx.jpg")
worm0_image = screenshot_path("Worms0.jpg")
cricketx_image = screenshot_path("Cricketsx.jpg")
cricket0_image = screenshot_path("Crickets0.jpg")
leechx_image = screenshot_path("Leechesx.jpg")
leech0_image = screenshot_path("Leeches0.jpg")
minnowx_image = screenshot_path("Minnowsx.jpg")
minnow0_image = screenshot_path("Minnows0.jpg")
squidx_image = screenshot_path("Squidsx.jpg")
squid0_image = screenshot_path("Squids0.jpg")
nautilusx_image = screenshot_path("Nautilusesx.jpg")
nautilus0_image = screenshot_path("Nautiluses0.jpg")

# stuff for shopping
shopWorm_image = screenshot_path("shopWorm.jpg")
shopCricket_image = screenshot_path("shopCricket.jpg")
shopLeech_image = screenshot_path("shopLeech.jpg")
shopMinnow_image = screenshot_path("shopMinnow.jpg")
shopSquid_image = screenshot_path("shopSquid.jpg")
shopNautilus_image = screenshot_path("shopNautilus.jpg")
sell_image = screenshot_path("sellall.jpg")


REEL_TRIGGER_IMAGES = [reel1_image, reel2_image, start_image]
BAIT_IMAGE_PRIORITY = [
    (nautilus0_image, nautilusx_image),
    (squid0_image, squidx_image),
    (minnow0_image, minnowx_image),
    (leech0_image, leechx_image),
    (cricket0_image, cricketx_image),
    (worm0_image, wormx_image),
]
SHOP_IMAGES = [
    sell_image,
    shopNautilus_image,
    shopSquid_image,
    shopMinnow_image,
    shopLeech_image,
    shopCricket_image,
    shopWorm_image,
]
TEMPLATE_SCALE_FACTORS = tuple([1.0] + [round(scale, 2) for scale in np.arange(0.6, 1.65, 0.05) if round(scale, 2) != 1.0])


class WindowLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowTarget:
    title_substring: str | None = None
    executable_name: str | None = None
    file_description: str | None = None

    def matches(self, window_info):
        checks = []

        if self.title_substring:
            title = (window_info.get("title") or "").lower()
            checks.append(self.title_substring.lower() in title)

        if self.executable_name:
            exe_name = Path(window_info.get("exe_name") or "").name.lower()
            checks.append(Path(self.executable_name).name.lower() == exe_name)

        if self.file_description:
            description = (window_info.get("file_description") or "").lower()
            checks.append(self.file_description.lower() == description)

        return any(checks) if checks else False


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class Win32WindowBackend:
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    MK_LBUTTON = 0x0001
    PW_CLIENTONLY = 0x00000001
    PW_RENDERFULLCONTENT = 0x00000002
    SRCCOPY = 0x00CC0020
    DIB_RGB_COLORS = 0
    BI_RGB = 0
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def __init__(self):
        if os.name != "nt":
            raise OSError("Window-targeted automation is only available on Windows.")
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.kernel32 = ctypes.windll.kernel32
        self.version = ctypes.windll.version

    def _window_title(self, hwnd):
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _query_process_image_name(self, pid):
        process_handle = self.kernel32.OpenProcess(
            self.PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            pid,
        )
        if not process_handle:
            return None

        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not self.kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(size),
            ):
                return None
            return buffer.value
        finally:
            self.kernel32.CloseHandle(process_handle)

    def _query_file_description(self, executable_path):
        if not executable_path:
            return None

        handle = wintypes.DWORD()
        size = self.version.GetFileVersionInfoSizeW(executable_path, ctypes.byref(handle))
        if size == 0:
            return None

        version_buffer = ctypes.create_string_buffer(size)
        if not self.version.GetFileVersionInfoW(executable_path, 0, size, version_buffer):
            return None

        value_ptr = ctypes.c_void_p()
        value_len = wintypes.UINT()
        translations = []
        if self.version.VerQueryValueW(
            version_buffer,
            "\\VarFileInfo\\Translation",
            ctypes.byref(value_ptr),
            ctypes.byref(value_len),
        ):
            translation_words = ctypes.cast(value_ptr, ctypes.POINTER(wintypes.WORD))
            translation_count = value_len.value // ctypes.sizeof(wintypes.WORD)
            for index in range(0, translation_count, 2):
                language = translation_words[index]
                code_page = translation_words[index + 1]
                translations.append(f"{language:04x}{code_page:04x}")

        translations.extend(["040904b0", "000004b0"])

        for translation in translations:
            query = f"\\StringFileInfo\\{translation}\\FileDescription"
            if self.version.VerQueryValueW(
                version_buffer,
                query,
                ctypes.byref(value_ptr),
                ctypes.byref(value_len),
            ) and value_len.value > 1:
                return ctypes.wstring_at(value_ptr, value_len.value - 1)

        return None

    def _describe_window(self, hwnd):
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        executable_path = self._query_process_image_name(pid.value)
        return {
            "hwnd": hwnd,
            "title": self._window_title(hwnd),
            "exe_name": Path(executable_path).name if executable_path else None,
            "file_description": self._query_file_description(executable_path),
        }

    def find_window(self, target):
        if isinstance(target, str):
            target = WindowTarget(title_substring=target)

        matches = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_windows(hwnd, _):
            if not self.user32.IsWindowVisible(hwnd):
                return True

            window_info = self._describe_window(hwnd)
            if target.matches(window_info):
                matches.append(hwnd)
            return True

        self.user32.EnumWindows(enum_windows, 0)
        return matches[0] if matches else None

    def is_window(self, hwnd):
        return bool(self.user32.IsWindow(hwnd))

    def get_client_size(self, hwnd):
        rect = RECT()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            raise WindowLookupError("Could not read the target window size.")
        return rect.right - rect.left, rect.bottom - rect.top

    def _client_origin(self, hwnd):
        point = POINT(0, 0)
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(point)):
            raise WindowLookupError("Could not translate the target window coordinates.")
        return point.x, point.y

    def capture_window(self, hwnd):
        width, height = self.get_client_size(hwnd)
        if width <= 0 or height <= 0:
            raise WindowLookupError("Target window has an invalid client area.")

        hwnd_dc = self.user32.GetDC(hwnd)
        mem_dc = self.gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = self.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        old_bitmap = self.gdi32.SelectObject(mem_dc, bitmap)

        try:
            flags = self.PW_CLIENTONLY | self.PW_RENDERFULLCONTENT
            success = self.user32.PrintWindow(hwnd, mem_dc, flags)
            if not success:
                left, top = self._client_origin(hwnd)
                right = left + width
                bottom = top + height
                return np.array(ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True))

            bitmap_info = BITMAPINFO()
            bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bitmap_info.bmiHeader.biWidth = width
            bitmap_info.bmiHeader.biHeight = -height
            bitmap_info.bmiHeader.biPlanes = 1
            bitmap_info.bmiHeader.biBitCount = 32
            bitmap_info.bmiHeader.biCompression = self.BI_RGB

            buffer = ctypes.create_string_buffer(width * height * 4)
            self.gdi32.GetDIBits(
                mem_dc,
                bitmap,
                0,
                height,
                buffer,
                ctypes.byref(bitmap_info),
                self.DIB_RGB_COLORS,
            )
            frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        finally:
            self.gdi32.SelectObject(mem_dc, old_bitmap)
            self.gdi32.DeleteObject(bitmap)
            self.gdi32.DeleteDC(mem_dc)
            self.user32.ReleaseDC(hwnd, hwnd_dc)

    def _vk_for_key(self, key):
        if len(key) != 1:
            raise ValueError(f"Unsupported key for window-targeted input: {key}")
        upper_key = key.upper()
        if "A" <= upper_key <= "Z":
            return ord(upper_key)
        if "0" <= key <= "9":
            return ord(key)
        raise ValueError(f"Unsupported key for window-targeted input: {key}")

    def _key_lparam(self, vk_code, is_key_up):
        scan_code = self.user32.MapVirtualKeyW(vk_code, 0)
        lparam = 1 | (scan_code << 16)
        if is_key_up:
            lparam |= 1 << 30
            lparam |= 1 << 31
        return lparam

    def _point_lparam(self, x, y):
        return (y << 16) | (x & 0xFFFF)

    def press_key(self, hwnd, key):
        self.key_down(hwnd, key)
        self.key_up(hwnd, key)

    def key_down(self, hwnd, key):
        vk_code = self._vk_for_key(key)
        self.user32.PostMessageW(hwnd, self.WM_KEYDOWN, vk_code, self._key_lparam(vk_code, False))

    def key_up(self, hwnd, key):
        vk_code = self._vk_for_key(key)
        self.user32.PostMessageW(hwnd, self.WM_KEYUP, vk_code, self._key_lparam(vk_code, True))

    def click(self, hwnd, x, y):
        self.mouse_down(hwnd, x, y)
        self.mouse_up(hwnd, x, y)

    def mouse_down(self, hwnd, x, y):
        point = self._point_lparam(x, y)
        self.user32.PostMessageW(hwnd, self.WM_MOUSEMOVE, 0, point)
        self.user32.PostMessageW(hwnd, self.WM_LBUTTONDOWN, self.MK_LBUTTON, point)

    def mouse_up(self, hwnd, x=None, y=None):
        if x is None or y is None:
            x = 0
            y = 0
        point = self._point_lparam(x, y)
        self.user32.PostMessageW(hwnd, self.WM_LBUTTONUP, 0, point)


class WindowAutomation:
    def __init__(self, target, backend=None, logger=print, refresh_interval=2.0, clock=time.monotonic):
        self.target = target if isinstance(target, WindowTarget) else WindowTarget(title_substring=target)
        self.backend = backend or Win32WindowBackend()
        self.logger = logger
        self.hwnd = None
        self.refresh_interval = refresh_interval
        self.clock = clock
        self.last_resolve_at = 0.0

    def _window_is_valid(self):
        if self.hwnd is None:
            return False
        checker = getattr(self.backend, "is_window", None)
        return True if checker is None else bool(checker(self.hwnd))

    def _resolve_window(self, force=False):
        now = self.clock()
        should_refresh = self.hwnd is None or not self._window_is_valid()
        if not should_refresh and self.refresh_interval is not None:
            should_refresh = (now - self.last_resolve_at) >= self.refresh_interval

        if force or should_refresh:
            self.hwnd = self.backend.find_window(self.target)
            if self.hwnd is None:
                raise WindowLookupError(
                    f"Could not find a visible window matching {self.target}."
                )
            self.last_resolve_at = now
        return self.hwnd

    def screenshot(self):
        return self.backend.capture_window(self._resolve_window())

    def size(self):
        return self.backend.get_client_size(self._resolve_window())

    def press(self, key):
        self.backend.press_key(self._resolve_window(), key)

    def keyDown(self, key):
        self.backend.key_down(self._resolve_window(), key)

    def keyUp(self, key):
        self.backend.key_up(self._resolve_window(), key)

    def click(self, x=None, y=None):
        if x is None or y is None:
            width, height = self.size()
            x = width // 2
            y = height // 2
        self.backend.click(self._resolve_window(), x, y)

    def mouseDown(self, x=None, y=None):
        if x is None or y is None:
            width, height = self.size()
            x = width // 2
            y = height // 2
        self.backend.mouse_down(self._resolve_window(), x, y)

    def mouseUp(self, x=None, y=None):
        self.backend.mouse_up(self._resolve_window(), x, y)


def capture_frame(screenshot_provider=None):
    capture = screenshot_provider() if screenshot_provider else pyautogui.screenshot()
    frame = capture if isinstance(capture, np.ndarray) else np.array(capture)

    if frame.ndim == 2:
        return frame
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2GRAY)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)


# Function to perform image matching
def find_image_on_screen(
    image_path,
    threshold=0.8,
    scale_factors=TEMPLATE_SCALE_FACTORS,
    screenshot_provider=None,
):
    screenshot = capture_frame(screenshot_provider=screenshot_provider)

    reference_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if reference_image is None:
        print(f"Error: Could not load image at {image_path}")
        return None

    screenshot_height, screenshot_width = screenshot.shape
    best_match = None

    for scale in scale_factors:
        interpolation_modes = [None] if scale == 1.0 else (
            [cv2.INTER_LINEAR, cv2.INTER_NEAREST] if scale > 1.0 else [cv2.INTER_AREA, cv2.INTER_LINEAR]
        )

        for interpolation in interpolation_modes:
            if scale == 1.0:
                scaled_reference = reference_image
            else:
                scaled_reference = cv2.resize(
                    reference_image,
                    None,
                    fx=scale,
                    fy=scale,
                    interpolation=interpolation,
                )

            ref_height, ref_width = scaled_reference.shape
            if ref_height < 1 or ref_width < 1:
                continue
            if ref_height > screenshot_height or ref_width > screenshot_width:
                continue

            result = cv2.matchTemplate(screenshot, scaled_reference, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if best_match is None or max_val > best_match[0]:
                best_match = (max_val, max_loc, ref_width, ref_height)

    if best_match and best_match[0] >= threshold:
        _, max_loc, ref_width, ref_height = best_match
        center_x = max_loc[0] + ref_width // 2
        center_y = max_loc[1] + ref_height // 2
        return center_x, center_y

    if best_match is None:
        print(
            f"Error: Reference image at {image_path} is larger than the current screenshot for all configured scales."
        )
    return None


@dataclass
class BotConfig:
    scan_interval: float = 0.5
    inventory_pause: float = 1.0
    catch_timeout: float = 45.0
    catch_dialog_timeout: float = 8.0
    idle_timeout: float = 25.0
    cast_hold_duration: float = 1.5
    summon_pause: float = 1.0
    shop_click_pause: float = 0.1
    movement_duration: float = 0.6
    jitter_fraction: float = 0.08
    pause_hotkey: str = "F8"
    stop_hotkey: str = "F9"
    pause_poll_interval: float = 0.25
    fallback_to_desktop_on_window_failure: bool = False
    handle_refresh_interval: float = 2.0
    debug_snapshot_after: float = 45.0
    debug_snapshot_cooldown: float = 60.0
    debug_snapshot_dir: str = str(BASE_DIR / "debug_snapshots")
    max_consecutive_capture_failures: int = 5
    max_consecutive_input_failures: int = 5
    cast_cooldown: float = 1.0
    restock_cooldown: float = 4.0
    recovery_cooldown: float = 5.0
    startup_self_check: bool = True


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_json_config():
    config_path = os.getenv("AWF_CONFIG_PATH")
    path = Path(config_path) if config_path else BASE_DIR / "awf_config.json"
    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def load_bot_config():
    file_config = _load_json_config()
    config = BotConfig()

    field_specs = {
        "scan_interval": ("AWF_SCAN_INTERVAL", float),
        "inventory_pause": ("AWF_INVENTORY_PAUSE", float),
        "catch_timeout": ("AWF_CATCH_TIMEOUT", float),
        "catch_dialog_timeout": ("AWF_CATCH_DIALOG_TIMEOUT", float),
        "idle_timeout": ("AWF_IDLE_TIMEOUT", float),
        "cast_hold_duration": ("AWF_CAST_HOLD_DURATION", float),
        "summon_pause": ("AWF_SUMMON_PAUSE", float),
        "shop_click_pause": ("AWF_SHOP_CLICK_PAUSE", float),
        "movement_duration": ("AWF_MOVEMENT_DURATION", float),
        "jitter_fraction": ("AWF_JITTER_FRACTION", float),
        "pause_hotkey": ("AWF_PAUSE_HOTKEY", str),
        "stop_hotkey": ("AWF_STOP_HOTKEY", str),
        "pause_poll_interval": ("AWF_PAUSE_POLL_INTERVAL", float),
        "handle_refresh_interval": ("AWF_HANDLE_REFRESH_INTERVAL", float),
        "debug_snapshot_after": ("AWF_DEBUG_SNAPSHOT_AFTER", float),
        "debug_snapshot_cooldown": ("AWF_DEBUG_SNAPSHOT_COOLDOWN", float),
        "debug_snapshot_dir": ("AWF_DEBUG_SNAPSHOT_DIR", str),
        "max_consecutive_capture_failures": ("AWF_MAX_CONSECUTIVE_CAPTURE_FAILURES", int),
        "max_consecutive_input_failures": ("AWF_MAX_CONSECUTIVE_INPUT_FAILURES", int),
        "cast_cooldown": ("AWF_CAST_COOLDOWN", float),
        "restock_cooldown": ("AWF_RESTOCK_COOLDOWN", float),
        "recovery_cooldown": ("AWF_RECOVERY_COOLDOWN", float),
    }

    for field_name, (_, caster) in field_specs.items():
        if field_name in file_config:
            setattr(config, field_name, caster(file_config[field_name]))

    for field_name, (env_name, caster) in field_specs.items():
        value = os.getenv(env_name)
        if value is not None:
            setattr(config, field_name, caster(value))

    config.fallback_to_desktop_on_window_failure = _env_bool(
        "AWF_FALLBACK_TO_DESKTOP",
        bool(file_config.get("fallback_to_desktop_on_window_failure", config.fallback_to_desktop_on_window_failure)),
    )
    config.startup_self_check = _env_bool(
        "AWF_STARTUP_SELF_CHECK",
        bool(file_config.get("startup_self_check", config.startup_self_check)),
    )
    return config


def enable_dpi_awareness():
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32
    for awareness in (-4, -3, -2):
        try:
            if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(awareness)):
                return True
        except Exception:
            pass

    try:
        return bool(user32.SetProcessDPIAware())
    except Exception:
        return False


class NullControlMonitor:
    def consume_pause_toggle(self):
        return False

    def consume_stop_request(self):
        return False


class Win32ControlMonitor:
    def __init__(self, pause_hotkey="F8", stop_hotkey="F9"):
        if os.name != "nt":
            raise OSError("Global hotkeys are only available on Windows.")
        self.user32 = ctypes.windll.user32
        self.pause_vk = self._vk_code(pause_hotkey)
        self.stop_vk = self._vk_code(stop_hotkey)
        self.previous_state = {self.pause_vk: False, self.stop_vk: False}

    def _vk_code(self, hotkey):
        hotkey = hotkey.upper().strip()
        if len(hotkey) == 1 and hotkey.isalnum():
            return ord(hotkey)
        if hotkey.startswith("F") and hotkey[1:].isdigit():
            index = int(hotkey[1:])
            if 1 <= index <= 24:
                return 0x6F + index
        raise ValueError(f"Unsupported hotkey: {hotkey}")

    def _consume(self, vk_code):
        is_down = bool(self.user32.GetAsyncKeyState(vk_code) & 0x8000)
        was_down = self.previous_state.get(vk_code, False)
        self.previous_state[vk_code] = is_down
        return is_down and not was_down

    def consume_pause_toggle(self):
        return self._consume(self.pause_vk)

    def consume_stop_request(self):
        return self._consume(self.stop_vk)


class Diagnostics:
    def __init__(self, snapshot_dir, logger=print):
        self.snapshot_dir = Path(snapshot_dir)
        self.logger = logger

    def save_snapshot(self, reason, frame=None):
        if frame is None:
            return None

        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_path = self.snapshot_dir / f"{timestamp}-{reason}.png"
        image = frame if isinstance(frame, np.ndarray) else np.array(frame)

        if image.ndim == 2:
            cv2.imwrite(str(output_path), image)
        elif image.shape[2] == 4:
            cv2.imwrite(str(output_path), cv2.cvtColor(image, cv2.COLOR_RGBA2BGRA))
        else:
            cv2.imwrite(str(output_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        self.logger(f"Saved debug snapshot: {output_path}")
        return str(output_path)


class FishingBot:
    def __init__(
        self,
        automation=pyautogui,
        finder=None,
        sleeper=time.sleep,
        clock=time.monotonic,
        logger=print,
        config=None,
        control_monitor=None,
        diagnostics=None,
        rng=None,
    ):
        self.automation = automation
        self.sleep = sleeper
        self.clock = clock
        self.logger = logger
        self.config = config or BotConfig()
        self.control_monitor = control_monitor or NullControlMonitor()
        self.diagnostics = diagnostics
        self.random = rng or random.Random(0)
        self.last_progress_at = self.clock()
        self.last_snapshot_at = float("-inf")
        self.last_action_at = {}
        self.mouse_held = False
        self.paused = False
        self.stop_requested = False
        self.consecutive_capture_failures = 0
        self.consecutive_input_failures = 0
        self.screenshot_provider = getattr(self.automation, "screenshot", None)
        if finder is None:
            self.finder = lambda image_path, threshold=0.8: find_image_on_screen(
                image_path,
                threshold=threshold,
                screenshot_provider=self.screenshot_provider,
            )
        else:
            self.finder = finder

    def log(self, message):
        self.logger(message)

    def _sleep_with_jitter(self, duration):
        if duration <= 0:
            return
        jitter = duration * self.config.jitter_fraction
        actual_duration = duration if jitter == 0 else max(
            0.0,
            duration + self.random.uniform(-jitter, jitter),
        )
        self.sleep(actual_duration)

    def _action_ready(self, action_name, cooldown):
        if cooldown <= 0:
            return True
        return (self.clock() - self.last_action_at.get(action_name, float("-inf"))) >= cooldown

    def _mark_action(self, action_name):
        self.last_action_at[action_name] = self.clock()

    def _record_input_failure(self, action_name, exc):
        self.consecutive_input_failures += 1
        self.log(f"Input failure during {action_name}: {exc}")
        if self.consecutive_input_failures >= self.config.max_consecutive_input_failures:
            self.stop_requested = True
            self.log("Stopping bot after repeated input failures.")

    def _run_input_action(self, action_name, callback):
        try:
            callback()
            self.consecutive_input_failures = 0
            return True
        except Exception as exc:
            self._record_input_failure(action_name, exc)
            return False

    def capture_debug_frame(self):
        if self.screenshot_provider is None:
            return None
        try:
            frame = self.screenshot_provider()
        except Exception as exc:
            self.log(f"Could not capture debug frame: {exc}")
            return None
        return frame if isinstance(frame, np.ndarray) else np.array(frame)

    def _maybe_save_snapshot(self, reason, force=False):
        if self.diagnostics is None:
            return None

        now = self.clock()
        if not force and (now - self.last_snapshot_at) < self.config.debug_snapshot_cooldown:
            return None

        self.last_snapshot_at = now
        return self.diagnostics.save_snapshot(reason, frame=self.capture_debug_frame())

    def handle_control_events(self):
        if self.stop_requested:
            return "stop_requested"

        if self.control_monitor.consume_stop_request():
            self.stop_requested = True
            self.release_left_button()
            self.log("Stop hotkey received.")
            return "stop_requested"

        if self.control_monitor.consume_pause_toggle():
            self.paused = not self.paused
            self.release_left_button()
            self.log("Paused." if self.paused else "Resumed.")
            return "paused" if self.paused else "resumed"

        return "running"

    def startup_self_check(self):
        image_paths = [
            start_image,
            catch_image,
            stop_image,
            reel1_image,
            reel2_image,
            wormx_image,
            worm0_image,
            cricketx_image,
            cricket0_image,
            leechx_image,
            leech0_image,
            minnowx_image,
            minnow0_image,
            squidx_image,
            squid0_image,
            nautilusx_image,
            nautilus0_image,
            shopWorm_image,
            shopCricket_image,
            shopLeech_image,
            shopMinnow_image,
            shopSquid_image,
            shopNautilus_image,
            sell_image,
        ]
        missing = [path for path in image_paths if not Path(path).is_file()]
        if missing:
            raise FileNotFoundError(f"Missing screenshot assets: {missing}")

        width, height = self.automation.size()
        if width <= 0 or height <= 0:
            raise WindowLookupError("Could not determine the target window size.")

        frame = self.capture_debug_frame()
        if frame is None or getattr(frame, "size", 0) == 0:
            raise WindowLookupError("Could not capture the target window during startup self-check.")

        return {
            "window_size": (width, height),
            "frame_shape": tuple(frame.shape),
        }

    def press_key(self, key):
        if hasattr(self.automation, "press"):
            return self._run_input_action(f"press {key}", lambda: self.automation.press(key))
        return self._run_input_action(
            f"press {key}",
            lambda: (self.automation.keyDown(key), self.automation.keyUp(key)),
        )

    def click(self, x, y):
        if hasattr(self.automation, "click"):
            return self._run_input_action(f"click {x},{y}", lambda: self.automation.click(x, y))
        return self._run_input_action(
            f"click {x},{y}",
            lambda: (self.automation.mouseDown(x, y), self.automation.mouseUp(x, y)),
        )

    def hold_key_for(self, key, duration):
        if not self.press_key_down(key):
            return False
        self._sleep_with_jitter(duration)
        return self.press_key_up(key)

    def press_key_down(self, key):
        if hasattr(self.automation, "keyDown"):
            return self._run_input_action(f"key down {key}", lambda: self.automation.keyDown(key))
        return self.press_key(key)

    def press_key_up(self, key):
        if hasattr(self.automation, "keyUp"):
            return self._run_input_action(f"key up {key}", lambda: self.automation.keyUp(key))
        return True

    def screen_center(self):
        screen_width, screen_height = self.automation.size()
        return screen_width // 2, screen_height // 2

    def is_visible(self, image_path, threshold=0.8):
        try:
            visible = self.finder(image_path, threshold=threshold) is not None
            self.consecutive_capture_failures = 0
            return visible
        except Exception as exc:
            self.consecutive_capture_failures += 1
            self.log(f"Capture failure while checking {image_path}: {exc}")
            if self.consecutive_capture_failures >= self.config.max_consecutive_capture_failures:
                self._maybe_save_snapshot("capture_failure", force=True)
                self.stop_requested = True
            return False

    def is_any_visible(self, image_paths, threshold=0.8):
        return any(self.is_visible(image_path, threshold=threshold) for image_path in image_paths)

    def wait_for_any_visible(self, image_paths, timeout, threshold=0.8):
        deadline = self.clock() + timeout
        while self.clock() <= deadline and not self.stop_requested:
            for image_path in image_paths:
                if self.is_visible(image_path, threshold=threshold):
                    return image_path
            self._sleep_with_jitter(self.config.scan_interval)
        return None

    def hold_left_button(self):
        if self.mouse_held:
            return True
        center_x, center_y = self.screen_center()
        if not self._run_input_action(
            "mouse down",
            lambda: self.automation.mouseDown(center_x, center_y),
        ):
            return False
        self.mouse_held = True
        self.log(f"Holding left click at center: ({center_x}, {center_y})")
        return True

    def release_left_button(self):
        if not self.mouse_held:
            return True
        released = self._run_input_action("mouse up", lambda: self.automation.mouseUp())
        if released:
            self.mouse_held = False
            self.log("Released left click.")
        return released

    def open_inventory(self):
        if not self.press_key("b"):
            return False
        self.log("Pressed b.")
        self._sleep_with_jitter(self.config.inventory_pause)
        return True

    def close_inventory(self):
        if not self.press_key("b"):
            return False
        self.log("Pressed b.")
        return True

    def select_bait_from_inventory(self):
        if not self.open_inventory():
            return False
        for absence_image, presence_image in BAIT_IMAGE_PRIORITY:
            if self.is_visible(absence_image, threshold=0.99):
                self.log(f"Bait '{absence_image}' is absent. Moving to next type.")
                continue

            bait_location = self.finder(presence_image, threshold=0.95)
            if bait_location:
                center_x, center_y = bait_location
                self.log(f"Clicking on bait at ({center_x}, {center_y}).")
                if not self.click(center_x, center_y):
                    return False
                self.close_inventory()
                self.last_progress_at = self.clock()
                return True

        self.close_inventory()
        self.log("No bait available in inventory.")
        return False

    def restock_bait(self):
        if not self._action_ready("restock_bait", self.config.restock_cooldown):
            return False

        self._mark_action("restock_bait")
        self.log("Restocking bait from portable bait station.")
        if not self.hold_key_for("s", self.config.movement_duration):
            return False
        if not self.press_key("5"):
            return False
        self.log("Pressed 5.")
        self._sleep_with_jitter(self.config.summon_pause)

        center_x, center_y = self.screen_center()
        if not self.click(center_x, center_y):
            return False
        self.log(f"Clicked summon center: ({center_x}, {center_y}).")
        if not self.press_key("e"):
            return False
        self._sleep_with_jitter(self.config.summon_pause)

        clicked_items = 0
        for image_path in SHOP_IMAGES:
            shop_location = self.finder(image_path, threshold=0.8)
            if not shop_location:
                self.log(f"Image not found on screen: {image_path}.")
                continue

            item_x, item_y = shop_location
            if not self.click(item_x, item_y):
                return False
            clicked_items += 1
            self.log(f"Clicked on shop item at ({item_x}, {item_y}) for image: {image_path}.")
            self._sleep_with_jitter(self.config.shop_click_pause)

        if clicked_items == 0:
            self.log("Could not verify the bait shop UI.")
            self._maybe_save_snapshot("restock_unverified", force=True)
            return False

        if not self.press_key("e"):
            return False
        self._sleep_with_jitter(self.config.inventory_pause)
        if not self.press_key("1"):
            return False
        if not self.hold_key_for("w", self.config.movement_duration):
            return False
        self.last_progress_at = self.clock()
        return True

    def ensure_bait(self):
        if self.select_bait_from_inventory():
            return True

        if not self.restock_bait():
            return False
        return self.select_bait_from_inventory()

    def dismiss_catch_dialog(self):
        deadline = self.clock() + self.config.catch_dialog_timeout
        while self.clock() <= deadline and self.is_visible(catch_image) and not self.stop_requested:
            if not self.press_key("e"):
                return False
            self.log("Pressing E.")
            self._sleep_with_jitter(self.config.scan_interval)
        self.last_progress_at = self.clock()
        return not self.is_visible(catch_image)

    def cast_line(self):
        if not self._action_ready("cast_line", self.config.cast_cooldown):
            return False

        self._mark_action("cast_line")
        center_x, center_y = self.screen_center()
        if not self._run_input_action(
            "cast mouse down",
            lambda: self.automation.mouseDown(center_x, center_y),
        ):
            return False
        self.log(f"Holding left click for {self.config.cast_hold_duration} seconds at center: ({center_x}, {center_y})")
        self._sleep_with_jitter(self.config.cast_hold_duration)
        if not self._run_input_action("cast mouse up", lambda: self.automation.mouseUp()):
            return False
        self.log("Released left click after cast.")
        self.last_progress_at = self.clock()
        return True

    def handle_hooked_fish(self):
        if not self.hold_left_button():
            return False
        visible_image = self.wait_for_any_visible([catch_image], timeout=self.config.catch_timeout)
        self.release_left_button()

        if visible_image != catch_image:
            self.log("Catch prompt did not appear before timeout.")
            return False

        if not self.dismiss_catch_dialog():
            self.log("Catch prompt remained visible after dismissal timeout.")
            return False

        if self.is_visible(stop_image):
            if not self.ensure_bait():
                self.log("Unable to acquire bait after catch.")
                return False
        if not self.cast_line():
            return False
        self.last_progress_at = self.clock()
        return True

    def recover_from_idle(self):
        if not self._action_ready("recover_from_idle", self.config.recovery_cooldown):
            return False

        self._mark_action("recover_from_idle")
        self.log("No fishing prompts detected for too long. Recovering AFK loop.")
        self.release_left_button()
        if self.is_visible(stop_image):
            if not self.ensure_bait():
                self.log("Recovery paused because no bait is available.")
                return False
        if not self.press_key("1"):
            return False
        if not self.cast_line():
            return False
        self.last_progress_at = self.clock()
        return True

    def run_step(self):
        control_state = self.handle_control_events()
        if control_state == "stop_requested":
            return "stop_requested"
        if self.paused:
            return "paused"

        if self.is_visible(catch_image):
            self.release_left_button()
            if not self.dismiss_catch_dialog():
                return "catch_dialog_stuck"
            if self.is_visible(stop_image):
                if not self.ensure_bait():
                    return "bait_unavailable"
            self.cast_line()
            return "handled_catch"

        if self.is_any_visible(REEL_TRIGGER_IMAGES):
            handled = self.handle_hooked_fish()
            if handled:
                return "hooked_fish"
            self.recover_from_idle()
            return "hook_timeout_recovered"

        if self.is_visible(stop_image):
            if not self.ensure_bait():
                return "bait_unavailable"
            self.cast_line()
            return "restocked_bait"

        idle_for = self.clock() - self.last_progress_at
        if idle_for >= self.config.debug_snapshot_after:
            self._maybe_save_snapshot("idle_no_match")

        if idle_for >= self.config.idle_timeout:
            recovered = self.recover_from_idle()
            return "bait_unavailable" if recovered is False else "recovered_idle"

        return "idle"

    def run_forever(self):
        while not self.stop_requested:
            result = self.run_step()
            if result == "stop_requested":
                break
            sleep_duration = self.config.pause_poll_interval if self.paused else self.config.scan_interval
            self._sleep_with_jitter(sleep_duration)


def create_control_monitor(config):
    try:
        return Win32ControlMonitor(
            pause_hotkey=config.pause_hotkey,
            stop_hotkey=config.stop_hotkey,
        )
    except Exception:
        return NullControlMonitor()


def baitInventory():
    return create_default_bot().ensure_bait()


def create_default_automation(config=None, logger=print):
    config = config or load_bot_config()
    window_target = WindowTarget(
        title_substring=os.getenv("AWF_WINDOW_TITLE", "WEBFISHING").strip() or None,
        executable_name=os.getenv("AWF_WINDOW_EXE", "webfishing.exe").strip() or None,
        file_description=os.getenv("AWF_WINDOW_DESCRIPTION", "Fish! (On the WEB!)").strip() or None,
    )
    if any(
        [
            window_target.title_substring,
            window_target.executable_name,
            window_target.file_description,
        ]
    ):
        try:
            automation = WindowAutomation(
                window_target,
                logger=logger,
                refresh_interval=config.handle_refresh_interval,
            )
            automation.size()
            logger(f"Using window-targeted automation for {window_target}.")
            return automation
        except Exception as exc:
            if not config.fallback_to_desktop_on_window_failure:
                raise
            logger(
                f"Window-targeted automation unavailable for {window_target}: {exc}. Falling back to desktop automation."
            )
    return pyautogui


def create_default_bot(logger=print):
    enable_dpi_awareness()
    config = load_bot_config()
    automation = create_default_automation(config=config, logger=logger)
    diagnostics = Diagnostics(config.debug_snapshot_dir, logger=logger)
    bot = FishingBot(
        automation=automation,
        logger=logger,
        config=config,
        control_monitor=create_control_monitor(config),
        diagnostics=diagnostics,
    )
    if config.startup_self_check:
        bot.startup_self_check()
    return bot


def main():
    create_default_bot().run_forever()


if __name__ == "__main__":
    main()
