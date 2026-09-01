"""Screen capture helper — lets an assistant "look over your shoulder".

Writes screenshots to `debug/live/` so they can be opened and inspected while
you walk through the Rocket League UI. Every capture is also copied to
`debug/live/latest.png`, so there is always one stable path to look at.

Modes:
    snap      Take one screenshot right now.
    hotkey    Stay running; F9 captures, F10 captures + labels, Escape quits.
    watch     Capture on a fixed interval for a set number of frames.
    overlay   Screenshot with the bot's click targets drawn on top.

Examples:
    python screen_watch.py snap --name garage_menu
    python screen_watch.py hotkey
    python screen_watch.py watch --interval 1.0 --count 30 --name trade_run
    python screen_watch.py overlay --layout trade_in
    python screen_watch.py snap --region 0,0,1400,300 --name tab_bar
"""

import argparse
import os
import shutil
import sys
import time
from datetime import datetime

import cv2
import numpy as np
import pyautogui

LIVE_DIR = os.path.join("debug", "live")
LATEST = os.path.join(LIVE_DIR, "latest.png")


def ensure_live_dir():
    os.makedirs(LIVE_DIR, exist_ok=True)


def grab(region=None):
    """Capture the screen (or a region) as a BGR numpy array.

    Args:
        region: Optional (x, y, w, h) tuple to crop to.
    """
    shot = pyautogui.screenshot()
    frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
    if region is not None:
        x, y, w, h = region
        frame = frame[y:y + h, x:x + w]
    return frame


def save(frame, name="snap", scale=1.0):
    """Write a frame to debug/live/ and refresh latest.png.

    Returns the timestamped path.
    """
    ensure_live_dir()
    if scale != 1.0:
        frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    stamp = datetime.now().strftime("%H-%M-%S")
    safe = name.replace(" ", "_").replace("/", "_")
    path = os.path.join(LIVE_DIR, f"{stamp}_{safe}.png")
    cv2.imwrite(path, frame)
    shutil.copyfile(path, LATEST)
    return path


def parse_region(text):
    """Parse an 'x,y,w,h' string into a tuple of ints."""
    if text is None:
        return None
    parts = [int(p.strip()) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--region needs exactly 4 numbers: x,y,w,h")
    return tuple(parts)


# --- Overlay layouts ---------------------------------------------------------
# Each layout is a list of shapes the bot uses, so you can see at a glance
# whether the hardcoded coordinates still line up with the live UI.

def draw_label(frame, text, x, y, color):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)


def overlay_trade_in(frame):
    """Draw the trade-in screen's item grid and 5 slot detection regions."""
    import trade_in_bot as bot

    green, yellow, red = (0, 255, 0), (0, 255, 255), (0, 0, 255)

    cv2.rectangle(
        frame,
        (bot.ITEM_GRID_X, bot.ITEM_GRID_Y),
        (bot.ITEM_GRID_X + bot.ITEM_GRID_W, bot.ITEM_GRID_Y + bot.ITEM_GRID_H),
        yellow, 2)
    draw_label(frame, "ITEM_GRID", bot.ITEM_GRID_X + 6, bot.ITEM_GRID_Y - 8, yellow)

    for i in range(bot.ITEM_COLS * bot.ITEM_ROWS):
        x, y = bot.get_item_position(i)
        cv2.circle(frame, (x, y), 6, green, -1)
        draw_label(frame, str(i), x + 10, y - 8, green)

    for idx, cx in enumerate([453, 717, 980, 1244, 1507]):
        cv2.rectangle(frame, (cx - 100, 230), (cx + 100, 420), red, 2)
        draw_label(frame, f"slot{idx}", cx - 90, 222, red)

    return frame


def overlay_inventory(frame):
    """Draw the Manage Inventory tab bar and item grid targets."""
    import trade_in_bot as bot

    cyan, green = (255, 255, 0), (0, 255, 0)

    x, y, w, h = bot.INV_TAB_SEARCH_REGION
    cv2.rectangle(frame, (x, y), (x + w, y + h), cyan, 2)
    draw_label(frame, "TAB_SEARCH_REGION", x + 6, y - 8, cyan)

    for i in range(bot.INV_COLS * bot.INV_ROWS):
        px, py = bot.get_inventory_position(i)
        cv2.circle(frame, (px, py), 6, green, -1)
        draw_label(frame, str(i), px + 10, py - 8, green)

    return frame


OVERLAYS = {
    "trade_in": overlay_trade_in,
    "inventory": overlay_inventory,
}


# --- Modes -------------------------------------------------------------------

def mode_snap(args):
    frame = grab(parse_region(args.region))
    path = save(frame, args.name, args.scale)
    print(f"saved {path}")
    print(f"latest {LATEST}")


def mode_overlay(args):
    frame = grab()
    frame = OVERLAYS[args.layout](frame)
    path = save(frame, f"overlay_{args.layout}", args.scale)
    print(f"saved {path}")
    print(f"latest {LATEST}")


def mode_watch(args):
    region = parse_region(args.region)
    print(f"capturing {args.count} frames every {args.interval}s — Ctrl+C to stop")
    try:
        for i in range(args.count):
            path = save(grab(region), f"{args.name}_{i:03d}", args.scale)
            print(f"  [{i + 1}/{args.count}] {path}")
            if i < args.count - 1:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")


def mode_hotkey(args):
    from pynput import keyboard

    region = parse_region(args.region)
    counter = {"n": 0}
    print("hotkey mode active — switch to Rocket League")
    print("  F9     capture")
    print("  F10    capture, then type a label in this terminal")
    print("  Esc    quit")

    def snap(label=None):
        counter["n"] += 1
        name = label or f"{args.name}_{counter['n']:03d}"
        path = save(grab(region), name, args.scale)
        print(f"  captured -> {path}")

    def on_press(key):
        if key == keyboard.Key.f9:
            snap()
        elif key == keyboard.Key.f10:
            snap()
            print("  (label it by renaming the file, or use --name next run)")
        elif key == keyboard.Key.esc:
            print("quit")
            return False

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


def mode_sheet(args):
    """Tile a directory of captures into one contact sheet image."""
    import glob

    paths = sorted(glob.glob(os.path.join(args.dir, "*.png")))
    paths = [p for p in paths if os.path.basename(p) != "sheet.png"]
    if args.last:
        paths = paths[-args.last:]
    if not paths:
        print(f"no PNGs in {args.dir}")
        return

    cols = args.cols
    thumb_w = args.width
    tiles = []
    for path in paths:
        img = cv2.imread(path)
        if img is None:
            continue
        h, w = img.shape[:2]
        thumb = cv2.resize(img, (thumb_w, int(h * thumb_w / w)), interpolation=cv2.INTER_AREA)
        label = np.full((26, thumb_w, 3), 30, np.uint8)
        cv2.putText(label, os.path.basename(path)[:60], (4, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        tiles.append(np.vstack([label, thumb]))

    tile_h = max(t.shape[0] for t in tiles)
    rows = []
    for i in range(0, len(tiles), cols):
        chunk = tiles[i:i + cols]
        padded = []
        for t in chunk:
            pad = np.full((tile_h, thumb_w, 3), 30, np.uint8)
            pad[:t.shape[0]] = t
            padded.append(pad)
        while len(padded) < cols:
            padded.append(np.full((tile_h, thumb_w, 3), 30, np.uint8))
        rows.append(np.hstack(padded))

    sheet = np.vstack(rows)
    out = args.out or os.path.join(args.dir, "sheet.png")
    cv2.imwrite(out, sheet)
    print(f"{len(tiles)} frames -> {out} ({sheet.shape[1]}x{sheet.shape[0]})")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    def common(sp):
        sp.add_argument("--name", default="snap", help="Base filename for captures")
        sp.add_argument("--scale", type=float, default=1.0, help="Resize factor, e.g. 0.5")
        sp.add_argument("--region", help="Crop to 'x,y,w,h'")

    sp = sub.add_parser("snap", help="Single screenshot")
    common(sp)
    sp.set_defaults(func=mode_snap)

    sp = sub.add_parser("hotkey", help="F9 to capture, Escape to quit")
    common(sp)
    sp.set_defaults(func=mode_hotkey)

    sp = sub.add_parser("watch", help="Capture on an interval")
    common(sp)
    sp.add_argument("--interval", type=float, default=1.0)
    sp.add_argument("--count", type=int, default=20)
    sp.set_defaults(func=mode_watch)

    sp = sub.add_parser("overlay", help="Screenshot with bot click targets drawn on")
    common(sp)
    sp.add_argument("--layout", choices=sorted(OVERLAYS), default="trade_in")
    sp.set_defaults(func=mode_overlay)

    sp = sub.add_parser("sheet", help="Tile a folder of captures into one image")
    sp.add_argument("--dir", default=os.path.join("debug", "trace"))
    sp.add_argument("--cols", type=int, default=4)
    sp.add_argument("--width", type=int, default=560, help="Thumbnail width in px")
    sp.add_argument("--last", type=int, help="Only the last N frames")
    sp.add_argument("--out", help="Output path (default: <dir>/sheet.png)")
    sp.set_defaults(func=mode_sheet)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
