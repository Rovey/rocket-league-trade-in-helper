"""Check that every TEMPLATE_REGIONS box actually contains its template.

A wrong region makes a template silently undetectable at runtime, so each one is
verified against a reference screenshot: the full-screen match and the
region-limited match must agree.

Usage:
    python validate_regions.py
"""

import sys

import cv2

import trade_in_bot as bot

# template filename -> reference screenshot that shows it
REFERENCES = {
    "menu_garage.png": "ui-images/main_menu.png",
    "garage_trade_in.png": "ui-images/garage_menu.png",
    "garage_manage_inv.png": "ui-images/garage_menu.png",
    "inv_header_all.png": "ui-images/inventory_all_items.png",
    "inv_tab_reward.png": "ui-images/inventory_all_items.png",
    "inv_back.png": "ui-images/inventory_all_items.png",
    "inv_header_reward.png": "ui-images/inventory_reward_items.png",
    "trade_in_title.png": "ui-images/main screen.png",
    "trade_in_title.png#dimmed": "ui-images/trade_in_menu_dimmed.png",
    "show_filters.png": "ui-images/trade in empty.png",
    "back_button.png": "ui-images/trade in empty.png",
    "trade_in_empty_slots.png": "ui-images/trade in empty.png",
    "accept_button.png": "ui-images/trade in filled.png",
    "confirm_yes.png": "ui-images/trade in accept warning.png",
    "reward_ok.png": "ui-images/trade in item reward.png",
    "not_eligible_popup.png": "ui-images/trade in warning cannot trade in.png",
    "not_eligible_ok.png": "ui-images/trade in warning cannot trade in.png",
    "choose_quantity_popup.png": "ui-images/trade in choose quantity.png",
    "quantity_ok.png": "ui-images/trade in choose quantity.png",
    "quantity_plus.png": "ui-images/trade in choose quantity.png",
    "drop_open_button.png": "debug/drop_flow/04_after_click.png",
    "drop_reveal_ok.png": "debug/drop_flow/12_after_open.png",
    # Same button, but on a reveal that shows an extra banner and sits lower.
    "drop_reveal_ok.png#banner": "ui-images/drop_reveal_with_banner.png",
    "drop_reveal_ok_hl.png": "ui-images/drop_reveal_single_ok.png",
    "drop_reveal_label.png": "ui-images/drop_reveal_single_ok.png",
    "drop_reveal_label.png#banner": "ui-images/drop_reveal_with_banner.png",
    "drop_reveal_label.png#plain": "debug/drop_flow/12_after_open.png",
}
for card, _ in bot.CATEGORY_CARDS:
    REFERENCES[card] = "ui-images/main screen.png"


def main():
    failures = 0
    missing_reference = []

    checks = [(name, name, region) for name, region in sorted(bot.TEMPLATE_REGIONS.items())]
    # Extra reference screenshots for the same template, keyed "template#variant".
    for key, ref_path in REFERENCES.items():
        if "#" in key:
            base = key.split("#", 1)[0]
            checks.append((key, base, bot.TEMPLATE_REGIONS[base]))

    for key, name, region in checks:
        ref = REFERENCES.get(key)
        if ref is None:
            missing_reference.append(key)
            continue

        screen = cv2.imread(ref)
        if screen is None:
            print(f"SKIP  {key:34s} reference not found: {ref}")
            continue

        full = bot.find_on_screen(name, screenshot=screen, region=None)
        limited = bot.find_on_screen(name, screenshot=screen, region=region)

        if full is None:
            print(f"SKIP  {key:34s} not visible in {ref}")
        elif limited == full:
            print(f"OK    {key:34s} {full} in {region}")
        else:
            failures += 1
            print(f"FAIL  {key:34s} full={full} region-limited={limited} box={region}")

    for name in missing_reference:
        print(f"NOREF {name}")

    print()
    print(f"{failures} region(s) wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
