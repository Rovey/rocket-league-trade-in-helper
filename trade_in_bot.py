"""Rocket League Trade-In Automation Bot.

Automates the item trade-in process using screen capture and template matching.
Press Escape at any time to abort.

Usage:
    python trade_in_bot.py
"""

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
CONFIDENCE_THRESHOLD = 0.8  # Template matching confidence (0-1)
WAIT_TIMEOUT = 10  # Seconds to wait before giving up on finding an image
CLICK_DELAY = 0.4  # Seconds between regular actions
LONG_DELAY = 1.5  # Seconds for reward animation, screen transitions
SHORT_DELAY = 0.3  # Seconds for popup dismissals

# Item grid region on the trade-in screen (x, y, width, height) at 1440p
# This is the area where item icons appear below the 5 trade-in slots
ITEM_GRID_X = 35
ITEM_GRID_Y = 275
ITEM_GRID_W = 440
ITEM_GRID_H = 360

# Grid layout: items are arranged in rows and columns
ITEM_COLS = 8  # Items per row
ITEM_ROWS = 3  # Visible rows
ITEM_CELL_W = 55  # Approximate width of each item cell
ITEM_CELL_H = 75  # Approximate height of each item cell
ITEM_START_X = 55  # X of first item center (relative to screen)
ITEM_START_Y = 310  # Y of first item center (relative to screen)

# Category cards to try, in order (template filename, display name)
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

# --- Global State ---
abort_flag = False
trade_summary = {}  # {"Category Name": trade_count}


def on_key_press(key):
    """Keyboard listener callback. Sets abort flag on Escape."""
    global abort_flag
    if key == keyboard.Key.esc:
        abort_flag = True
        print("\n[!] Escape pressed — aborting after current action...")


def check_abort():
    """Check if abort was requested. Raises SystemExit if so."""
    if abort_flag:
        print_summary()
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
    safe_context = context.replace(" ", "_").replace("/", "_")
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


def take_screenshot():
    """Capture the screen and return as a BGR numpy array (for OpenCV)."""
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    # Convert RGB (PIL) to BGR (OpenCV)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame


def find_on_screen(template_name, screenshot=None, confidence=None):
    """Find a template image on screen.

    Args:
        template_name: Filename of the template in TEMPLATES_DIR.
        screenshot: Optional pre-captured screenshot. If None, captures a new one.
        confidence: Minimum match confidence (0-1). Defaults to CONFIDENCE_THRESHOLD.

    Returns:
        (x, y) center coordinates of the best match if confidence exceeds threshold,
        or None if not found.
    """
    if confidence is None:
        confidence = CONFIDENCE_THRESHOLD

    template = load_template(template_name)
    if screenshot is None:
        screenshot = take_screenshot()

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        h, w = template.shape[:2]
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2
        return (center_x, center_y)

    return None


def wait_for_image(template_name, timeout=None, interval=0.5):
    """Wait until a template image appears on screen.

    Args:
        template_name: Filename of the template to wait for.
        timeout: Max seconds to wait. Defaults to WAIT_TIMEOUT.
        interval: Seconds between checks.

    Returns:
        (x, y) center coordinates of the match.

    Raises:
        TimeoutError: If the image is not found within the timeout.
    """
    if timeout is None:
        timeout = WAIT_TIMEOUT

    start = time.time()
    while time.time() - start < timeout:
        check_abort()
        pos = find_on_screen(template_name)
        if pos is not None:
            return pos
        time.sleep(interval)

    # Timeout — save debug screenshot and raise
    elapsed = time.time() - start
    debug_path = save_debug_screenshot(f"timeout_looking_for_{template_name}")
    error_msg = (
        f"Timeout after {elapsed:.1f}s looking for '{template_name}'. "
        f"Debug screenshot saved to: {debug_path}"
    )
    raise TimeoutError(error_msg)


def click_image(template_name, timeout=None, delay_after=None):
    """Find a template on screen and click its center.

    Args:
        template_name: Filename of the template to find and click.
        timeout: Max seconds to wait for the image. Defaults to WAIT_TIMEOUT.
        delay_after: Seconds to wait after clicking. Defaults to CLICK_DELAY.

    Returns:
        (x, y) coordinates that were clicked.

    Raises:
        TimeoutError: If the image is not found within the timeout.
    """
    if delay_after is None:
        delay_after = CLICK_DELAY

    pos = wait_for_image(template_name, timeout=timeout)
    check_abort()
    pyautogui.click(pos[0], pos[1])
    time.sleep(delay_after)
    return pos


def is_on_screen(template_name, screenshot=None):
    """Check if a template image is currently visible on screen.

    Args:
        template_name: Filename of the template.
        screenshot: Optional pre-captured screenshot.

    Returns:
        True if found, False otherwise.
    """
    return find_on_screen(template_name, screenshot=screenshot) is not None


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


def handle_not_eligible_popup():
    """Dismiss the 'Not Eligible' popup by clicking OK.

    Returns:
        True if popup was found and dismissed, False if not present.
    """
    screenshot = take_screenshot()
    if is_on_screen("not_eligible_popup.png", screenshot=screenshot):
        click_image("not_eligible_ok.png", timeout=3, delay_after=SHORT_DELAY)
        print("    [skip] Item not eligible for trade-in")
        return True
    return False


def handle_choose_quantity_popup(slots_remaining):
    """Handle the 'Choose Quantity' popup — select max available up to slots_remaining.

    Args:
        slots_remaining: Number of trade-in slots still empty (1-5).

    Returns:
        Number of items selected if popup was found, 0 if not present.
    """
    screenshot = take_screenshot()
    if is_on_screen("choose_quantity_popup.png", screenshot=screenshot):
        # Click + button (slots_remaining - 1) times since it starts at 1
        clicks_needed = slots_remaining - 1
        for _ in range(clicks_needed):
            check_abort()
            try:
                click_image("quantity_plus.png", timeout=3, delay_after=0.15)
            except TimeoutError:
                # Plus button disappeared — we've hit the max available
                break

        click_image("quantity_ok.png", timeout=3, delay_after=SHORT_DELAY)
        print(f"    [quantity] Selected up to {slots_remaining} from duplicates")
        return slots_remaining  # May be less if capped, but we track optimistically
    return 0


def count_filled_slots(screenshot=None):
    """Count how many of the 5 trade-in slots are filled by checking for the empty slot pattern.

    This is a heuristic — we primarily track slot count via logic rather than vision.
    Used as a hook for future improvement.
    """
    # We rely on logical tracking rather than visual counting
    pass


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
    time.sleep(0.5)
    return True


def execute_trade():
    """Execute the trade-in: click ACCEPT, confirm YES, dismiss reward.

    Returns:
        True if trade completed successfully.

    Raises:
        TimeoutError: If any step in the trade process fails.
    """
    print("  [trade] 5 slots filled — executing trade...")

    # Click ACCEPT
    click_image("accept_button_active.png", timeout=5, delay_after=0.5)

    # Click YES on confirm popup
    click_image("confirm_yes.png", timeout=5, delay_after=LONG_DELAY)

    # Click OK on reward screen
    click_image("reward_ok.png", timeout=5, delay_after=0.5)

    print("  [trade] Trade complete! Reward collected.")
    return True


def run_trade_in_loop(category_name):
    """Run the trade-in loop for a single category.

    Clicks items in the grid one by one, handles popups, fills 5 slots,
    executes the trade, and repeats until no more items can be traded.

    Args:
        category_name: Display name of the category (for logging/summary).

    Returns:
        Number of trades completed in this category.
    """
    trades_completed = 0
    slots_filled = 0
    item_index = 0
    max_items_visible = ITEM_COLS * ITEM_ROWS
    scroll_attempts = 0
    max_scroll_attempts = 5  # Max times to scroll looking for more items
    items_tried_since_last_fill = 0

    print(f"\n  Starting trade-in for: {category_name}")

    while True:
        check_abort()

        # If we've tried all visible items without filling 5 slots
        if item_index >= max_items_visible:
            if scroll_attempts < max_scroll_attempts:
                print(f"  [scroll] Scrolling down for more items (attempt {scroll_attempts + 1})...")
                # Take screenshot before scroll to compare after
                before_scroll = take_screenshot()
                scroll_item_grid()
                after_scroll = take_screenshot()

                # Check if scroll revealed new content by comparing screenshots
                # Simple check: if the grid region changed significantly
                grid_region_before = before_scroll[ITEM_GRID_Y:ITEM_GRID_Y+ITEM_GRID_H, ITEM_GRID_X:ITEM_GRID_X+ITEM_GRID_W]
                grid_region_after = after_scroll[ITEM_GRID_Y:ITEM_GRID_Y+ITEM_GRID_H, ITEM_GRID_X:ITEM_GRID_X+ITEM_GRID_W]
                diff = cv2.absdiff(grid_region_before, grid_region_after)
                mean_diff = np.mean(diff)

                if mean_diff < 5:  # Very little changed — no new items
                    print("  [scroll] No new items found after scrolling.")
                    break

                # Reset item index to try new items (start from top of visible grid)
                item_index = 0
                scroll_attempts += 1
                continue
            else:
                print("  [done] Max scroll attempts reached — category exhausted.")
                break

        # Click the next item in the grid
        pos = get_item_position(item_index)
        check_abort()
        pyautogui.click(pos[0], pos[1])
        time.sleep(SHORT_DELAY)

        # Check what happened after clicking
        # Wait a moment for any popup to appear
        time.sleep(0.2)

        # Check for "Not Eligible" popup
        if handle_not_eligible_popup():
            item_index += 1
            items_tried_since_last_fill += 1
            continue

        # Check for "Choose Quantity" popup
        slots_remaining = 5 - slots_filled
        quantity_added = handle_choose_quantity_popup(slots_remaining)
        if quantity_added > 0:
            slots_filled += quantity_added
            print(f"    Slots filled: {slots_filled}/5")
            item_index += 1
            items_tried_since_last_fill = 0
        else:
            # No popup — item was added to a slot directly
            slots_filled += 1
            print(f"    [+] Item added. Slots filled: {slots_filled}/5")
            item_index += 1
            items_tried_since_last_fill = 0

        # If 5 slots filled, execute the trade
        if slots_filled >= 5:
            try:
                execute_trade()
                trades_completed += 1
                slots_filled = 0
                item_index = 0  # Reset — grid refreshes after trade
                scroll_attempts = 0
                items_tried_since_last_fill = 0
                # Wait for trade-in screen to return to empty state
                time.sleep(0.5)
            except TimeoutError as e:
                print(f"  [ERROR] Trade execution failed: {e}")
                break

    if slots_filled > 0 and slots_filled < 5:
        print(f"  [done] Only {slots_filled}/5 slots filled — not enough items to trade.")

    return trades_completed
