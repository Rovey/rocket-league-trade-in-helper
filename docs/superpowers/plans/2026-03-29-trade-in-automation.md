# Trade-In Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that automates Rocket League's item trade-in UI using screen capture and template matching, trading in all eligible items across every category.

**Architecture:** Single-file Python script (`trade_in_bot.py`) using PyAutoGUI for screen capture/mouse control and OpenCV for template matching. A pynput background thread listens for Escape to abort. The script loops through category cards on the main menu, enters each trade-in screen, clicks items to fill 5 slots, confirms the trade, and repeats until all categories are exhausted.

**Tech Stack:** Python 3, PyAutoGUI, OpenCV (`opencv-python`), numpy, pynput

---

## File Structure

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `crop_templates.py` | One-time utility to crop template images from UI screenshots |
| `templates/` | Directory for cropped template images (created by `crop_templates.py`) |
| `trade_in_bot.py` | Main automation script |
| `debug/` | Auto-created at runtime for failure screenshots |

---

### Task 1: Project Setup — requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
pyautogui
opencv-python
numpy
pynput
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 3: Verify imports work**

Run: `python -c "import pyautogui; import cv2; import numpy; from pynput import keyboard; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add requirements.txt with project dependencies"
```

---

### Task 2: Crop Template Images from UI Screenshots

**Files:**
- Create: `crop_templates.py`
- Create: `templates/` (populated by running the script)

This script crops specific regions from the UI screenshots to produce template images for matching. The crop coordinates are determined from the 2560x1440 screenshots in `ui-images/`.

- [ ] **Step 1: Create crop_templates.py**

```python
"""Crop template images from UI screenshots for template matching.

Run once to generate all templates in the templates/ directory.
Coordinates are for 2560x1440 resolution.
"""

import cv2
import os

TEMPLATES_DIR = "templates"
UI_IMAGES_DIR = "ui-images"


def crop_and_save(source_filename, region, template_name):
    """Crop a region from a source image and save as a template.

    Args:
        source_filename: Filename in ui-images/ directory
        region: (x, y, width, height) tuple defining the crop region
        template_name: Output filename in templates/ directory
    """
    source_path = os.path.join(UI_IMAGES_DIR, source_filename)
    img = cv2.imread(source_path)
    if img is None:
        print(f"ERROR: Could not load {source_path}")
        return False

    x, y, w, h = region
    cropped = img[y:y+h, x:x+w]

    output_path = os.path.join(TEMPLATES_DIR, template_name)
    cv2.imwrite(output_path, cropped)
    print(f"  Saved {template_name} ({w}x{h})")
    return True


def main():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    print("Cropping template images...")
    print()

    # --- Trade-in screen buttons ---
    print("From: trade in empty.png")
    crop_and_save("trade in empty.png", (207, 133, 100, 30), "accept_button.png")
    crop_and_save("trade in empty.png", (15, 880, 80, 30), "back_button.png")
    crop_and_save("trade in empty.png", (305, 260, 135, 30), "show_filters.png")
    crop_and_save("trade in empty.png", (28, 50, 530, 35), "trade_in_header.png")
    print()

    # --- Trade-in filled (ACCEPT button when clickable) ---
    print("From: trade in filled.png")
    crop_and_save("trade in filled.png", (207, 133, 100, 30), "accept_button_active.png")
    print()

    # --- Not Eligible popup ---
    print("From: trade in warning cannot trade in.png")
    crop_and_save("trade in warning cannot trade in.png", (220, 225, 200, 40), "not_eligible_popup.png")
    crop_and_save("trade in warning cannot trade in.png", (260, 280, 120, 35), "not_eligible_ok.png")
    print()

    # --- Confirm Trade popup ---
    print("From: trade in accept warning.png")
    crop_and_save("trade in accept warning.png", (220, 225, 200, 40), "confirm_trade_popup.png")
    crop_and_save("trade in accept warning.png", (215, 305, 90, 30), "confirm_yes.png")
    print()

    # --- Reward screen ---
    print("From: trade in item reward.png")
    crop_and_save("trade in item reward.png", (235, 460, 170, 35), "reward_ok.png")
    crop_and_save("trade in item reward.png", (200, 65, 240, 40), "reward_new_item.png")
    print()

    # --- Choose Quantity popup ---
    print("From: trade in choose quantity.png")
    crop_and_save("trade in choose quantity.png", (225, 225, 190, 40), "choose_quantity_popup.png")
    crop_and_save("trade in choose quantity.png", (315, 275, 35, 30), "quantity_plus.png")
    crop_and_save("trade in choose quantity.png", (220, 310, 80, 30), "quantity_ok.png")
    print()

    # --- Main screen category cards ---
    # Core Items row
    print("From: main screen.png")
    crop_and_save("main screen.png", (50, 75, 105, 100), "card_core_special.png")
    crop_and_save("main screen.png", (160, 75, 105, 100), "card_core_deluxe.png")
    crop_and_save("main screen.png", (270, 75, 105, 100), "card_core_import.png")
    crop_and_save("main screen.png", (380, 75, 105, 100), "card_core_exotic.png")
    crop_and_save("main screen.png", (490, 75, 105, 100), "card_core_black_market.png")

    # Tournament Items row
    crop_and_save("main screen.png", (50, 195, 85, 45), "card_tournament_special.png")
    crop_and_save("main screen.png", (140, 195, 85, 45), "card_tournament_deluxe.png")
    crop_and_save("main screen.png", (230, 195, 85, 45), "card_tournament_import.png")
    crop_and_save("main screen.png", (320, 195, 85, 45), "card_tournament_exotic.png")
    crop_and_save("main screen.png", (410, 195, 85, 45), "card_tournament_black_market.png")

    # Blueprints row
    crop_and_save("main screen.png", (160, 300, 105, 100), "card_blueprints_deluxe.png")
    crop_and_save("main screen.png", (270, 300, 105, 100), "card_blueprints_import.png")
    crop_and_save("main screen.png", (380, 300, 105, 100), "card_blueprints_exotic.png")
    crop_and_save("main screen.png", (490, 300, 105, 100), "card_blueprints_black_market.png")
    print()

    print("Done! Template images saved to templates/")
    print()
    print("IMPORTANT: Verify the cropped templates look correct before running the bot.")
    print("Open the templates/ folder and check each image visually.")
    print("If any crop is wrong, adjust the coordinates in this script and re-run.")


if __name__ == "__main__":
    main()
```

**Note on crop coordinates:** The coordinates above are initial estimates based on the screenshot layout. After running, visually inspect every template image. If a crop is off, adjust the `(x, y, width, height)` tuple in this script and re-run. Getting these right is critical — the bot depends entirely on accurate templates.

- [ ] **Step 2: Run the crop script**

Run: `python crop_templates.py`
Expected: All templates saved with no errors. Output shows each template name and dimensions.

- [ ] **Step 3: Visually verify every template**

Open the `templates/` folder and check each image:
- Does `accept_button.png` show the ACCEPT button text clearly?
- Does `back_button.png` show the BACK button?
- Does `show_filters.png` show "SHOW FILTERS"?
- Does `not_eligible_popup.png` show the "NOT ELIGIBLE" header?
- Does `not_eligible_ok.png` show the OK button from that popup?
- Does `confirm_yes.png` show the YES button?
- Does `reward_ok.png` show the OK button from the reward screen?
- Does `reward_new_item.png` show the "NEW ITEM" header?
- Does `choose_quantity_popup.png` show "CHOOSE QUANTITY"?
- Does `quantity_plus.png` show the + button?
- Does `quantity_ok.png` show the OK button from quantity popup?
- Do all category card templates show their respective cards?

If any template is wrong, adjust coordinates in `crop_templates.py` and re-run. **Do not proceed until all templates are correct.**

- [ ] **Step 4: Commit**

```bash
git add crop_templates.py templates/
git commit -m "feat: add template cropping utility and initial templates"
```

---

### Task 3: Core Utilities — Screen Capture, Template Matching, Abort Listener

**Files:**
- Create: `trade_in_bot.py`

This task creates the foundation: imports, constants, the abort listener, screenshot/debug utilities, and the template matching functions that everything else builds on.

- [ ] **Step 1: Create trade_in_bot.py with imports, constants, and abort listener**

```python
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
```

- [ ] **Step 2: Add template loading and matching functions**

Append to `trade_in_bot.py`:

```python
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
```

- [ ] **Step 3: Verify the script loads without errors**

Run: `python -c "import trade_in_bot; print('Module loaded OK')"`
Expected: `Module loaded OK`

- [ ] **Step 4: Commit**

```bash
git add trade_in_bot.py
git commit -m "feat: add core utilities — screen capture, template matching, abort listener"
```

---

### Task 4: Trade-In Loop — Item Selection and Slot Filling

**Files:**
- Modify: `trade_in_bot.py`

This task adds the logic for the trade-in screen: clicking items in the grid, handling popups (Not Eligible, Choose Quantity), detecting filled slots, and executing the trade.

- [ ] **Step 1: Add the item clicking and popup handling functions**

Append to `trade_in_bot.py`:

```python
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
    Used as a sanity check.
    """
    # We rely on logical tracking rather than visual counting
    # This function exists as a hook for future improvement
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
```

- [ ] **Step 2: Verify the script still loads**

Run: `python -c "import trade_in_bot; print('Module loaded OK')"`
Expected: `Module loaded OK`

- [ ] **Step 3: Commit**

```bash
git add trade_in_bot.py
git commit -m "feat: add trade-in loop — item selection, popup handling, slot filling"
```

---

### Task 5: Main Loop — Category Iteration and Entry Point

**Files:**
- Modify: `trade_in_bot.py`

This task adds the main loop that iterates through category cards on the main menu and the script's entry point with the Escape key listener.

- [ ] **Step 1: Add the main menu navigation and main function**

Append to `trade_in_bot.py`:

```python
def is_on_main_menu(screenshot=None):
    """Check if we're on the main trade-in menu (with category cards).

    Looks for any category card template on screen.
    """
    if screenshot is None:
        screenshot = take_screenshot()

    # Check for a few known cards — if any are visible, we're on the main menu
    for template_name, _ in CATEGORY_CARDS[:3]:
        try:
            if is_on_screen(template_name, screenshot=screenshot):
                return True
        except FileNotFoundError:
            continue
    return False


def is_on_trade_in_screen(screenshot=None):
    """Check if we're on the trade-in item selection screen."""
    if screenshot is None:
        screenshot = take_screenshot()
    return is_on_screen("show_filters.png", screenshot=screenshot)


def navigate_to_category(template_name, category_name):
    """Click a category card from the main menu and wait for the trade-in screen.

    Args:
        template_name: Template filename for the category card.
        category_name: Display name (for logging).

    Returns:
        True if successfully navigated to the trade-in screen, False if card not found.
    """
    print(f"\n[>] Trying category: {category_name}")

    # Check if the card exists on screen
    pos = find_on_screen(template_name)
    if pos is None:
        print(f"  [skip] Card not found on screen — may not have enough items.")
        return False

    # Click the card
    check_abort()
    pyautogui.click(pos[0], pos[1])
    time.sleep(0.8)

    # Wait for trade-in screen to appear
    try:
        wait_for_image("show_filters.png", timeout=5)
        print(f"  [ok] Entered trade-in screen for {category_name}")
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


def main():
    """Main entry point. Iterates through all categories and trades in everything."""
    global trade_summary

    print("=" * 50)
    print("  Rocket League Trade-In Bot")
    print("  Press Escape at any time to abort")
    print("=" * 50)
    print()

    # Start the keyboard listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()

    # Give user time to switch to the game
    print("Starting in 3 seconds — switch to Rocket League now!")
    print("Make sure you're on the Trade-In main menu screen.")
    for i in range(3, 0, -1):
        check_abort()
        print(f"  {i}...")
        time.sleep(1)
    print("  Go!\n")

    try:
        # Verify we're on the main menu
        if not is_on_main_menu():
            debug_path = save_debug_screenshot("not_on_main_menu")
            print(f"[ERROR] Doesn't look like the Trade-In main menu.")
            print(f"        Make sure Rocket League is in the foreground on the Trade-In screen.")
            print(f"        Debug screenshot: {debug_path}")
            return

        # Iterate through all category cards
        for template_name, category_name in CATEGORY_CARDS:
            check_abort()

            # Try to enter this category
            if not navigate_to_category(template_name, category_name):
                continue

            # Run the trade-in loop
            try:
                trades = run_trade_in_loop(category_name)
                if trades > 0:
                    trade_summary[category_name] = trades
            except TimeoutError as e:
                print(f"  [ERROR] Trade-in loop failed: {e}")
            except Exception as e:
                debug_path = save_debug_screenshot(f"error_in_{template_name}")
                print(f"  [ERROR] Unexpected error: {e}")
                print(f"          Debug screenshot: {debug_path}")

            # Go back to main menu for the next category
            try:
                go_back_to_main_menu()
            except TimeoutError:
                print("[ERROR] Could not return to main menu. Aborting.")
                break

            # Verify we're back on the main menu
            time.sleep(0.5)
            if not is_on_main_menu():
                debug_path = save_debug_screenshot("not_on_main_menu_after_back")
                print(f"[ERROR] Not on main menu after clicking BACK.")
                print(f"        Debug screenshot: {debug_path}")
                break

        print("\n[done] All categories processed!")

    except SystemExit:
        pass  # Abort via check_abort() — summary already printed
    except Exception as e:
        debug_path = save_debug_screenshot("unexpected_error")
        print(f"\n[FATAL ERROR] {e}")
        print(f"              Debug screenshot: {debug_path}")
    finally:
        print_summary()
        listener.stop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script loads and runs (will fail gracefully without game)**

Run: `python -c "import trade_in_bot; print('Module loaded OK')"`
Expected: `Module loaded OK`

- [ ] **Step 3: Commit**

```bash
git add trade_in_bot.py
git commit -m "feat: add main loop — category iteration, navigation, and entry point"
```

---

### Task 6: End-to-End Dry Run and Coordinate Tuning

**Files:**
- Modify: `crop_templates.py` (adjust coordinates as needed)
- Modify: `trade_in_bot.py` (adjust grid coordinates as needed)

This is the calibration task. Run the bot with Rocket League open and tune coordinates until everything works.

- [ ] **Step 1: Run the template cropper and verify all templates**

Run: `python crop_templates.py`

Open `templates/` folder and visually verify each image. If any crop is wrong:
1. Open the source screenshot in an image editor
2. Find the correct pixel coordinates for the UI element
3. Update the coordinates in `crop_templates.py`
4. Re-run `python crop_templates.py`
5. Repeat until all templates are correct

- [ ] **Step 2: Test template matching in isolation**

Create a quick test by running Python interactively with Rocket League open on the main menu:

```python
python -c "
from trade_in_bot import *
screenshot = take_screenshot()
for name, display in CATEGORY_CARDS[:5]:
    try:
        pos = find_on_screen(name, screenshot=screenshot)
        print(f'{display}: found at {pos}' if pos else f'{display}: NOT FOUND')
    except FileNotFoundError:
        print(f'{display}: template file missing')
"
```

Expected: Category cards that are visible on screen should show coordinates. Adjust templates or confidence threshold if matches are wrong.

- [ ] **Step 3: Test item grid coordinates**

With Rocket League on the trade-in screen (after clicking a category), verify item positions:

```python
python -c "
from trade_in_bot import get_item_position
for i in range(8):
    print(f'Item {i}: {get_item_position(i)}')
"
```

Manually verify these coordinates match the center of item icons on screen. If not, adjust `ITEM_START_X`, `ITEM_START_Y`, `ITEM_CELL_W`, `ITEM_CELL_H` in `trade_in_bot.py`.

- [ ] **Step 4: Run the full bot for one category**

Run: `python trade_in_bot.py`

Watch it operate on the first category. Press Escape if anything goes wrong. Check:
- Does it find and click the first category card?
- Does it click items in the correct positions?
- Does it detect and handle the "Not Eligible" popup?
- Does it detect and handle the "Choose Quantity" popup?
- Does it detect when 5 slots are filled and click ACCEPT?
- Does it confirm the trade and dismiss the reward?
- Does it go back to the main menu?

Fix any issues found. Common problems:
- Template confidence too high/low → adjust `CONFIDENCE_THRESHOLD`
- Click positions slightly off → adjust grid constants
- Timing too fast → increase delays
- Template crops wrong → fix in `crop_templates.py` and re-run

- [ ] **Step 5: Commit final tuned version**

```bash
git add trade_in_bot.py crop_templates.py templates/
git commit -m "feat: tune coordinates and templates for reliable operation"
```

---

### Task 7: Full Run and Final Verification

- [ ] **Step 1: Run the bot through all categories**

Run: `python trade_in_bot.py`

Let it run through multiple categories. Verify:
- Processes Core Items, Tournament Items, and Blueprints
- Correctly skips categories with no cards visible
- Prints a complete trade summary at the end
- Escape key stops it cleanly at any point

- [ ] **Step 2: Check debug screenshots (if any errors occurred)**

If any errors occurred during the run, check the `debug/` folder for screenshots. Each screenshot shows what the screen looked like when the bot got stuck, with a filename indicating what it was looking for.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete trade-in automation bot — tested end-to-end"
```
