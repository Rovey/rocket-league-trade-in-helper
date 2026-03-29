"""Overlay item grid positions on the trade-in screenshot for visual validation.

Shows numbered circles at each position where the bot would click.
Adjust constants in trade_in_bot.py if positions are off.

Controls (all letter keys, arrow keys don't work on Windows):

  Item grid position:
    W/S          — Move grid up/down by 5px
    A/D          — Move grid left/right by 5px
    E/Q          — Increase/decrease cell width by 5px
    R/F          — Increase/decrease cell height by 5px
    T/G          — Add/remove columns
    Y/H          — Add/remove rows

  Scroll detection box:
    I/K          — Move box up/down by 10px
    J/L          — Move box left/right by 10px
    U/O          — Decrease/increase box width by 10px
    8/9 (number) — Decrease/increase box height by 10px
    B            — Auto-fit detection box around current grid

  General:
    P            — Print current values
    Enter        — Save values to trade_in_bot.py and exit
    Escape       — Exit without saving
"""

import cv2
import os
import re

UI_IMAGES_DIR = "ui-images"
TRADE_IN_IMAGE = os.path.join(UI_IMAGES_DIR, "trade in empty.png")


def load_grid_constants():
    with open("trade_in_bot.py", "r") as f:
        content = f.read()

    def extract(name):
        match = re.search(rf'^{name}\s*=\s*(\d+)', content, re.MULTILINE)
        return int(match.group(1)) if match else None

    return {
        "ITEM_COLS": extract("ITEM_COLS"),
        "ITEM_ROWS": extract("ITEM_ROWS"),
        "ITEM_CELL_W": extract("ITEM_CELL_W"),
        "ITEM_CELL_H": extract("ITEM_CELL_H"),
        "ITEM_START_X": extract("ITEM_START_X"),
        "ITEM_START_Y": extract("ITEM_START_Y"),
        "ITEM_GRID_X": extract("ITEM_GRID_X"),
        "ITEM_GRID_Y": extract("ITEM_GRID_Y"),
        "ITEM_GRID_W": extract("ITEM_GRID_W"),
        "ITEM_GRID_H": extract("ITEM_GRID_H"),
    }


def save_grid_constants(vals):
    with open("trade_in_bot.py", "r") as f:
        content = f.read()

    for name, value in vals.items():
        content = re.sub(
            rf'^({name}\s*=\s*)\d+',
            rf'\g<1>{value}',
            content,
            flags=re.MULTILINE
        )

    with open("trade_in_bot.py", "w") as f:
        f.write(content)

    print("Saved updated constants to trade_in_bot.py")


def auto_fit_detection_box(vals):
    """Auto-fit the detection box to surround the current item grid with padding."""
    padding = 30
    cols = vals["ITEM_COLS"]
    rows = vals["ITEM_ROWS"]
    start_x = vals["ITEM_START_X"]
    start_y = vals["ITEM_START_Y"]
    cell_w = vals["ITEM_CELL_W"]
    cell_h = vals["ITEM_CELL_H"]

    # Calculate the bounding box of all item positions
    left = start_x - cell_w // 2
    top = start_y - cell_h // 2
    right = start_x + (cols - 1) * cell_w + cell_w // 2
    bottom = start_y + (rows - 1) * cell_h + cell_h // 2

    vals["ITEM_GRID_X"] = max(0, left - padding)
    vals["ITEM_GRID_Y"] = max(0, top - padding)
    vals["ITEM_GRID_W"] = (right - left) + 2 * padding
    vals["ITEM_GRID_H"] = (bottom - top) + 2 * padding


def draw_grid(img, vals):
    display = img.copy()
    cols = vals["ITEM_COLS"]
    rows = vals["ITEM_ROWS"]
    cell_w = vals["ITEM_CELL_W"]
    cell_h = vals["ITEM_CELL_H"]
    start_x = vals["ITEM_START_X"]
    start_y = vals["ITEM_START_Y"]
    grid_x = vals["ITEM_GRID_X"]
    grid_y = vals["ITEM_GRID_Y"]
    grid_w = vals["ITEM_GRID_W"]
    grid_h = vals["ITEM_GRID_H"]

    # Draw grid region rectangle (cyan)
    cv2.rectangle(display, (grid_x, grid_y),
                  (grid_x + grid_w, grid_y + grid_h),
                  (255, 255, 0), 2)
    cv2.putText(display, "Scroll detection region (I/K/J/L to move, U/O width, 8/9 height, B=auto-fit)",
                (grid_x + 5, grid_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    # Draw item positions
    idx = 0
    for row in range(rows):
        for col in range(cols):
            x = start_x + col * cell_w
            y = start_y + row * cell_h

            # Draw crosshair circle
            cv2.circle(display, (x, y), 20, (0, 255, 0), 2)
            cv2.line(display, (x - 25, y), (x + 25, y), (0, 255, 0), 1)
            cv2.line(display, (x, y - 25), (x, y + 25), (0, 255, 0), 1)

            # Draw index number
            cv2.putText(display, str(idx), (x - 8, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            idx += 1

    # Draw info panel at top
    bar_h = 110
    cv2.rectangle(display, (0, 0), (display.shape[1], bar_h), (30, 30, 30), -1)

    info_lines = [
        f"START: ({start_x}, {start_y})  CELL: {cell_w}x{cell_h}  GRID: {cols}cols x {rows}rows",
        f"DETECT BOX: ({grid_x}, {grid_y}) {grid_w}x{grid_h}",
        "W/S=Y pos | A/D=X pos | E/Q=cell W | R/F=cell H | T/G=cols | Y/H=rows",
        "P=print | B=auto-fit box | Enter=save | Esc=quit",
    ]
    for i, line in enumerate(info_lines):
        cv2.putText(display, line, (10, 22 + i * 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    return display


def main():
    img = cv2.imread(TRADE_IN_IMAGE)
    if img is None:
        print(f"ERROR: Could not load {TRADE_IN_IMAGE}")
        return

    vals = load_grid_constants()
    print("Current grid constants:")
    for k, v in vals.items():
        print(f"  {k} = {v}")
    print()
    print("Controls:")
    print("  W/S = move Y | A/D = move X | E/Q = cell width | R/F = cell height")
    print("  T/G = add/remove cols | Y/H = add/remove rows")
    print("  I/K/J/L = move detect box | U/O = box width | 8/9 = box height")
    print("  B = auto-fit box | P = print | Enter = save | Esc = quit")

    window_name = "Grid Validator - Adjust positions"

    # Scale for display
    scale = min(1.0, 1400 / img.shape[1])
    if scale < 1.0:
        display_base = cv2.resize(img, None, fx=scale, fy=scale)
    else:
        display_base = img

    while True:
        # Scale vals for display
        scaled_vals = {}
        for k, v in vals.items():
            scaled_vals[k] = int(v * scale)

        display = draw_grid(display_base, scaled_vals)
        cv2.imshow(window_name, display)
        key = cv2.waitKey(30) & 0xFF

        step = 5
        box_step = 10

        # --- Item grid position ---
        if key == ord('w'):
            vals["ITEM_START_Y"] -= step
        elif key == ord('s'):
            vals["ITEM_START_Y"] += step
        elif key == ord('a'):
            vals["ITEM_START_X"] -= step
        elif key == ord('d'):
            vals["ITEM_START_X"] += step

        # --- Cell size ---
        elif key == ord('e'):
            vals["ITEM_CELL_W"] += step
        elif key == ord('q'):
            vals["ITEM_CELL_W"] = max(10, vals["ITEM_CELL_W"] - step)
        elif key == ord('r'):
            vals["ITEM_CELL_H"] += step
        elif key == ord('f'):
            vals["ITEM_CELL_H"] = max(10, vals["ITEM_CELL_H"] - step)

        # --- Columns and rows ---
        elif key == ord('t'):
            vals["ITEM_COLS"] += 1
        elif key == ord('g'):
            vals["ITEM_COLS"] = max(1, vals["ITEM_COLS"] - 1)
        elif key == ord('y'):
            vals["ITEM_ROWS"] += 1
        elif key == ord('h'):
            vals["ITEM_ROWS"] = max(1, vals["ITEM_ROWS"] - 1)

        # --- Detection box ---
        elif key == ord('i'):
            vals["ITEM_GRID_Y"] -= box_step
        elif key == ord('k'):
            vals["ITEM_GRID_Y"] += box_step
        elif key == ord('j'):
            vals["ITEM_GRID_X"] -= box_step
        elif key == ord('l'):
            vals["ITEM_GRID_X"] += box_step
        elif key == ord('u'):
            vals["ITEM_GRID_W"] = max(50, vals["ITEM_GRID_W"] - box_step)
        elif key == ord('o'):
            vals["ITEM_GRID_W"] += box_step
        elif key == ord('8'):
            vals["ITEM_GRID_H"] = max(50, vals["ITEM_GRID_H"] - box_step)
        elif key == ord('9'):
            vals["ITEM_GRID_H"] += box_step

        # --- Auto-fit detection box ---
        elif key == ord('b'):
            auto_fit_detection_box(vals)
            print("  Auto-fitted detection box around grid")

        # --- Print / Save / Exit ---
        elif key == ord('p'):
            print("\nCurrent values:")
            for k, v in vals.items():
                print(f"  {k} = {v}")
        elif key == 13:  # Enter
            save_grid_constants(vals)
            break
        elif key == 27:  # Escape
            print("Exited without saving.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
