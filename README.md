# Rocket League Trade-In Helper

Automates Rocket League's reward drops and item trade-ins using screen capture
and template matching. The bot starts from the game's main menu, navigates
itself, opens every drop, then trades in items across all categories.

## What it does

- Navigates itself from the **main menu**:
  `GARAGE > MANAGE INVENTORY > REWARD ITEMS` to open drops, then
  `GARAGE > TRADE IN` for the trade-in loop
- Opens every drop on the REWARD ITEMS tab, stack by stack
- Iterates through all category cards: Core Items, Tournament Items, Blueprints
- Clicks items in the grid to fill 5 trade-in slots
- Handles popups: "Not Eligible", "Choose Quantity" (selects max available),
  "Too Many Items", "ERROR - Inventory out of sync"
- Executes trades: ACCEPT > Confirm YES > Collect reward
- Skips categories that are dimmed out (fewer than 5 items of that quality)
- Sweeps every category repeatedly: each trade returns a higher-quality item,
  which can push another category over the five-item line. Stops when a full
  sweep trades nothing
- Recovers from being left on an unexpected screen by an earlier run
- Writes a timestamped log of every action, and a summary on completion or abort

## Requirements

- Python 3.8+
- Windows
- Rocket League running at **2560x1440** (1440p)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Open Rocket League. Any of these works as a starting point: main menu, Garage
menu, Manage Inventory, the trade-in screen, or mid-way through a drop.

```bash
python trade_in_bot.py                  # open all drops, then trade in everything
python trade_in_bot.py --mode drops     # only open reward drops
python trade_in_bot.py --mode trade     # only run the trade-in loop
python trade_in_bot.py --mode where     # print which screen the bot thinks it sees
```

On Windows, double-click `start_bot.bat` instead; it passes any flags through
(`start_bot.bat --mode trade`).

| Flag | Effect |
|---|---|
| `--dry-run` | Navigates and fills slots but never clicks ACCEPT / YES / OPEN DROP |
| `--trace` | Saves a labelled screenshot at each step to `debug/trace/` |
| `--max-drops N` | Stop after opening N drops |
| `--max-passes N` | Cap on trade-in sweeps (default 5) |
| `--full-scan` | Search the whole screen per template instead of the known regions |
| `--no-focus` | Never touch window focus |
| `--no-countdown` | Skip the 3 second countdown |

Press **Escape** at any time to abort. Escape is reserved for that, so the bot
never uses it to go back — every "back" step clicks the on-screen BACK button.

The bot pulls the Rocket League window to the front and keeps it there. Anything
covering the game breaks it twice over: clicks land on the wrong window, and
template matching reads the wrong pixels. Don't alt-tab while it runs.

## Run logs

Every run writes to `debug/runs/<date>_<time>.log`, recording each click, screen
transition and wait with a wall-clock time and an offset from the run start:

```
01:39:52.104 +   5.31s        . click (207, 1217) drop_open_button.png
01:39:53.286 +   6.49s        . click (1535, 1062) drop_reveal_ok.png
01:39:53.640 +   6.85s    [drops] Opened 4
```

Debug screenshots land in `debug/` with matching timestamps, so a failure can be
lined up with what was on screen at that moment.

## Watching the screen

`screen_watch.py` captures what is on screen into `debug/live/`, which makes it
easy to share exactly what the game is showing when something goes wrong.

```bash
python screen_watch.py snap --name garage_menu       # one screenshot
python screen_watch.py hotkey                        # F9 captures, Escape quits
python screen_watch.py watch --interval 1 --count 30 # record a sequence
python screen_watch.py overlay --layout trade_in     # draw the bot's click targets
python screen_watch.py overlay --layout inventory
python screen_watch.py sheet --dir debug/trace       # tile frames into one image
```

Every capture is also copied to `debug/live/latest.png`, so there is one stable
path to look at. `overlay` is the quickest way to check whether the hardcoded
grid coordinates still line up with the live UI after a game update.

## Speed

Matching one template against the full 2560x1440 screen costs about 200 ms.
`TEMPLATE_REGIONS` in `trade_in_bot.py` pins each template to the box it can
appear in, which brings that to about 4 ms and takes a full screen
identification from ~450 ms down to ~7 ms. Drops open at roughly 33 per minute.

A wrong region makes a template silently undetectable, so every box is checked
against a reference screenshot:

```bash
python validate_regions.py
```

Run it after changing a region or re-cropping a template. `--full-scan` bypasses
the regions if the UI ever moves.

## Working with the game's UI

Four things the game does that the bot has to account for:

- **Clicks during animations are dropped.** After a menu transition, a click
  lands on nothing. Actions that matter are retried until the expected screen
  appears rather than clicked once and hoped for.
- **Buttons change appearance when focused or hovered**, which stops the plain
  template from matching. The cursor is parked on an inert strip after every
  click, and buttons with more than one look get one template per look —
  `click_first()` clicks whichever is showing.
- **Screens are identified by something that never changes.** The reveal is
  detected by its "NEW ITEM" caption, not by its buttons (which differ per
  item); the trade-in screen by its "TRADE IN" panel title, not by the category
  cards (which all dim out once you drop below five items).
- **The category counts are cached.** They are recalculated when the trade-in
  screen is entered, not while you sit on it, so the bot leaves and re-enters
  between passes instead of trusting the numbers it already read.

## Recording a new UI flow

If the game adds a screen the bot does not know:

```bash
python trade_in_bot.py --discover-drops   # record the drop preview flow
python trade_in_bot.py --discover-open    # also click OPEN DROP and record the reveal
```

Frames land in `debug/drop_flow/`. Crop the new button into `templates/`, add its
search box to `TEMPLATE_REGIONS`, add a reference screenshot to
`validate_regions.py`, and re-run the validator.

## Recalibration

If you switch resolution:

1. Take new screenshots of each UI state into `ui-images/`
2. `python crop_templates_interactive.py` to re-select template regions
3. `python validate_grid.py` to adjust the item grid positions
4. `python validate_regions.py` to re-check the search boxes

## Safety

- **Escape** stops the bot after the current action
- **PyAutoGUI failsafe** — moving the mouse to the top-left corner (0,0) aborts
- `--dry-run` exercises the whole flow without trading or opening anything
- Failures are logged with timestamped debug screenshots in `debug/`

## Project structure

```
trade_in_bot.py                  # Main bot script
screen_watch.py                  # Screen capture / overlay / contact-sheet helper
validate_regions.py              # Checks every template search region
crop_templates.py                # Batch template cropper
crop_templates_interactive.py    # Interactive template selection tool
validate_grid.py                 # Item grid position validator/tuner
requirements.txt                 # Python dependencies
templates/                       # Cropped UI element images for matching
ui-images/                       # Full reference screenshots
debug/                           # Logs, traces and failure screenshots (runtime)
```
