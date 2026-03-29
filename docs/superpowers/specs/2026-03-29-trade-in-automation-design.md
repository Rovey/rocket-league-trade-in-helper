# Rocket League Trade-In Automation Script — Design Spec

## Overview

A Python script that automates the Rocket League item trade-in process. It uses screen capture + template matching to navigate the trade-in UI, systematically trading in all eligible items across every category and rarity tier.

## Technology

- **Language:** Python 3
- **Screen capture & mouse control:** PyAutoGUI
- **Image/template matching:** OpenCV (`cv2.matchTemplate`)
- **Keyboard listener (Escape abort):** pynput
- **Additional:** numpy (required by OpenCV)
- **Target resolution:** 2560x1440 (1440p)
- **Platform:** Windows 11

## Project Structure

```
27_rocket-league-trade-in-helper/
  trade_in_bot.py          # Main script
  requirements.txt         # Python dependencies
  templates/               # Cropped UI element images for template matching
    accept_button.png
    confirm_yes.png
    reward_ok.png
    not_eligible_ok.png
    not_eligible_popup.png
    choose_quantity_popup.png
    quantity_plus.png
    quantity_ok.png
    back_button.png
    trade_in_empty_slots.png
    show_filters.png
    card_core_special.png
    card_core_deluxe.png
    card_core_import.png
    card_core_exotic.png
    card_core_black_market.png
    card_tournament_special.png
    card_tournament_deluxe.png
    card_tournament_import.png
    card_tournament_exotic.png
    card_tournament_black_market.png
    card_blueprints_deluxe.png
    card_blueprints_import.png
    card_blueprints_exotic.png
    card_blueprints_black_market.png
  debug/                   # Auto-created, stores failure screenshots
  ui-images/               # Original reference screenshots (already present)
```

## Template Images

Cropped from the existing UI screenshots in `ui-images/`:

| Template | Source | Purpose |
|---|---|---|
| `accept_button.png` | trade in filled.png | Detect & click the ACCEPT button |
| `confirm_yes.png` | trade in accept warning.png | Click YES on confirm trade popup |
| `reward_ok.png` | trade in item reward.png | Click OK on reward screen |
| `not_eligible_ok.png` | trade in warning cannot trade in.png | Click OK on "Not Eligible" popup |
| `not_eligible_popup.png` | trade in warning cannot trade in.png | Detect "NOT ELIGIBLE" header |
| `choose_quantity_popup.png` | trade in choose quantity.png | Detect "CHOOSE QUANTITY" header |
| `quantity_plus.png` | trade in choose quantity.png | Click + button to increase quantity |
| `quantity_ok.png` | trade in choose quantity.png | Click OK on quantity popup |
| `back_button.png` | trade in empty.png | Click BACK button |
| `trade_in_empty_slots.png` | trade in empty.png | Detect empty trade-in screen |
| `show_filters.png` | trade in empty.png | Confirm we're on the trade-in screen |
| Category card templates | main screen.png | One per card across all 3 category rows |

## Core Logic

### Main Loop

1. Start on the main menu trade-in screen.
2. Scan for category cards by template matching. Try each one left-to-right, top-to-bottom: Core Items row first, then Tournament Items, then Blueprints.
3. Click a card. Wait for the trade-in screen (detect via `show_filters.png` or empty slot bar).
4. Run the trade-in loop for that category.
5. When trade-in loop exits (can't fill 5 slots), click BACK to return to main menu.
6. Move to the next category card. Repeat until all categories exhausted.
7. Print summary and exit.

### Trade-In Loop (per category)

1. Track slots filled (start at 0).
2. Click the next item in the grid (left-to-right, top-to-bottom).
3. Wait briefly (~0.3-0.5s) and check what happened:
   - **"Not Eligible" popup** detected → click OK, skip this item, move to next.
   - **"Choose Quantity" popup** detected → click + button repeatedly to set quantity to `min(available, 5 - slots_filled)`, click OK, update slot count.
   - **Neither popup** → item was added to a slot, increment slot count by 1.
4. If slots_filled == 5 → click ACCEPT → click YES on confirm → click OK on reward → reset slots to 0, repeat from step 1.
5. If all visible items exhausted → scroll down in the item grid to reveal more items. If no new items appear, category is done → exit loop.

### Item Grid Navigation

- The item grid occupies a known region of the screen (determined from the screenshots).
- Items are clicked in sequence: left-to-right, top-to-bottom.
- After clicking all visible items, scroll down and continue.
- If scrolling reveals no new items, the category is exhausted.

### Choose Quantity Handling

When the "Choose Quantity" popup appears:
1. Determine how many more slots need filling: `remaining = 5 - slots_filled`.
2. Click the + button `(remaining - 1)` times (popup starts at 1).
3. Click OK.
4. Update `slots_filled += remaining` (or however many were actually selected — may be capped by available count).

Note: If fewer duplicates are available than slots remaining, the + button will stop increasing. The script clicks + the desired number of times regardless; the UI will cap it at the max available.

## Timing

| Action | Delay |
|---|---|
| Between item clicks | 0.3 - 0.5s |
| After dismissing popup (Not Eligible, Quantity) | 0.3 - 0.5s |
| After clicking ACCEPT | 0.5s |
| After clicking YES on confirm | 1.5 - 2s (reward animation) |
| After clicking OK on reward | 0.5s |
| After clicking BACK | 0.5 - 1s |
| After clicking a category card | 0.5 - 1s |

## Safety: Escape Key Abort

- A background thread (via `pynput`) listens for the Escape key at all times.
- When Escape is pressed, a global `abort` flag is set.
- The main loop checks `abort` before every action (every click, every wait).
- On abort: stop immediately, print trade summary, exit cleanly.

## Error Handling

### Stuck Detection

- Every `wait_for_image()` call has a 10-second timeout.
- If no match is found within the timeout, the script treats this as an error.

### Debug Screenshots

- On every failed image match (timeout), a screenshot is saved to `debug/` with a descriptive filename:
  `debug/2026-03-29_14-23-45_looking_for_accept_button.png`
- The error message printed to console includes:
  - What template it was trying to match
  - How long it waited
  - The path to the saved debug screenshot
- Debug screenshots accumulate across the run so the full failure history can be reviewed.

### Graceful Exit on Error

- On any unrecoverable error, the script saves a debug screenshot, prints the error with context, prints the trade summary so far, and exits.

## Trade Summary

On exit (normal completion or abort), the script prints:

```
Trade-in complete!
Core Items - Special: 2 trades
Core Items - Deluxe: 1 trade
Blueprints - Import: 3 trades
Total: 6 trades (30 items consumed)
```

## Dependencies (requirements.txt)

```
pyautogui
opencv-python
numpy
pynput
```
