"""Rocket League Trade-In Automation Bot.

Automates the item trade-in process using screen capture and template matching.
Starts from the Rocket League main menu, navigates itself, opens reward drops,
then trades in items across every category.

Press Escape at any time to abort.

Usage:
    python trade_in_bot.py                     # open drops, then trade in
    python trade_in_bot.py --mode drops        # only open reward drops
    python trade_in_bot.py --mode trade        # only run the trade-in loop
    python trade_in_bot.py --mode where        # report the current screen
    python trade_in_bot.py --discover-drops    # capture the open-drop UI flow
"""

import argparse
import ctypes
import cv2
import numpy as np
import pyautogui
import os
import sys
import time
from datetime import datetime
from pynput import keyboard

# --- Configuration ---
TEMPLATES_DIR = "templates"
DEBUG_DIR = "debug"
CONFIDENCE_THRESHOLD = 0.7  # Template matching confidence (0-1)
# A category card you do not have five items for is drawn dimmed. Measured on
# ui-images/main screen.png: available cards average a brightness (HSV value)
# of 98-110, locked ones 52-57.
CARD_ENABLED_BRIGHTNESS = 75
WAIT_TIMEOUT = 10  # Seconds to wait before giving up on finding an image
POLL_INTERVAL = 0.12  # Seconds between polls while waiting for an image
CLICK_DELAY = 0.15  # Seconds between regular actions
LONG_DELAY = 0.5  # Seconds for reward animation, screen transitions
CATEGORY_REFRESH_DELAY = 0.6  # Let the trade-in screen finish counting categories
SHORT_DELAY = 0.12  # Seconds for popup dismissals

# PyAutoGUI sleeps 0.1s after every call by default. Every wait in this bot is
# driven by wait_for_image instead, so that blanket pause is pure overhead.
pyautogui.PAUSE = 0
# With no pause at all, mouse-down and mouse-up land in the same frame and
# Rocket League ignores the click, so the press is held explicitly instead.
MOUSE_SETTLE = 0.05  # Seconds between moving onto a control and pressing
MOUSE_HOLD = 0.08  # Seconds to hold the button down
MOUSE_RELEASE = 0.08  # Seconds to stay on the control after releasing
DROP_SETTLE = 0.35  # Seconds to let the drop screens finish animating

# Item grid region on the trade-in screen (x, y, width, height) at 1440p
# This is the area where item icons appear below the 5 trade-in slots
ITEM_GRID_X = 280
ITEM_GRID_Y = 650
ITEM_GRID_W = 1400
ITEM_GRID_H = 670

# Grid layout: items are arranged in rows and columns
ITEM_COLS = 7  # Items per row
ITEM_ROWS = 3  # Visible rows
ITEM_CELL_W = 195  # Approximate width of each item cell
ITEM_CELL_H = 220  # Approximate height of each item cell
ITEM_START_X = 385  # X of first item center (relative to screen)
ITEM_START_Y = 765  # Y of first item center (relative to screen)

# --- Manage Inventory screen (1440p) ---
# Item tiles are laid out 7 per row; 4 rows are visible without scrolling.
# Measured from ui-images/inventory_all_items.png: tile gaps at x = 50, 230,
# 410, ... (180px pitch) and y = 300, 500, 700, ... (200px pitch).
INV_COLS = 7
INV_ROWS = 4
INV_CELL_W = 180
INV_CELL_H = 200
INV_START_X = 140  # X of first tile center
INV_START_Y = 400  # Y of first tile center
INV_GRID_X = 50
INV_GRID_Y = 300
INV_GRID_W = 1260
INV_GRID_H = 800
# The tab strip above the panel. Tab positions shift as the active tab widens,
# so the tab icon is located by template match inside this band.
INV_TAB_SEARCH_REGION = (0, 60, 1400, 110)

# Where each template can appear, as (x, y, w, h) at 1440p. Matching a 230x60
# template against the full 2560x1440 screen costs ~200 ms; against a 900x180
# region it costs ~4 ms, and the whole bot is template matching in a loop.
# Regions are deliberately generous. `--full-scan` ignores them.
TEMPLATE_REGIONS = {
    # Trade-in category screen
    # The title sits 137 px higher when the Black Market Item Converter card is
    # shown underneath it, so the box has to cover both heights.
    "trade_in_title.png": (1780, 380, 500, 330),
    "card_core_special.png": (140, 280, 380, 270),
    "card_core_deluxe.png": (430, 280, 380, 270),
    "card_core_import.png": (720, 285, 390, 270),
    "card_core_exotic.png": (1010, 265, 400, 290),
    "card_core_black_market.png": (1300, 275, 400, 280),
    "card_tournament_special.png": (130, 640, 390, 290),
    "card_tournament_deluxe.png": (430, 635, 390, 290),
    "card_tournament_import.png": (720, 630, 390, 300),
    "card_tournament_exotic.png": (1010, 625, 390, 300),
    "card_tournament_black_market.png": (1300, 640, 390, 290),
    "card_blueprints_deluxe.png": (430, 1025, 390, 270),
    "card_blueprints_import.png": (720, 1015, 390, 290),
    "card_blueprints_exotic.png": (1010, 1015, 390, 290),
    "card_blueprints_black_market.png": (1300, 1015, 390, 280),
    # Trade-in item screen and its popups
    "show_filters.png": (1300, 530, 520, 160),
    "accept_button.png": (800, 410, 520, 170),
    "confirm_yes.png": (900, 740, 620, 190),
    # The reveal button row shifts down when an extra banner is shown (for
    # example "This item will also be available in Fortnite"), so the box has
    # to cover both heights.
    "reward_ok.png": (950, 940, 800, 320),
    "not_eligible_popup.png": (900, 510, 820, 190),
    "not_eligible_ok.png": (1050, 730, 520, 180),
    "choose_quantity_popup.png": (850, 510, 920, 190),
    "quantity_ok.png": (950, 730, 520, 180),
    "quantity_plus.png": (1200, 650, 420, 170),
    "trade_in_empty_slots.png": (260, 130, 1450, 400),
    # Menus
    "menu_garage.png": (0, 730, 520, 150),
    "garage_trade_in.png": (0, 880, 620, 140),
    "garage_manage_inv.png": (0, 950, 620, 150),
    "inv_header_all.png": (0, 140, 720, 150),
    "inv_header_reward.png": (0, 140, 720, 150),
    "inv_tab_reward.png": INV_TAB_SEARCH_REGION,
    "back_button.png": (0, 1130, 520, 310),
    "inv_back.png": (0, 1130, 520, 310),
    # Drops
    "drop_open_button.png": (0, 1130, 620, 190),
    "drop_reveal_ok.png": (950, 940, 1000, 320),
    "drop_reveal_ok_hl.png": (950, 940, 1000, 320),
    "drop_reveal_label.png": (1050, 150, 500, 100),
}

# Category cards to try, in order (display name)
CATEGORY_CARDS = [
    ("card_core_special.png", "Core Items - Special"),
    ("card_core_deluxe.png", "Core Items - Deluxe"),
    ("card_core_import.png", "Core Items - Import"),
    ("card_core_exotic.png", "Core Items - Exotic"),
    ("card_core_black_market.png", "Core Items - Black Market"),
    ("card_tournament_special.png", "Tournament Items - Special"),
    ("card_tournament_deluxe.png", "Tournament Items - Deluxe"),
    ("card_tournament_import.png", "Tournament Items - Import"),
    ("card_tournament_exotic.png", "Tournament Items - Exotic"),
    ("card_tournament_black_market.png", "Tournament Items - Black Market"),
    ("card_blueprints_deluxe.png", "Blueprints - Deluxe"),
    ("card_blueprints_import.png", "Blueprints - Import"),
    ("card_blueprints_exotic.png", "Blueprints - Exotic"),
    ("card_blueprints_black_market.png", "Blueprints - Black Market"),
]

GAME_WINDOW_PREFIX = "Rocket League"
# Where to leave the cursor after a click. Rocket League draws a hover
# highlight on whatever the mouse rests on, which changes the pixels enough
# that the un-hovered template stops matching, so the cursor is parked on an
# inert strip at the right edge of the screen after every click.
PARK_POS = (2550, 720)
RUNS_DIR = os.path.join(DEBUG_DIR, "runs")

# --- Global State ---
abort_flag = False
trade_summary = {}  # {"Category Name": trade_count}
DRY_RUN = False  # When True, skip every irreversible click (ACCEPT / YES / OPEN)
AUTO_FOCUS = True  # Re-focus the game whenever another window steals the front
FULL_SCAN = False  # When True, ignore TEMPLATE_REGIONS and search the whole screen
_game_hwnd = None
TRACE = False  # When True, record an annotated frame at each step
TRACE_DIR = os.path.join(DEBUG_DIR, "trace")
_trace_counter = 0
_log_handle = None
_log_stdout = None
_log_stderr = None


def _force_foreground(hwnd):
    """Raise a window to the foreground, working around Windows focus rules.

    A background process is normally not allowed to steal the foreground. The
    standard workaround is to attach our input queue to both the current
    foreground thread and the target thread for the duration of the call.

    Args:
        hwnd: Window handle to raise.

    Returns:
        True if the window is the foreground window afterwards.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if user32.GetForegroundWindow() == hwnd:
        return True

    SW_RESTORE = 9
    current_tid = kernel32.GetCurrentThreadId()
    foreground_tid = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)

    attached = []
    for tid in {foreground_tid, target_tid}:
        if tid and tid != current_tid and user32.AttachThreadInput(current_tid, tid, True):
            attached.append(tid)
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        for tid in attached:
            user32.AttachThreadInput(current_tid, tid, False)

    return user32.GetForegroundWindow() == hwnd


def find_game_window():
    """Return the Rocket League window handle, or None if the game is not running."""
    global _game_hwnd
    if _game_hwnd and ctypes.windll.user32.IsWindow(_game_hwnd):
        return _game_hwnd

    user32 = ctypes.windll.user32
    matches = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def collect(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value.startswith(GAME_WINDOW_PREFIX) and user32.IsWindowVisible(hwnd):
                matches.append(hwnd)
        return True

    user32.EnumWindows(collect, None)
    _game_hwnd = matches[0] if matches else None
    return _game_hwnd


def game_is_foreground():
    """True if the Rocket League window is currently the foreground window."""
    hwnd = find_game_window()
    return bool(hwnd) and ctypes.windll.user32.GetForegroundWindow() == hwnd


class _TeeStream:
    """Write to the console and to the run log, timestamping each log line."""

    def __init__(self, console, handle, start):
        self.console = console
        self.handle = handle
        self.start = start
        self._at_line_start = True

    def write(self, text):
        self.console.write(text)
        for part in text.splitlines(keepends=True):
            if self._at_line_start and part.strip():
                stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.handle.write(f"{stamp} +{time.time() - self.start:7.2f}s  ")
            self.handle.write(part)
            self._at_line_start = part.endswith(chr(10))
        self.handle.flush()
        return len(text)

    def flush(self):
        self.console.flush()
        self.handle.flush()

    def isatty(self):
        return self.console.isatty()


def start_run_log():
    """Start mirroring stdout and stderr into a timestamped log file.

    Every run gets its own file under debug/runs/, so a failed run can always be
    replayed afterwards next to the debug screenshots it produced.

    Returns:
        Path to the log file.
    """
    global _log_handle, _log_stdout, _log_stderr

    os.makedirs(RUNS_DIR, exist_ok=True)
    path = os.path.join(RUNS_DIR, datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")
    _log_handle = open(path, "w", encoding="utf-8")
    _log_handle.write(f"# run started {datetime.now().isoformat(timespec='seconds')}" + chr(10))
    _log_handle.write("# argv: " + " ".join(sys.argv) + chr(10))

    start = time.time()
    _log_stdout, _log_stderr = sys.stdout, sys.stderr
    sys.stdout = _TeeStream(_log_stdout, _log_handle, start)
    sys.stderr = _TeeStream(_log_stderr, _log_handle, start)
    return path


def stop_run_log():
    """Restore stdout/stderr and close the run log."""
    global _log_handle, _log_stdout, _log_stderr

    if _log_stdout is not None:
        sys.stdout = _log_stdout
        sys.stderr = _log_stderr
        _log_stdout = _log_stderr = None
    if _log_handle is not None:
        _log_handle.close()
        _log_handle = None


def park_mouse():
    """Move the cursor off any interactive element so hover styling clears."""
    pyautogui.moveTo(*PARK_POS)


def click_at(x, y, what="", park=True):
    """Click a screen position and record it in the run log.

    Args:
        x: Screen x coordinate.
        y: Screen y coordinate.
        what: Short description of what is being clicked.
        park: Move the cursor away afterwards so the button is not left
            hover-highlighted, which would break the next template match.
    """
    check_abort()
    print(f"      . click ({x}, {y}) {what}".rstrip())
    pyautogui.moveTo(x, y)
    time.sleep(MOUSE_SETTLE)
    pyautogui.mouseDown()
    time.sleep(MOUSE_HOLD)
    pyautogui.mouseUp()
    # The game processes input per frame; moving away in the same frame as the
    # release makes it treat the click as cancelled.
    time.sleep(MOUSE_RELEASE)
    if park:
        park_mouse()


def focus_game(timeout=5.0):
    """Bring the Rocket League window to the foreground.

    The bot both clicks the real mouse and reads the real screen, so anything
    covering the game breaks it in two ways at once: clicks land on the wrong
    window, and template matching sees the wrong pixels.

    Args:
        timeout: Seconds to keep retrying activation.

    Returns:
        True if the game window is in front, False if it could not be found or
        raised.
    """
    hwnd = find_game_window()
    if not hwnd:
        print(f"[focus] No window titled '{GAME_WINDOW_PREFIX}*' found — is the game running?")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _force_foreground(hwnd):
            return True
        time.sleep(0.2)

    print("[focus] Could not bring Rocket League to the front — "
          "leave the game window in focus while the bot runs")
    return False


def maybe_focus():
    """Re-focus the game if another window has taken the foreground.

    Screen capture reads whatever is on top, so a terminal or overlay in front
    of the game makes every template match fail. Checking is cheap; activating
    only happens when the game actually lost focus.

    Returns:
        True if the game is (now) the active window.
    """
    if not AUTO_FOCUS:
        return True
    if game_is_foreground():
        return True
    return focus_game(timeout=3.0)


def trace(label, screenshot=None, note=""):
    """Record a labelled frame when tracing is on.

    Args:
        label: Short step name; becomes part of the filename.
        screenshot: Optional already-captured BGR frame to reuse.
        note: Extra text for the trace log.

    Returns:
        Path to the written frame, or None when tracing is off.
    """
    global _trace_counter
    if not TRACE:
        return None

    os.makedirs(TRACE_DIR, exist_ok=True)
    _trace_counter += 1
    safe = label.replace(" ", "_").replace("/", "_")
    path = os.path.join(TRACE_DIR, f"{_trace_counter:03d}_{safe}.png")

    frame = take_screenshot() if screenshot is None else screenshot
    cv2.imwrite(path, frame)

    line = f"{_trace_counter:03d}\t{label}\t{note}"
    with open(os.path.join(TRACE_DIR, "trace.log"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(f"    [trace] {line}")
    return path


def reset_trace():
    """Clear any frames from a previous traced run."""
    global _trace_counter
    _trace_counter = 0
    if os.path.isdir(TRACE_DIR):
        for name in os.listdir(TRACE_DIR):
            if name.endswith(".png") or name == "trace.log":
                os.remove(os.path.join(TRACE_DIR, name))


def on_key_press(key):
    """Keyboard listener callback. Sets abort flag on Escape."""
    global abort_flag
    if key == keyboard.Key.esc:
        abort_flag = True
        print("\n[!] Escape pressed — aborting after current action...")


def check_abort():
    """Check if abort was requested. Raises SystemExit if so."""
    if abort_flag:
        print("\nAborted by user.")
        sys.exit(0)


def ensure_debug_dir():
    """Create debug directory if it doesn't exist."""
    os.makedirs(DEBUG_DIR, exist_ok=True)


def save_debug_screenshot(context):
    """Save a debug screenshot with timestamp and context description.

    Args:
        context: Description of what was happening (e.g., "looking_for_accept_button")

    Returns:
        Path to the saved screenshot.
    """
    ensure_debug_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_context = context.replace(" ", "_").replace("/", "_").replace(".png", "")
    filename = f"{timestamp}_{safe_context}.png"
    filepath = os.path.join(DEBUG_DIR, filename)
    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)
    return filepath


def print_summary():
    """Print the trade-in summary."""
    print("\n" + "=" * 40)
    if not trade_summary:
        print("No trades completed.")
    else:
        print("Trade-in Summary:")
        total_trades = 0
        for category, count in trade_summary.items():
            print(f"  {category}: {count} trade{'s' if count != 1 else ''}")
            total_trades += count
        total_items = total_trades * 5
        print(f"  Total: {total_trades} trades ({total_items} items consumed)")
    print("=" * 40)


# --- Template cache ---
_template_cache = {}


def load_template(template_name):
    """Load a template image from the templates directory. Caches results.

    Args:
        template_name: Filename of the template in TEMPLATES_DIR.

    Returns:
        The template image as a numpy array (BGR).

    Raises:
        FileNotFoundError: If the template file doesn't exist.
    """
    if template_name in _template_cache:
        return _template_cache[template_name]

    path = os.path.join(TEMPLATES_DIR, template_name)
    template = cv2.imread(path)
    if template is None:
        raise FileNotFoundError(f"Template not found: {path}")

    _template_cache[template_name] = template
    return template


_mss = None
_mss_failed = False


def take_screenshot():
    """Capture the screen and return as a BGR numpy array (for OpenCV).

    Uses mss when available (~10 ms) and falls back to PyAutoGUI (~45 ms).
    """
    global _mss, _mss_failed

    if not _mss_failed:
        try:
            if _mss is None:
                import mss as mss_module
                _mss = mss_module.mss()
            raw = _mss.grab(_mss.monitors[0])
            # mss returns BGRA; drop the alpha channel.
            return np.asarray(raw, dtype=np.uint8)[:, :, :3]
        except Exception:
            _mss, _mss_failed = None, True

    frame = np.array(pyautogui.screenshot())
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def find_on_screen(template_name, screenshot=None, confidence=None, region="auto"):
    """Find a template image on screen.

    Args:
        template_name: Filename of the template in TEMPLATES_DIR.
        screenshot: Optional pre-captured screenshot. If None, captures a new one.
        confidence: Minimum match confidence (0-1). Defaults to CONFIDENCE_THRESHOLD.
        region: (x, y, w, h) to restrict the search to. Defaults to "auto",
            which uses TEMPLATE_REGIONS; pass None to search the full screen.
            Returned coordinates are always absolute screen coordinates.

    Returns:
        (x, y) center coordinates of the best match if confidence exceeds threshold,
        or None if not found.
    """
    if confidence is None:
        confidence = CONFIDENCE_THRESHOLD

    template = load_template(template_name)
    if screenshot is None:
        screenshot = take_screenshot()

    if region == "auto":
        region = None if FULL_SCAN else TEMPLATE_REGIONS.get(template_name)

    offset_x, offset_y = 0, 0
    if region is not None:
        rx, ry, rw, rh = region
        screenshot = screenshot[ry:ry + rh, rx:rx + rw]
        offset_x, offset_y = rx, ry

    th, tw = template.shape[:2]
    if screenshot.shape[0] < th or screenshot.shape[1] < tw:
        return None

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        center_x = offset_x + max_loc[0] + tw // 2
        center_y = offset_y + max_loc[1] + th // 2
        return (center_x, center_y)

    return None


def wait_for_image(template_name, timeout=None, interval=None, confidence=None,
                   region="auto"):
    """Wait until a template image appears on screen.

    Args:
        template_name: Filename of the template to wait for.
        timeout: Max seconds to wait. Defaults to WAIT_TIMEOUT.
        interval: Seconds between checks.
        confidence: Minimum match confidence. Defaults to CONFIDENCE_THRESHOLD.
        region: Optional (x, y, w, h) to restrict the search to.

    Returns:
        (x, y) center coordinates of the match.

    Raises:
        TimeoutError: If the image is not found within the timeout.
    """
    if timeout is None:
        timeout = WAIT_TIMEOUT
    if interval is None:
        interval = POLL_INTERVAL

    start = time.time()
    refocused = False
    while time.time() - start < timeout:
        check_abort()
        pos = find_on_screen(template_name, confidence=confidence, region=region)
        if pos is not None:
            waited = time.time() - start
            if waited > 1.0:
                print(f"      . waited {waited:.1f}s for {template_name}")
            return pos
        if not refocused and time.time() - start > 1.0:
            # A window in front of the game hides everything from the capture.
            refocused = True
            maybe_focus()
        time.sleep(interval)

    # Timeout — save debug screenshot and raise
    elapsed = time.time() - start
    debug_path = save_debug_screenshot(f"timeout_looking_for_{template_name}")
    error_msg = (
        f"Timeout after {elapsed:.1f}s looking for '{template_name}'. "
        f"Debug screenshot saved to: {debug_path}"
    )
    raise TimeoutError(error_msg)


def click_image(template_name, timeout=None, delay_after=None, confidence=None,
                region="auto"):
    """Find a template on screen and click its center.

    Args:
        template_name: Filename of the template to find and click.
        timeout: Max seconds to wait for the image. Defaults to WAIT_TIMEOUT.
        delay_after: Seconds to wait after clicking. Defaults to CLICK_DELAY.
        confidence: Minimum match confidence. Defaults to CONFIDENCE_THRESHOLD.
        region: Optional (x, y, w, h) to restrict the search to.

    Returns:
        (x, y) coordinates that were clicked.

    Raises:
        TimeoutError: If the image is not found within the timeout.
    """
    if delay_after is None:
        delay_after = CLICK_DELAY

    pos = wait_for_image(template_name, timeout=timeout, confidence=confidence, region=region)
    click_at(pos[0], pos[1], template_name)
    time.sleep(delay_after)
    return pos


def find_first(template_names, screenshot=None, confidence=None):
    """Find the first of several interchangeable templates that is on screen.

    Buttons change appearance when the game focuses or hovers them, which stops
    the plain template matching. Each visual variant gets its own template and
    they are tried in turn.

    Args:
        template_names: Iterable of template filenames, most likely first.
        screenshot: Optional pre-captured screenshot.
        confidence: Minimum match confidence.

    Returns:
        (template_name, (x, y)) for the first match, or None.
    """
    if screenshot is None:
        screenshot = take_screenshot()
    for name in template_names:
        pos = find_on_screen(name, screenshot=screenshot, confidence=confidence)
        if pos is not None:
            return name, pos
    return None


def click_first(template_names, timeout=None, delay_after=None, confidence=None):
    """Wait for any of several interchangeable templates, then click it.

    Args:
        template_names: Iterable of template filenames, most likely first.
        timeout: Max seconds to wait. Defaults to WAIT_TIMEOUT.
        delay_after: Seconds to wait after clicking. Defaults to CLICK_DELAY.
        confidence: Minimum match confidence.

    Returns:
        (x, y) that was clicked.

    Raises:
        TimeoutError: If none of the templates showed up in time.
    """
    if timeout is None:
        timeout = WAIT_TIMEOUT
    if delay_after is None:
        delay_after = CLICK_DELAY

    names = list(template_names)
    start = time.time()
    refocused = False
    while time.time() - start < timeout:
        check_abort()
        hit = find_first(names, confidence=confidence)
        if hit is not None:
            name, pos = hit
            click_at(pos[0], pos[1], name)
            time.sleep(delay_after)
            return pos
        if not refocused and time.time() - start > 1.0:
            refocused = True
            maybe_focus()
        time.sleep(POLL_INTERVAL)

    debug_path = save_debug_screenshot("timeout_looking_for_" + names[0])
    raise TimeoutError(
        f"Timeout after {time.time() - start:.1f}s looking for any of "
        f"{names}. Debug screenshot saved to: {debug_path}")


def is_on_screen(template_name, screenshot=None, region="auto"):
    """Check if a template image is currently visible on screen.

    Args:
        template_name: Filename of the template.
        screenshot: Optional pre-captured screenshot.
        region: See find_on_screen.

    Returns:
        True if found, False otherwise.
    """
    return find_on_screen(template_name, screenshot=screenshot, region=region) is not None


def get_item_position(index):
    """Get the screen coordinates for an item in the grid by its index.

    Args:
        index: 0-based item index (left-to-right, top-to-bottom).

    Returns:
        (x, y) center coordinates of the item cell.
    """
    row = index // ITEM_COLS
    col = index % ITEM_COLS
    x = ITEM_START_X + col * ITEM_CELL_W
    y = ITEM_START_Y + row * ITEM_CELL_H
    return (x, y)


def get_inventory_position(index):
    """Get the screen coordinates for a tile in the Manage Inventory grid.

    Args:
        index: 0-based tile index (left-to-right, top-to-bottom).

    Returns:
        (x, y) center coordinates of the tile.
    """
    row = index // INV_COLS
    col = index % INV_COLS
    x = INV_START_X + col * INV_CELL_W
    y = INV_START_Y + row * INV_CELL_H
    return (x, y)




def count_filled_slots(screenshot=None):
    """Count how many of the 5 trade-in slots are filled by checking pixel variance.

    Filled slots have a detailed item image (high pixel variance).
    Empty slots are mostly uniform dark with a faint number (low variance).

    Slot positions derived from the crop of the 5-slot bar at (321, 192, 1318, 263).

    Returns:
        Number of filled slots (0-5).
    """
    if screenshot is None:
        screenshot = take_screenshot()

    # Slot bar: x=321, w=1318 → each slot ~264px wide
    # Slot centers at 1440p: 321 + 132, +264, +264, +264, +264
    slot_centers_x = [453, 717, 980, 1244, 1507]
    slot_y_start = 230  # Inner area of slot (skip top border)
    slot_y_end = 420    # Inner area of slot (skip bottom border)
    slot_half_w = 100   # Check a 200px wide region centered on each slot

    filled = 0
    for cx in slot_centers_x:
        region = screenshot[slot_y_start:slot_y_end, cx - slot_half_w:cx + slot_half_w]
        std = np.std(region)
        if std > 30:  # Filled slots have much more visual variation than empty ones
            filled += 1

    return filled


def dismiss_any_popup(label="unknown popup"):
    """Check for and dismiss any popup dialog by clicking the OK button area.

    Detects popups by checking for bright content in the center of the screen
    where popup headers appear. Handles: 'Too Many Items', 'ERROR', etc.

    Args:
        label: Description for logging.

    Returns:
        True if a popup was detected and dismissed, False otherwise.
    """
    screenshot = take_screenshot()

    # Every OK-only dialog draws the same button in the same place as the
    # quantity popup. The server "ERROR" dialog is far too dark for the
    # brightness check below (77 measured), so the button is what gives it away.
    ok_pos = find_on_screen("quantity_ok.png", screenshot=screenshot)

    # Check the popup header region (center of screen) for high brightness
    popup_region = screenshot[550:650, 950:1600]
    mean_brightness = np.mean(popup_region)

    if ok_pos is not None or mean_brightness > 120:
        print(f"    [popup] Detected {label} — dismissing with OK")
        # OK button is at approximately the same position for all popups
        x, y = ok_pos or (1280, 830)
        click_at(x, y, "generic popup OK")
        time.sleep(0.5)
        return True
    return False


def scroll_item_grid():
    """Scroll down in the item grid to reveal more items.

    Returns:
        True if scroll was performed.
    """
    # Move mouse to center of item grid and scroll down
    grid_center_x = ITEM_GRID_X + ITEM_GRID_W // 2
    grid_center_y = ITEM_GRID_Y + ITEM_GRID_H // 2
    pyautogui.moveTo(grid_center_x, grid_center_y)
    time.sleep(0.1)
    pyautogui.scroll(-3)  # Scroll down
    time.sleep(0.3)
    park_mouse()
    return True


def execute_trade():
    """Execute the trade-in: click ACCEPT, confirm YES, dismiss reward.

    In dry-run mode nothing is clicked — the trade is only reported.

    Returns:
        True if trade completed successfully, False if skipped by dry-run.

    Raises:
        TimeoutError: If any step in the trade process fails.
    """
    print("  [trade] 5 slots filled — executing trade...")
    trace("slots_full_before_accept")

    if DRY_RUN:
        print("  [dry-run] Would click ACCEPT > YES > OK. Nothing traded.")
        return False

    # Click ACCEPT
    try:
        click_image("accept_button.png", timeout=5, delay_after=0.5)
    except TimeoutError:
        print("    [warn] ACCEPT template not found, clicking known position")
        click_at(1000, 495, "ACCEPT fallback")
        time.sleep(0.5)

    # Click YES on confirm popup
    try:
        click_image("confirm_yes.png", timeout=5, delay_after=LONG_DELAY)
    except TimeoutError:
        print("    [warn] YES template not found, clicking known position")
        click_at(1132, 835, "YES fallback")
        time.sleep(LONG_DELAY)

    # Click OK on reward screen
    try:
        click_first(("reward_ok.png", "drop_reveal_ok.png", "drop_reveal_ok_hl.png"),
                    timeout=5, delay_after=0.3)
    except TimeoutError:
        # No reward screen can also mean the servers refused the trade.
        if dismiss_any_popup("error instead of reward"):
            raise TimeoutError("the game showed an error dialog instead of a reward")
        print("    [warn] Reward OK template not found, clicking known position")
        click_at(1280, 1060, "reward OK fallback")
        time.sleep(0.5)

    print("  [trade] Trade complete! Reward collected.")
    return True


def run_trade_in_loop(category_name):
    """Run the trade-in loop for a single category.

    Clicks items in the grid one by one, handles popups, fills 5 slots,
    executes the trade, and repeats until no more items can be traded.

    Uses visual slot counting after each action for reliable tracking.

    Args:
        category_name: Display name of the category (for logging/summary).

    Returns:
        Number of trades completed in this category.
    """
    trades_completed = 0
    item_index = 0
    max_items_visible = ITEM_COLS * ITEM_ROWS
    scroll_attempts = 0
    max_scroll_attempts = 5
    no_change_count = 0
    max_no_change = 7  # Bail out after this many consecutive items with no slot change

    print(f"\n  Starting trade-in for: {category_name}")

    while True:
        check_abort()
        maybe_focus()

        # Take ONE screenshot and reuse for all checks (big speed improvement)
        screen = take_screenshot()

        # Check if game auto-returned us to main menu (category complete)
        if is_on_trade_in_menu(screenshot=screen):
            print(f"  [done] Category complete — game returned to main menu.")
            return trades_completed

        # Visually check how many slots are currently filled
        slots_filled = count_filled_slots(screenshot=screen)

        # If 5 slots filled, execute the trade
        if slots_filled >= 5:
            try:
                if not execute_trade():
                    # Dry-run: the slots stay full, so stop instead of looping.
                    print("  [dry-run] Stopping category with slots still filled.")
                    return trades_completed
                trades_completed += 1
                # Accumulate: a category can be visited again in a later pass.
                trade_summary[category_name] = trade_summary.get(category_name, 0) + 1
                item_index = 0
                scroll_attempts = 0
                time.sleep(1.0)
                if is_on_trade_in_menu():
                    print(f"  [done] Category complete — game returned to main menu.")
                    return trades_completed
                continue
            except TimeoutError as e:
                print(f"  [ERROR] Trade execution failed: {e}")
                break

        # If we've tried all visible items
        if item_index >= max_items_visible:
            if scroll_attempts < max_scroll_attempts:
                print(f"  [scroll] Scrolling down for more items (attempt {scroll_attempts + 1})...")
                before_scroll = take_screenshot()
                scroll_item_grid()
                after_scroll = take_screenshot()

                grid_before = before_scroll[ITEM_GRID_Y:ITEM_GRID_Y+ITEM_GRID_H, ITEM_GRID_X:ITEM_GRID_X+ITEM_GRID_W]
                grid_after = after_scroll[ITEM_GRID_Y:ITEM_GRID_Y+ITEM_GRID_H, ITEM_GRID_X:ITEM_GRID_X+ITEM_GRID_W]
                if np.mean(cv2.absdiff(grid_before, grid_after)) < 5:
                    print("  [scroll] No new items found after scrolling.")
                    break

                item_index = 0
                scroll_attempts += 1
                continue
            else:
                print("  [done] Max scroll attempts reached — category exhausted.")
                break

        # Click the next item in the grid
        pos = get_item_position(item_index)
        click_at(pos[0], pos[1], f"item {item_index}")
        time.sleep(0.2)  # Brief wait for game to respond

        # Take ONE screenshot for all popup checks
        popup_screen = take_screenshot()

        # Check for "Not Eligible" popup
        if find_on_screen("not_eligible_popup.png", screenshot=popup_screen, confidence=0.6) is not None:
            try:
                click_image("not_eligible_ok.png", timeout=2, delay_after=0.2)
            except TimeoutError:
                click_at(1280, 815, "not-eligible OK fallback")
                time.sleep(0.2)
            print("    [skip] Item not eligible for trade-in")
            item_index += 1
            continue

        # Check for "Choose Quantity" popup
        if find_on_screen("choose_quantity_popup.png", screenshot=popup_screen, confidence=0.6) is not None:
            slots_remaining = 5 - slots_filled
            clicks_needed = slots_remaining - 1
            for _ in range(clicks_needed):
                click_at(1375, 731, "quantity +")
                time.sleep(0.15)
            try:
                click_image("quantity_ok.png", timeout=2, delay_after=0.2)
            except TimeoutError:
                click_at(1132, 815, "quantity OK fallback")
                time.sleep(0.2)
            new_count = count_filled_slots()
            print(f"    [quantity] Selected duplicates. Slots filled: {new_count}/5")
            item_index += 1
            continue

        # Check for any other popup (Too Many Items, etc.)
        popup_region = popup_screen[550:650, 950:1600]
        if np.mean(popup_region) > 120:
            print("    [popup] Unexpected popup — dismissing")
            click_at(1280, 830, "unexpected popup OK")
            time.sleep(0.3)
            continue

        # No popup — item was added directly
        new_count = count_filled_slots(screenshot=popup_screen)
        if new_count > slots_filled:
            print(f"    [+] Item added. Slots filled: {new_count}/5")
            no_change_count = 0
        else:
            no_change_count += 1
            print(f"    [?] Clicked item {item_index} — no change (slots: {new_count}/5)")
            if no_change_count >= max_no_change:
                print(f"  [done] {max_no_change} items in a row with no change — category exhausted.")
                break
        item_index += 1

    slots_filled = count_filled_slots()
    if 0 < slots_filled < 5:
        print(f"  [done] Only {slots_filled}/5 slots filled — not enough items to trade.")

    return trades_completed


def is_on_trade_in_menu(screenshot=None):
    """Check if the trade-in category screen is showing."""
    if screenshot is None:
        screenshot = take_screenshot()

    # The "TRADE IN" panel title is always there. The category cards are not a
    # reliable marker: every one of them dims out once you drop below five
    # items of that quality, and then none of them match.
    try:
        return is_on_screen("trade_in_title.png", screenshot=screenshot)
    except FileNotFoundError:
        pass

    for template_name, _ in CATEGORY_CARDS[:3]:
        try:
            if is_on_screen(template_name, screenshot=screenshot):
                return True
        except FileNotFoundError:
            continue
    return False


# --- Navigation from the Rocket League main menu -----------------------------
# Main Menu -> GARAGE -> TRADE IN            (the trade-in category screen)
# Main Menu -> GARAGE -> MANAGE INVENTORY    -> REWARD ITEMS tab (drops)
#
# Escape is reserved as the abort key, so every "back" step clicks the on-screen
# BACK button instead of pressing Escape.

def is_on_rl_main_menu(screenshot=None):
    """True if the Rocket League main menu (PLAY / GARAGE / ...) is showing."""
    return is_on_screen("menu_garage.png", screenshot=screenshot)


def is_on_garage_menu(screenshot=None):
    """True if the Garage preset menu (CUSTOMIZE CAR / TRADE IN / ...) is showing."""
    if screenshot is None:
        screenshot = take_screenshot()
    return (is_on_screen("garage_trade_in.png", screenshot=screenshot)
            and is_on_screen("garage_manage_inv.png", screenshot=screenshot))


def is_in_inventory(screenshot=None):
    """True if the Manage Inventory screen is showing (any tab)."""
    if screenshot is None:
        screenshot = take_screenshot()
    return (is_on_screen("inv_header_all.png", screenshot=screenshot)
            or is_on_screen("inv_header_reward.png", screenshot=screenshot))


def is_on_reward_items_tab(screenshot=None):
    """True if the Manage Inventory REWARD ITEMS tab is showing."""
    return is_on_screen("inv_header_reward.png", screenshot=screenshot)


def is_on_drop_preview(screenshot=None):
    """True if a single drop is being previewed (the OPEN DROP screen)."""
    try:
        return is_on_screen("drop_open_button.png", screenshot=screenshot)
    except FileNotFoundError:
        return False


def is_on_drop_reveal(screenshot=None):
    """True if a freshly opened item is being revealed."""
    try:
        return is_on_screen("drop_reveal_label.png", screenshot=screenshot)
    except FileNotFoundError:
        return False


def describe_current_screen():
    """Identify which known screen is currently visible.

    Returns:
        One of "main_menu", "garage", "inventory", "drop_preview",
        "drop_reveal", "trade_in", or "unknown".
    """
    screen = take_screenshot()
    # The reveal overlays the preview, so it has to be checked first.
    if is_on_drop_reveal(screenshot=screen):
        return "drop_reveal"
    if is_on_drop_preview(screenshot=screen):
        return "drop_preview"
    if is_on_trade_in_menu(screenshot=screen):
        return "trade_in"
    if is_in_inventory(screenshot=screen):
        return "inventory"
    if is_on_garage_menu(screenshot=screen):
        return "garage"
    if is_on_rl_main_menu(screenshot=screen):
        return "main_menu"
    return "unknown"


def wait_for_screen_change(previous, timeout=4.0, interval=0.1):
    """Block until the detected screen differs from `previous`.

    Screen recognition costs about 7 ms, so polling for the real transition is
    cheaper and far more reliable than sleeping for a guessed duration.

    Args:
        previous: Screen name the UI was showing before the click.
        timeout: Seconds to wait for the change.
        interval: Seconds between checks.

    Returns:
        The new screen name, or `previous` if it never changed.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        check_abort()
        current = describe_current_screen()
        if current != previous:
            return current
        time.sleep(interval)
    return previous


def goto_garage_menu():
    """From the Rocket League main menu, open the Garage menu.

    Returns:
        True once the Garage menu is visible.

    Raises:
        TimeoutError: If the Garage menu never appears.
    """
    print("[nav] Main menu -> GARAGE")
    trace("nav_main_menu")
    click_image("menu_garage.png", timeout=8, delay_after=LONG_DELAY)
    wait_for_image("garage_trade_in.png", timeout=8)
    trace("nav_garage_menu")
    return True


def goto_trade_in_screen():
    """From the Garage menu, open the TRADE IN screen.

    Returns:
        True once the trade-in category cards are visible.

    Raises:
        TimeoutError: If the trade-in screen never appears.
    """
    print("[nav] Garage -> TRADE IN")
    click_image("garage_trade_in.png", timeout=8, delay_after=LONG_DELAY)

    start = time.time()
    while time.time() - start < WAIT_TIMEOUT:
        check_abort()
        if is_on_trade_in_menu():
            trace("nav_trade_in_screen")
            return True
        time.sleep(0.4)

    debug_path = save_debug_screenshot("trade_in_screen_did_not_open")
    raise TimeoutError(f"Trade-in screen did not open. Debug screenshot: {debug_path}")


def goto_manage_inventory():
    """From the Garage menu, open MANAGE INVENTORY.

    Returns:
        True once the inventory screen is visible.

    Raises:
        TimeoutError: If the inventory screen never appears.
    """
    print("[nav] Garage -> MANAGE INVENTORY")
    click_image("garage_manage_inv.png", timeout=8, delay_after=LONG_DELAY)

    start = time.time()
    while time.time() - start < WAIT_TIMEOUT:
        check_abort()
        if is_in_inventory():
            trace("nav_inventory")
            return True
        time.sleep(0.4)

    debug_path = save_debug_screenshot("inventory_did_not_open")
    raise TimeoutError(f"Manage Inventory did not open. Debug screenshot: {debug_path}")


def goto_reward_items_tab():
    """Select the REWARD ITEMS tab in Manage Inventory.

    The tab strip shifts as the active tab widens, so the tab icon is located by
    template match inside INV_TAB_SEARCH_REGION rather than clicked blind.

    Returns:
        True once the REWARD ITEMS header is visible.

    Raises:
        TimeoutError: If the tab icon is not found or the tab never opens.
    """
    if is_on_reward_items_tab():
        return True

    print("[nav] Manage Inventory -> REWARD ITEMS tab")
    click_image("inv_tab_reward.png", timeout=8, delay_after=LONG_DELAY,
                confidence=0.65, region=INV_TAB_SEARCH_REGION)

    start = time.time()
    while time.time() - start < WAIT_TIMEOUT:
        check_abort()
        if is_on_reward_items_tab():
            trace("nav_reward_items_tab")
            return True
        time.sleep(0.4)

    debug_path = save_debug_screenshot("reward_items_tab_did_not_open")
    raise TimeoutError(f"REWARD ITEMS tab did not open. Debug screenshot: {debug_path}")


def click_back_button():
    """Click the on-screen BACK button (bottom-left) and wait for the transition."""
    for attempt in range(2):
        for template in ("inv_back.png", "back_button.png"):
            pos = find_on_screen(template)
            if pos is not None:
                click_at(pos[0], pos[1], "BACK")
                time.sleep(SHORT_DELAY)
                return True
        if attempt == 0:
            # A screen transition may still be animating; clear any hover and retry.
            park_mouse()
            time.sleep(0.4)
    raise TimeoutError("BACK button not found on screen")


def return_to_rl_main_menu(max_steps=4):
    """Click BACK repeatedly until the Rocket League main menu is showing.

    Args:
        max_steps: Safety cap on the number of BACK clicks.

    Returns:
        True if the main menu was reached, False otherwise.
    """
    for _ in range(max_steps):
        check_abort()
        if is_on_rl_main_menu():
            return True
        try:
            click_back_button()
        except TimeoutError:
            break
    return is_on_rl_main_menu()


def ensure_screen(target, max_steps=12):
    """Navigate from wherever we are to a target screen.

    Walks the menu tree one step at a time, re-reading the screen after each
    step, so it recovers from being left on an unexpected screen by an earlier
    run. Screens that are not on the way to the target are backed out of.

    Args:
        target: "trade_in" or "reward_items".
        max_steps: Safety cap on navigation steps.

    Returns:
        True on success.

    Raises:
        TimeoutError: If navigation fails.
        ValueError: If the target is unknown.
    """
    if target not in ("trade_in", "reward_items"):
        raise ValueError(f"Unknown navigation target: {target}")

    for step in range(max_steps):
        check_abort()
        maybe_focus()
        where = describe_current_screen()
        print(f"[nav] Currently on: {where}")
        trace("nav_step", note=f"detected={where} target={target}")

        if target == "trade_in" and where == "trade_in":
            return True
        if target == "reward_items" and where == "inventory":
            return goto_reward_items_tab()

        if where == "main_menu":
            goto_garage_menu()
            continue

        if where == "garage":
            if target == "trade_in":
                return goto_trade_in_screen()
            goto_manage_inventory()
            continue

        # Any other known screen (drop preview, the wrong branch of the menu
        # tree) is backed out of one level at a time.
        if where == "drop_reveal":
            click_first(DROP_TEMPLATES["reveal_ok"], timeout=5)
            continue

        # A modal dialog (for example a server "ERROR") swallows every click
        # behind it, BACK included, so it has to go before anything else.
        if where == "unknown" and dismiss_any_popup("blocking popup"):
            continue

        if where in ("drop_preview", "inventory", "trade_in") or find_on_screen("back_button.png"):
            click_back_button()
            # The menu animates out; without waiting for the real transition the
            # next pass would see the old screen and click BACK again.
            if wait_for_screen_change(where) == where:
                print(f"  [nav] Screen did not change after BACK (still {where})")
            continue

        debug_path = save_debug_screenshot("unknown_start_screen")
        raise TimeoutError(
            "Could not recognise the current screen. Open Rocket League's main "
            f"menu and try again. Debug screenshot: {debug_path}")

    debug_path = save_debug_screenshot("navigation_gave_up")
    raise TimeoutError(
        f"Gave up navigating to {target} after {max_steps} steps. "
        f"Debug screenshot: {debug_path}")


# --- Reward drops ------------------------------------------------------------

# Templates needed to open drops. They are cropped from real screenshots of the
# open-drop flow, which `--discover-drops` captures for you.
DROP_TEMPLATES = {
    "open_button": "drop_open_button.png",  # the OPEN DROP button
    # The reveal is recognised by its constant "NEW ITEM" caption rather than by
    # its buttons, which differ per item: EQUIP NOW + OK for equippable items,
    # a single OK otherwise, and that single OK comes up focus-highlighted.
    "reveal_label": "drop_reveal_label.png",
    "reveal_ok": ("drop_reveal_ok.png", "drop_reveal_ok_hl.png"),
}


def missing_drop_templates():
    """Return the list of drop templates that are not present on disk."""
    missing = []
    for value in DROP_TEMPLATES.values():
        names = (value,) if isinstance(value, str) else value
        for name in names:
            if not os.path.exists(os.path.join(TEMPLATES_DIR, name)):
                missing.append(name)
    return missing


def tile_is_occupied(screenshot, index):
    """Check whether an inventory tile holds an item.

    Empty tiles are a flat dark panel; occupied tiles show an icon and a label,
    so pixel variance separates them cleanly.

    Args:
        screenshot: BGR screenshot of the full screen.
        index: 0-based tile index in the inventory grid.

    Returns:
        True if the tile appears to hold an item.
    """
    cx, cy = get_inventory_position(index)
    half_w, half_h = INV_CELL_W // 2 - 12, INV_CELL_H // 2 - 12
    region = screenshot[cy - half_h:cy + half_h, cx - half_w:cx + half_w]
    if region.size == 0:
        return False
    # Measured on ui-images/inventory_reward_items.png: occupied tiles score
    # 58-79, empty panel tiles score 3-6. Colour std does not separate them
    # (the empty panel's blue gradient inflates it), grayscale std does.
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    return np.std(gray) > 20


def tile_signature(screenshot, index):
    """Return a coarse fingerprint of an inventory tile's artwork.

    Emptying a stack removes its tile and shifts every later tile one place to
    the left, so remembering "skip tile 3" is wrong the moment anything is
    opened. The fingerprint identifies the stack itself instead of its slot.
    The quantity badge in the top-right corner is left out, because it changes
    as a stack shrinks.

    Args:
        screenshot: BGR screenshot of the full screen.
        index: 0-based tile index in the inventory grid.

    Returns:
        Bytes usable as a dict/set key.
    """
    cx, cy = get_inventory_position(index)
    half_w, half_h = INV_CELL_W // 3, INV_CELL_H // 3
    region = screenshot[cy - half_h:cy + half_h, cx - half_w:cx + half_w]
    if region.size == 0:
        return b""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (12, 12), interpolation=cv2.INTER_AREA)
    # Quantise so lighting and animation jitter do not change the fingerprint.
    return (small // 32).tobytes()


def count_reward_tiles(screenshot=None):
    """Count occupied tiles on the currently visible inventory page."""
    if screenshot is None:
        screenshot = take_screenshot()
    return sum(tile_is_occupied(screenshot, i) for i in range(INV_COLS * INV_ROWS))


def discover_drop_flow(frames=14, interval=0.4, open_it=False):
    """Click the first reward drop and record what the UI does.

    Used to calibrate the open-drop flow: the captured frames show which button
    appears and where, so the templates in DROP_TEMPLATES can be cropped.

    Args:
        frames: Number of screenshots to capture after the click.
        interval: Seconds between screenshots.
        open_it: Also click OPEN DROP and record the reveal. This actually
            opens one drop, so it is off by default.

    Returns:
        List of paths to the captured screenshots.
    """
    ensure_screen("reward_items")
    time.sleep(0.5)

    out_dir = os.path.join(DEBUG_DIR, "drop_flow")
    os.makedirs(out_dir, exist_ok=True)

    paths = []

    def capture(step, label):
        path = os.path.join(out_dir, f"{step:02d}_{label}.png")
        cv2.imwrite(path, take_screenshot())
        paths.append(path)
        print(f"  captured {path}")

    capture(0, "reward_tab")

    cx, cy = get_inventory_position(0)
    print(f"[discover] Clicking first drop tile at ({cx}, {cy})")
    click_at(cx, cy, "drop tile 0")

    preview_frames = 6 if open_it else frames
    for i in range(1, preview_frames + 1):
        check_abort()
        time.sleep(interval)
        capture(i, "after_click")

    if open_it:
        open_template = DROP_TEMPLATES["open_button"]
        if not os.path.exists(os.path.join(TEMPLATES_DIR, open_template)):
            print(f"[discover] {open_template} missing - cannot record the reveal.")
        else:
            print("[discover] Clicking OPEN DROP - this opens one real drop")
            click_image(open_template, timeout=5, delay_after=0.0)
            for i in range(preview_frames + 1, preview_frames + 1 + frames):
                check_abort()
                time.sleep(interval)
                capture(i, "after_open")

    print(f"\n[discover] {len(paths)} frames written to {out_dir}")
    print("           Crop the OPEN button and the reveal-dismiss button from these")
    print(f"           frames into {TEMPLATES_DIR}/ as:")
    for key, name in DROP_TEMPLATES.items():
        print(f"             {name}  ({key})")
    return paths


def open_one_drop(attempts=2, reveal_timeout=3.0):
    """Click OPEN DROP on the preview and dismiss the reveal that follows.

    Rocket League silently drops clicks that land while a menu is still
    animating, so a single click is not enough. An exhausted stack looks the
    same from the outside - the preview stays up and OPEN DROP simply stops
    responding - so a run of failed clicks means "this stack is empty", not
    "the bot is broken".

    Args:
        attempts: How many times to click OPEN DROP before giving up.
        reveal_timeout: Seconds to wait for the reveal after each click.

    Returns:
        True if a drop was opened.
    """
    for attempt in range(attempts):
        check_abort()
        try:
            click_image(DROP_TEMPLATES["open_button"], timeout=4, delay_after=0.25)
        except TimeoutError:
            return False

        try:
            click_first(DROP_TEMPLATES["reveal_ok"], timeout=reveal_timeout)
            time.sleep(DROP_SETTLE)
            return True
        except TimeoutError:
            if not is_on_drop_preview():
                # Something else is on screen; let the caller re-orient.
                return False
            print(f"      . OPEN DROP click {attempt + 1} did not register, retrying")
            time.sleep(DROP_SETTLE)

    return False


def open_all_drops(max_drops=500, max_steps=4000):
    """Open every drop on the REWARD ITEMS tab.

    Runs as a small state machine rather than a fixed click sequence, because
    the game moves between three screens while opening a stack:

        reward grid  -> click a drop tile
        drop preview -> click OPEN DROP
        reveal       -> click OK, which lands back on the preview while the
                        stack still has drops, and on the grid once it is empty

    Tiles that do not lead to a preview (crates that need a key, for instance)
    are skipped after one attempt.

    Args:
        max_drops: Stop after opening this many drops.
        max_steps: Safety cap on state machine iterations.

    Returns:
        Number of drops opened.

    Raises:
        FileNotFoundError: If the drop templates have not been calibrated.
    """
    missing = missing_drop_templates()
    if missing:
        raise FileNotFoundError(
            "Drop templates are not calibrated yet: " + ", ".join(missing) + ". "
            "Run `python trade_in_bot.py --discover-drops` and crop them "
            "from the captured frames.")

    # Already inside the drop flow? Then there is nothing to navigate to.
    if describe_current_screen() not in ("drop_preview", "drop_reveal"):
        ensure_screen("reward_items")

    opened = 0
    skipped_stacks = set()  # fingerprints of stacks that cannot be opened
    empty_previews = 0
    current_signature = None

    for _ in range(max_steps):
        check_abort()
        maybe_focus()
        if opened >= max_drops:
            print(f"  [drops] Reached the {max_drops} drop limit.")
            break
        screen = take_screenshot()

        if is_on_drop_reveal(screenshot=screen):
            click_first(DROP_TEMPLATES["reveal_ok"], timeout=5)
            # The preview slides back in; clicking during that animation is
            # swallowed by the game.
            time.sleep(DROP_SETTLE)
            continue

        if is_on_drop_preview(screenshot=screen):
            if DRY_RUN:
                print("  [dry-run] On the drop preview. Would click OPEN DROP.")
                trace("dry_run_drop_preview")
                return opened
            if open_one_drop():
                opened += 1
                empty_previews = 0
                print(f"  [drops] Opened {opened}")
            else:
                # OPEN DROP stopped responding: this stack is empty. Back out to
                # the grid so the next stack can be picked up.
                empty_previews += 1
                print("  [drops] Stack exhausted — back to the grid")
                if current_signature is not None:
                    skipped_stacks.add(current_signature)
                    current_signature = None
                try:
                    click_back_button()
                    wait_for_screen_change("drop_preview")
                except TimeoutError:
                    ensure_screen("reward_items")
                if empty_previews >= 3 and opened == 0:
                    print("  [drops] Three empty stacks in a row and nothing opened — stopping.")
                    break
            continue

        if is_on_reward_items_tab(screenshot=screen):
            tile = None
            for i in range(INV_COLS * INV_ROWS):
                if not tile_is_occupied(screen, i):
                    continue
                if tile_signature(screen, i) in skipped_stacks:
                    continue
                tile = i
                break

            if tile is None:
                print("  [drops] No openable drops left on this tab.")
                break

            signature = tile_signature(screen, tile)
            cx, cy = get_inventory_position(tile)
            click_at(cx, cy, f"drop tile {tile}")
            time.sleep(CLICK_DELAY)
            if is_on_drop_preview():
                current_signature = signature
            else:
                print(f"  [drops] Tile {tile} is not an openable drop — skipping.")
                skipped_stacks.add(signature)
            continue

        # Somewhere else entirely — walk back to the reward grid.
        ensure_screen("reward_items")

    print(f"[drops] Done — {opened} drop{'s' if opened != 1 else ''} opened.")
    return opened


def card_is_available(template_name, position, screenshot=None):
    """Check whether a category card is selectable rather than dimmed out.

    The dimmed Tournament cards still match their templates, so without this
    the bot clicks each of them and waits for a screen that never opens.

    Args:
        template_name: Card template filename.
        position: (x, y) centre returned by find_on_screen.
        screenshot: Optional pre-captured screenshot.

    Returns:
        True if the card looks enabled.
    """
    if screenshot is None:
        screenshot = take_screenshot()

    template = load_template(template_name)
    h, w = template.shape[:2]
    x, y = position[0] - w // 2, position[1] - h // 2
    crop = screenshot[y:y + h, x:x + w]
    if crop.size == 0:
        return True

    brightness = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2].mean()
    return brightness > CARD_ENABLED_BRIGHTNESS


def navigate_to_category(template_name, category_name):
    """Click a category card from the main menu and wait for the trade-in screen.

    Args:
        template_name: Template filename for the category card.
        category_name: Display name (for logging).

    Returns:
        True if successfully navigated to the trade-in screen, False if card not found.
    """
    print(f"\n[>] Trying category: {category_name}")

    # Check if the card exists on screen. This is a single look rather than a
    # wait, so a window covering the game would read as "no cards".
    maybe_focus()
    screen = take_screenshot()
    pos = find_on_screen(template_name, screenshot=screen)
    if pos is None:
        print(f"  [skip] Card not found on screen — may not have enough items.")
        return False

    if not card_is_available(template_name, pos, screenshot=screen):
        print(f"  [skip] Card is dimmed — fewer than 5 items available.")
        return False

    click_at(pos[0], pos[1], f"category card {category_name}")
    time.sleep(0.4)

    # Wait for trade-in screen to appear
    try:
        wait_for_image("show_filters.png", timeout=5)
        print(f"  [ok] Entered trade-in screen for {category_name}")
        trace("category_opened", note=category_name)
        return True
    except TimeoutError:
        debug_path = save_debug_screenshot(f"failed_entering_{template_name}")
        print(f"  [ERROR] Trade-in screen didn't appear after clicking {category_name}.")
        print(f"          Debug screenshot: {debug_path}")
        return False


def go_back_to_main_menu():
    """Click the BACK button to return to the main menu."""
    print("\n[<] Going back to main menu...")
    try:
        click_image("back_button.png", timeout=5, delay_after=0.8)
    except TimeoutError as e:
        print(f"  [ERROR] Could not find BACK button: {e}")
        raise


def run_all_categories():
    """Work through every trade-in category from the trade-in category screen.

    Returns:
        Number of trades completed in this pass.
    """
    pass_trades = 0
    for template_name, category_name in CATEGORY_CARDS:
        check_abort()

        # Dismiss any popup (e.g., "ERROR - Inventory out of sync")
        # These can appear after trades with a delay
        dismiss_any_popup("sync error")

        # Try to enter this category
        if not navigate_to_category(template_name, category_name):
            continue

        # Run the trade-in loop (updates trade_summary incrementally)
        try:
            pass_trades += run_trade_in_loop(category_name)
        except TimeoutError as e:
            print(f"  [ERROR] Trade-in loop failed: {e}")
        except Exception as e:
            debug_path = save_debug_screenshot(f"error_in_{template_name}")
            print(f"  [ERROR] Unexpected error: {e}")
            print(f"          Debug screenshot: {debug_path}")

        # Get back to the category screen from wherever the game left us. A
        # completed trade sometimes returns there by itself, and clicking BACK
        # on top of that drops out to the Garage menu, so navigate by state
        # rather than by a fixed number of BACK clicks.
        try:
            ensure_screen("trade_in")
        except TimeoutError as e:
            print(f"[ERROR] Could not return to the trade-in screen: {e}")
            break

        # Error popups can show up a moment after a trade.
        for _ in range(3):
            if dismiss_any_popup("post-trade error"):
                time.sleep(0.5)
                ensure_screen("trade_in")
            else:
                break

    return pass_trades


def run_trade_in_passes(max_passes=5):
    """Repeat the category sweep until a pass trades nothing.

    Every trade hands back a higher-quality item, which can push another
    category over the five-item threshold, so one sweep is never enough. The
    trade-in screen also caches its per-category counts, so it is left and
    re-entered between passes to force a recount.

    Args:
        max_passes: Safety cap on the number of sweeps.

    Returns:
        Total trades across all passes.
    """
    total = 0
    for pass_number in range(1, max_passes + 1):
        check_abort()
        ensure_screen("trade_in")
        time.sleep(CATEGORY_REFRESH_DELAY)

        print(f"\n=== Pass {pass_number} ===")
        traded = run_all_categories()
        total += traded

        if traded == 0:
            print(f"[done] Pass {pass_number} traded nothing — inventory is exhausted.")
            break

        print(f"[pass {pass_number}] {traded} trades — new items may unlock more, going again")
        # Leave the screen so the game recalculates the category counts.
        try:
            click_back_button()
            wait_for_screen_change("trade_in")
        except TimeoutError:
            pass
    else:
        print(f"[done] Stopped after {max_passes} passes.")

    return total


def countdown(seconds=3):
    """Give the user time to bring Rocket League to the foreground."""
    print(f"Starting in {seconds} seconds — switch to Rocket League now!")
    for i in range(seconds, 0, -1):
        check_abort()
        print(f"  {i}...")
        time.sleep(1)
    print("  Go!\n")


def build_parser():
    p = argparse.ArgumentParser(
        description="Rocket League trade-in bot. Navigates from the main menu, "
                    "opens reward drops, then trades in items.")
    p.add_argument("--mode", default="full",
                   choices=["full", "drops", "trade", "where"],
                   help="full: open drops then trade in (default). "
                        "drops: only open reward drops. "
                        "trade: only run the trade-in loop. "
                        "where: report which screen is currently visible and exit.")
    p.add_argument("--discover-drops", action="store_true",
                   help="Capture the open-drop UI flow to debug/drop_flow/ for calibration")
    p.add_argument("--discover-open", action="store_true",
                   help="Like --discover-drops, but also clicks OPEN DROP so the "
                        "reveal screen is recorded. Opens one real drop.")
    p.add_argument("--no-countdown", action="store_true",
                   help="Skip the 3 second countdown before starting")
    p.add_argument("--dry-run", action="store_true",
                   help="Navigate and select, but never click ACCEPT / YES / OPEN. "
                        "Nothing is traded and no drop is opened.")
    p.add_argument("--trace", action="store_true",
                   help="Record a labelled screenshot at each step into debug/trace/")
    p.add_argument("--max-passes", type=int, default=5,
                   help="How many times to sweep every trade-in category (default 5). "
                        "Each trade can unlock another category.")
    p.add_argument("--max-drops", type=int, default=500,
                   help="Stop after opening this many drops (default 500)")
    p.add_argument("--full-scan", action="store_true",
                   help="Search the whole screen for every template instead of the "
                        "known regions. Much slower; use if the UI has moved.")
    p.add_argument("--no-focus", action="store_true",
                   help="Never touch window focus. Without this the bot keeps the "
                        "game in front, because anything covering it breaks capture.")
    return p


def main():
    """Main entry point."""
    global DRY_RUN, TRACE, AUTO_FOCUS, FULL_SCAN
    args = build_parser().parse_args()
    DRY_RUN = args.dry_run
    TRACE = args.trace
    AUTO_FOCUS = not args.no_focus
    FULL_SCAN = args.full_scan

    log_path = start_run_log()

    print("=" * 50)
    print("  Rocket League Trade-In Bot")
    print(f"  Log: {log_path}")
    if DRY_RUN:
        print("  DRY RUN — no trades, no drops opened")
    if TRACE:
        print(f"  TRACE — frames go to {TRACE_DIR}")
    print("  Press Escape at any time to abort")
    print("=" * 50)
    print()

    if TRACE:
        reset_trace()

    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()

    try:
        if not args.no_focus:
            focus_game()
            time.sleep(0.5)

        if args.mode == "where":
            where = describe_current_screen()
            print(f"Current screen: {where}")
            trace("where", note=where)
            return

        if not args.no_countdown:
            countdown()

        if args.discover_drops or args.discover_open:
            discover_drop_flow(open_it=args.discover_open)
            return

        if args.mode in ("full", "drops"):
            try:
                open_all_drops(max_drops=args.max_drops)
            except FileNotFoundError as e:
                print(f"[skip drops] {e}")
                if args.mode == "drops":
                    return

        if args.mode in ("full", "trade"):
            run_trade_in_passes(args.max_passes)

    except SystemExit:
        pass  # Abort via check_abort() — summary already printed
    except Exception as e:
        debug_path = save_debug_screenshot("unexpected_error")
        print(f"\n[FATAL ERROR] {e}")
        print(f"              Debug screenshot: {debug_path}")
    finally:
        print_summary()
        print(f"Log written to {log_path}")
        listener.stop()
        stop_run_log()


if __name__ == "__main__":
    main()
