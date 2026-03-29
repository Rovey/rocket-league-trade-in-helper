"""Interactive template cropping tool.

Shows each UI screenshot and lets you draw a rectangle to select the region
for each template. Uses OpenCV's GUI.

Controls:
    Click + drag   — Draw selection rectangle
    Enter / Space  — Confirm selection and save template
    R              — Reset current selection
    S              — Skip this template (keep existing if any)
    Q / Escape     — Quit (saves all templates confirmed so far)
"""

import cv2
import os
import json

TEMPLATES_DIR = "templates"
UI_IMAGES_DIR = "ui-images"
COORDS_FILE = "template_coords.json"

# Each template to crop: (source_image, template_name, description)
TEMPLATES_TO_CROP = [
    # --- Trade-in screen buttons ---
    ("trade in filled.png", "accept_button.png",
     "Select the ACCEPT button (visible when 5 slots are filled)"),

    ("trade in empty.png", "back_button.png",
     "Select the BACK button (bottom-left corner)"),

    ("trade in empty.png", "show_filters.png",
     "Select the SHOW FILTERS button/text"),

    ("trade in empty.png", "trade_in_empty_slots.png",
     "Select the empty 5-slot bar at the top"),

    # --- Not Eligible popup ---
    ("trade in warning cannot trade in.png", "not_eligible_popup.png",
     "Select the NOT ELIGIBLE header text"),

    ("trade in warning cannot trade in.png", "not_eligible_ok.png",
     "Select the OK button on the Not Eligible popup"),

    # --- Confirm Trade popup ---
    ("trade in accept warning.png", "confirm_yes.png",
     "Select the YES button on the Confirm Trade popup"),

    # --- Reward screen ---
    ("trade in item reward.png", "reward_ok.png",
     "Select the OK button on the reward screen"),

    # --- Choose Quantity popup ---
    ("trade in choose quantity.png", "choose_quantity_popup.png",
     "Select the CHOOSE QUANTITY header text"),

    ("trade in choose quantity.png", "quantity_plus.png",
     "Select the + (plus) button"),

    ("trade in choose quantity.png", "quantity_ok.png",
     "Select the OK button on the quantity popup"),

    # --- Main screen category cards ---
    ("main screen.png", "card_core_special.png",
     "Select the SPECIAL card under CORE ITEMS"),

    ("main screen.png", "card_core_deluxe.png",
     "Select the DELUXE card under CORE ITEMS"),

    ("main screen.png", "card_core_import.png",
     "Select the IMPORT card under CORE ITEMS"),

    ("main screen.png", "card_core_exotic.png",
     "Select the EXOTIC card under CORE ITEMS"),

    ("main screen.png", "card_core_black_market.png",
     "Select the BLACK MARKET card under CORE ITEMS"),

    ("main screen.png", "card_tournament_special.png",
     "Select the SPECIAL ITEM under TOURNAMENT ITEMS"),

    ("main screen.png", "card_tournament_deluxe.png",
     "Select the DELUXE ITEM under TOURNAMENT ITEMS"),

    ("main screen.png", "card_tournament_import.png",
     "Select the IMPORT ITEM under TOURNAMENT ITEMS"),

    ("main screen.png", "card_tournament_exotic.png",
     "Select the EXOTIC ITEM under TOURNAMENT ITEMS"),

    ("main screen.png", "card_tournament_black_market.png",
     "Select the BLACK MARKET ITEM under TOURNAMENT ITEMS"),

    ("main screen.png", "card_blueprints_deluxe.png",
     "Select the DELUXE card under BLUEPRINTS"),

    ("main screen.png", "card_blueprints_import.png",
     "Select the IMPORT card under BLUEPRINTS"),

    ("main screen.png", "card_blueprints_exotic.png",
     "Select the EXOTIC card under BLUEPRINTS"),

    ("main screen.png", "card_blueprints_black_market.png",
     "Select the BLACK MARKET card under BLUEPRINTS"),
]


class RectangleSelector:
    """Handles mouse events for drawing a rectangle on an image."""

    def __init__(self):
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.done = False

    def reset(self):
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.done = False

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start_point = (x, y)
            self.end_point = (x, y)
            self.drawing = True
            self.done = False

        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end_point = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            self.end_point = (x, y)
            self.drawing = False
            self.done = True

    def get_rect(self):
        """Return (x, y, w, h) of the selected rectangle, normalized."""
        if self.start_point is None or self.end_point is None:
            return None
        x1 = min(self.start_point[0], self.end_point[0])
        y1 = min(self.start_point[1], self.end_point[1])
        x2 = max(self.start_point[0], self.end_point[0])
        y2 = max(self.start_point[1], self.end_point[1])
        w = x2 - x1
        h = y2 - y1
        if w < 2 or h < 2:
            return None
        return (x1, y1, w, h)


def draw_overlay(img, selector, template_name, description, index, total):
    """Draw the selection rectangle and instructions on a copy of the image."""
    display = img.copy()

    # Draw selection rectangle
    if selector.start_point and selector.end_point:
        cv2.rectangle(display, selector.start_point, selector.end_point,
                      (0, 255, 0), 2)

    # Draw info bar at top
    bar_h = 80
    cv2.rectangle(display, (0, 0), (display.shape[1], bar_h), (40, 40, 40), -1)

    # Template name and progress
    progress = f"[{index + 1}/{total}]"
    cv2.putText(display, f"{progress} {template_name}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # Description
    cv2.putText(display, description,
                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Controls
    cv2.putText(display, "Draw rect | Enter=confirm | R=reset | S=skip | Q=quit",
                (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    return display


def load_existing_coords():
    """Load previously saved coordinates if they exist."""
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_coords(coords):
    """Save coordinates to JSON file for future reference."""
    with open(COORDS_FILE, "w") as f:
        json.dump(coords, f, indent=2)


def main():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    # Load any previously saved coordinates
    saved_coords = load_existing_coords()

    # Cache loaded images to avoid re-reading the same file
    image_cache = {}
    window_name = "Template Cropper - Select Region"

    print("=" * 60)
    print("  Interactive Template Cropper")
    print("  Draw a rectangle around each UI element")
    print("=" * 60)
    print()

    total = len(TEMPLATES_TO_CROP)
    new_coords = {}

    for i, (source_file, template_name, description) in enumerate(TEMPLATES_TO_CROP):
        # Load source image (with caching)
        if source_file not in image_cache:
            path = os.path.join(UI_IMAGES_DIR, source_file)
            img = cv2.imread(path)
            if img is None:
                print(f"ERROR: Could not load {path} — skipping {template_name}")
                continue
            image_cache[source_file] = img

        img = image_cache[source_file]

        # Scale down for display if image is larger than screen
        # Show at a reasonable size — scale to fit ~1400px wide
        scale = min(1.0, 1400 / img.shape[1])
        if scale < 1.0:
            display_img = cv2.resize(img, None, fx=scale, fy=scale)
        else:
            display_img = img.copy()

        selector = RectangleSelector()
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(window_name, selector.mouse_callback)

        print(f"[{i + 1}/{total}] {template_name}: {description}")

        confirmed = False
        skipped = False

        while True:
            overlay = draw_overlay(display_img, selector, template_name,
                                   description, i, total)
            cv2.imshow(window_name, overlay)
            key = cv2.waitKey(30) & 0xFF

            # Enter or Space — confirm selection
            if key in (13, 32):
                rect = selector.get_rect()
                if rect is not None:
                    confirmed = True
                    break
                else:
                    print("  No valid selection — draw a rectangle first")

            # R — reset selection
            elif key == ord('r') or key == ord('R'):
                selector.reset()

            # S — skip this template
            elif key == ord('s') or key == ord('S'):
                skipped = True
                break

            # Q or Escape — quit
            elif key == ord('q') or key == ord('Q') or key == 27:
                print("\nQuitting. Saving confirmed templates so far...")
                cv2.destroyAllWindows()
                save_coords(new_coords)
                update_crop_script(new_coords)
                return

        if skipped:
            print(f"  Skipped {template_name}")
            continue

        if confirmed:
            # Get the rectangle in display coordinates
            rect = selector.get_rect()
            # Scale back to original image coordinates
            x = int(rect[0] / scale)
            y = int(rect[1] / scale)
            w = int(rect[2] / scale)
            h = int(rect[3] / scale)

            # Crop and save
            cropped = img[y:y + h, x:x + w]
            output_path = os.path.join(TEMPLATES_DIR, template_name)
            cv2.imwrite(output_path, cropped)

            new_coords[template_name] = {
                "source": source_file,
                "region": [x, y, w, h],
                "description": description,
            }

            print(f"  Saved {template_name} — region: ({x}, {y}, {w}, {h})")

    cv2.destroyAllWindows()

    # Save coordinates and update the batch crop script
    save_coords(new_coords)
    update_crop_script(new_coords)

    print()
    print("=" * 60)
    print(f"  Done! {len(new_coords)} templates saved to {TEMPLATES_DIR}/")
    print(f"  Coordinates saved to {COORDS_FILE}")
    print(f"  crop_templates.py has been updated with your coordinates")
    print("=" * 60)


def update_crop_script(coords):
    """Regenerate crop_templates.py with the user-selected coordinates."""
    if not coords:
        return

    lines = [
        '"""Crop template images from UI screenshots for template matching.',
        '',
        'Run once to generate all templates in the templates/ directory.',
        'Coordinates are for 2560x1440 resolution.',
        '"""',
        '',
        'import cv2',
        'import os',
        '',
        'TEMPLATES_DIR = "templates"',
        'UI_IMAGES_DIR = "ui-images"',
        '',
        '',
        'def crop_and_save(source_filename, region, template_name):',
        '    """Crop a region from a source image and save as a template."""',
        '    source_path = os.path.join(UI_IMAGES_DIR, source_filename)',
        '    img = cv2.imread(source_path)',
        '    if img is None:',
        '        print(f"ERROR: Could not load {source_path}")',
        '        return False',
        '',
        '    x, y, w, h = region',
        '    cropped = img[y:y+h, x:x+w]',
        '',
        '    output_path = os.path.join(TEMPLATES_DIR, template_name)',
        '    cv2.imwrite(output_path, cropped)',
        '    print(f"  Saved {template_name} ({w}x{h})")',
        '    return True',
        '',
        '',
        'def main():',
        '    os.makedirs(TEMPLATES_DIR, exist_ok=True)',
        '',
        '    print("Cropping template images...")',
        '    print()',
        '',
    ]

    # Group by source image
    by_source = {}
    for template_name, info in coords.items():
        source = info["source"]
        if source not in by_source:
            by_source[source] = []
        by_source[source].append((template_name, info["region"]))

    for source, templates in by_source.items():
        lines.append(f'    print("From: {source}")')
        for tname, region in templates:
            lines.append(
                f'    crop_and_save("{source}", ({region[0]}, {region[1]}, {region[2]}, {region[3]}), "{tname}")'
            )
        lines.append('    print()')
        lines.append('')

    lines.extend([
        '    print("Done! Template images saved to templates/")',
        '',
        '',
        'if __name__ == "__main__":',
        '    main()',
        '',
    ])

    with open("crop_templates.py", "w") as f:
        f.write("\n".join(lines))

    print(f"  Updated crop_templates.py with {len(coords)} template coordinates")


if __name__ == "__main__":
    main()
