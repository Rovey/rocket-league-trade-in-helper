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
    crop_and_save("trade in empty.png", (15, 880, 80, 30), "back_button.png")
    crop_and_save("trade in empty.png", (305, 260, 135, 30), "show_filters.png")
    crop_and_save("trade in empty.png", (55, 55, 500, 80), "trade_in_empty_slots.png")
    print()

    # --- Trade-in filled (ACCEPT button when clickable) ---
    print("From: trade in filled.png")
    crop_and_save("trade in filled.png", (207, 133, 100, 30), "accept_button.png")
    print()

    # --- Not Eligible popup ---
    print("From: trade in warning cannot trade in.png")
    crop_and_save("trade in warning cannot trade in.png", (220, 225, 200, 40), "not_eligible_popup.png")
    crop_and_save("trade in warning cannot trade in.png", (260, 280, 120, 35), "not_eligible_ok.png")
    print()

    # --- Confirm Trade popup ---
    print("From: trade in accept warning.png")
    crop_and_save("trade in accept warning.png", (215, 305, 90, 30), "confirm_yes.png")
    print()

    # --- Reward screen ---
    print("From: trade in item reward.png")
    crop_and_save("trade in item reward.png", (235, 460, 170, 35), "reward_ok.png")
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
