# Rocket League Trade-In Helper

Automates the Rocket League item trade-in process using screen capture and template matching. The bot navigates the trade-in UI, selects items, fills 5 slots, confirms trades, and repeats across all item categories.

## What it does

- Iterates through all category cards: Core Items, Tournament Items, and Blueprints (all rarities)
- Clicks items in the grid to fill 5 trade-in slots
- Handles popups: "Not Eligible", "Choose Quantity" (selects max available), "Too Many Items", "ERROR - Inventory out of sync"
- Executes trades: ACCEPT > Confirm YES > Collect reward
- Detects when a category is complete (game auto-returns to main menu)
- Skips categories with fewer than 5 items
- Prints a trade summary on completion or abort

## Requirements

- Python 3.8+
- Windows (uses PyAutoGUI screen capture)
- Rocket League running at **2560x1440** (1440p)

## Setup

```bash
pip install -r requirements.txt
```

If this is your first time or you changed resolution, calibrate the templates:

```bash
# Crop UI element templates from your screenshots (interactive — draw rectangles)
python crop_templates_interactive.py

# Verify item grid positions overlay correctly on the trade-in screen
python validate_grid.py
```

## Usage

1. Open Rocket League and navigate to the **Trade-In main menu** screen
2. Run the bot:

```bash
python trade_in_bot.py
```

3. You have 3 seconds to switch to the game window
4. Press **Escape** at any time to abort safely

The bot will work through each category and print a summary when done:

```
Trade-in Summary:
  Core Items - Special: 4 trades
  Core Items - Deluxe: 2 trades
  Core Items - Import: 4 trades
  Blueprints - Deluxe: 3 trades
  Total: 13 trades (65 items consumed)
```

## Safety

- **Escape key** stops the bot after the current action
- **PyAutoGUI failsafe** — moving your mouse to the top-left corner of the screen (0,0) will also abort
- All failures are logged with timestamped debug screenshots in the `debug/` folder
- The bot never does anything destructive — worst case it clicks in the wrong spot and nothing happens

## Recalibration

If the game UI changes or you switch resolution:

1. Take new screenshots of each UI state and place them in `ui-images/`
2. Run `python crop_templates_interactive.py` to re-select all template regions
3. Run `python validate_grid.py` to adjust the item grid positions
4. Both tools save their results directly — no manual coordinate editing needed

## Project structure

```
trade_in_bot.py                  # Main bot script
crop_templates.py                # Batch template cropper (auto-generated)
crop_templates_interactive.py    # Interactive template selection tool
validate_grid.py                 # Item grid position validator/tuner
requirements.txt                 # Python dependencies
templates/                       # Cropped UI element images for matching
ui-images/                       # Full reference screenshots
debug/                           # Failure screenshots (auto-created at runtime)
```
