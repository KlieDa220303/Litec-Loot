#!/usr/bin/env python3
"""Update descriptions in output markdown files with improved item descriptions."""

from pathlib import Path
import argparse
from typing import Dict, List

OUTPUT_DIR = Path("output")


def parse_frontmatter(content: str) -> Dict[str, str]:
    if not content.startswith("---"):
        return {}

    end_idx = content.find("\n---", 3)
    if end_idx == -1:
        return {}

    frontmatter = content[3:end_idx].strip()
    result: Dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def choose_variant(product: str, variants: List[str]) -> str:
    if not variants:
        return ""
    key = sum(ord(ch) for ch in product) % len(variants)
    return variants[key]


def build_description(metadata: Dict[str, str]) -> str:
    product = metadata.get("product", "This item")
    company = metadata.get("company")
    category = metadata.get("category", "Anderes").strip()
    rating = metadata.get("rating")
    year = metadata.get("year")

    clean_name = product.replace(company or "", "").strip()
    if not clean_name:
        clean_name = product

    templates = {
        "Stift": [
            f"{product} is a smooth-writing branded pen crafted for clear notes and everyday use.",
            f"A premium promotional pen from {company} that feels comfortable in hand and looks professional.",
            f"{product} delivers dependable ink flow and a sleek design, perfect for meetings and on-the-go writing."
        ],
        "Block": [
            f"A handy notepad from {company} for jotting down ideas, tasks and quick reminders.",
            f"This branded block combines solid paper quality with a useful format for daily notes.",
            f"A compact block that keeps your thoughts organized while carrying the {company} brand."
        ],
        "Süßigkeiten": [
            f"A sweet branded treat from {company}, ideal as a tasty giveaway or small snack.",
            f"These candy items bring a playful brand touch to your breaks and event goodie bags.",
            f"A colorful snack with {company} branding that adds a little reward to the day."
        ],
        "Schlüsselanhänger": [
            f"A stylish keychain accessory with {company} branding for keeping keys secure and easy to find.",
            f"This branded key ring is practical, compact and a great reminder of {company}.",
            f"A durable keychain that blends everyday use with clear brand visibility."
        ],
        "Messzeug": [
            f"A practical measuring tool from {company} designed for accuracy on the desk or in the field.",
            f"Useful for quick measurements, this branded tool is a smart addition to any workspace.",
            f"A precise and portable measuring accessory that reflects {company}'s professional identity."
        ],
        "Spielzeug": [
            f"A playful branded item that adds a fun moment to events and promotional giveaways.",
            f"This little toy brings an entertaining brand experience to children and adults alike.",
            f"A cheerful promotional piece with {company} messaging, created for enjoyment and recall."
        ],
        "Getränk": [
            f"A refreshing branded drink that makes a nice break during the workday.",
            f"This beverage item delivers a quick refresh with a subtle brand presence.",
            f"A convenient drink for events, complete with {company}'s promotional look."
        ],
        "Getränke": [
            f"A refreshing branded drink that makes a nice break during the workday.",
            f"This beverage item delivers a quick refresh with a subtle brand presence.",
            f"A convenient drink for events, complete with {company}'s promotional look."
        ],
        "Feuerzeug": [
            f"A sturdy lighter with {company} branding, built for reliable everyday use.",
            f"This branded lighter combines functionality with a compact design for easy carrying.",
            f"A practical promotional lighter that keeps flames handy and brand recognition strong."
        ],
        "Kleidung": [
            f"A branded clothing item from {company} that adds comfort and visibility to everyday wear.",
            f"This apparel piece reflects the company's style while remaining wearable and practical.",
            f"A promotional garment designed for events, staff or giveaways with strong brand impact."
        ],
        "Multitool": [
            f"A compact multi-tool that brings versatile utility and {company} branding to daily tasks.",
            f"This promotional gadget helps with small repairs and quick fixes while keeping the brand visible.",
            f"A practical, handy tool made for people who need simple solutions on the move."
        ],
        "Elektronik": [
            f"A branded tech item from {company} that adds convenience to everyday routines.",
            f"This electronic accessory blends functionality with a strong promotional identity.",
            f"A useful gadget that keeps the brand visible while supporting daily digital needs."
        ],
        "Gesundheit": [
            f"A compact wellness item from {company}, great for staying prepared and cared for on the go.",
            f"This health-oriented gift combines practical support with branded packaging.",
            f"A small but useful item designed to keep wellbeing in mind while carrying the company logo."
        ],
        "Jausenbox": [
            f"A branded lunch box that keeps snacks organized and the company identity visible.",
            f"This handy food container blends everyday convenience with promotional branding.",
            f"A useful item for meals away from home, featuring strong brand recognition."
        ],
        "Radierer": [
            f"A branded eraser designed for clean corrections and a compact desk presence.",
            f"This small stationery item keeps writing mistakes neat while boosting brand awareness.",
            f"A practical eraser with useful branding for students and office use."
        ],
        "Essen": [
            f"A tasty branded snack that makes a quick bite more enjoyable.",
            f"This edible giveaway offers a flavorful brand experience for recipients.",
            f"A little treat that combines convenience with subtle promotional appeal."
        ],
        "Sticker": [
            f"A branded sticker that works well on notebooks, laptops and personal gear.",
            f"This promotional decal adds visual interest while carrying the company logo.",
            f"A fun sticker for easy personalization and brand recognition."
        ],
        "Anderes": [
            f"A unique promotional item from {company}, suited for everyday visibility.",
            f"This branded piece stands out as a useful and memorable giveaway.",
            f"A versatile promotional product that keeps the brand present in daily life."
        ],
    }

    fallback = [
        f"{product} from {company or 'the brand'} makes a solid promotional item.",
        f"A branded giveaway that combines practicality with the company identity.",
        f"A useful item designed to keep the brand visible while serving everyday needs."
    ]

    key = category if category in templates else "Anderes"
    description = choose_variant(clean_name or product, templates.get(key, fallback))

    if "Stift" in category or "stift" in clean_name.lower() or "Kugelschreiber" in clean_name:
        description = choose_variant(product, templates["Stift"])
    elif "Block" in category or "postit" in clean_name.lower() or "block" in clean_name.lower():
        description = choose_variant(product, templates["Block"])
    elif "Feuerzeug" in category or "feuerzeug" in clean_name.lower():
        description = choose_variant(product, templates["Feuerzeug"])
    elif "Schlüsselanhänger" in category or "schlüsselanhänger" in clean_name.lower() or "schluessel" in clean_name.lower():
        description = choose_variant(product, templates["Schlüsselanhänger"])
    elif "Messzeug" in category or "Lineal" in clean_name or "Zollstock" in clean_name or "Geodreieck" in clean_name:
        description = choose_variant(product, templates["Messzeug"])
    elif "Süßigkeiten" in category or "Zuckerl" in clean_name.lower() or "Minzen" in clean_name.lower() or "Gummib" in clean_name:
        description = choose_variant(product, templates["Süßigkeiten"])
    elif "Getränk" in category or "Flasche" in clean_name.lower():
        description = choose_variant(product, templates["Getränke"])
    elif "Spielzeug" in category or "Spielkarten" in clean_name.lower():
        description = choose_variant(product, templates["Spielzeug"])
    elif "Kleidung" in category:
        description = choose_variant(product, templates["Kleidung"])
    elif "Multitool" in category:
        description = choose_variant(product, templates["Multitool"])
    elif "Elektronik" in category:
        description = choose_variant(product, templates["Elektronik"])
    elif "Gesundheit" in category:
        description = choose_variant(product, templates["Gesundheit"])
    elif "Jausenbox" in category:
        description = choose_variant(product, templates["Jausenbox"])
    elif "Radierer" in category:
        description = choose_variant(product, templates["Radierer"])
    elif "Essen" in category:
        description = choose_variant(product, templates["Essen"])
    elif "Sticker" in category:
        description = choose_variant(product, templates["Sticker"])

    extra_parts = []
    if year:
        extra_parts.append(f"Introduced in {year}")
    if rating:
        extra_parts.append(f"rated {rating}/10")
    if extra_parts:
        description += " " + ", ".join(extra_parts) + "."

    return description


def update_description_in_file(path: Path, dry_run: bool = False) -> bool:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    image_line_index = next(
        (index for index, line in enumerate(lines) if line.startswith("![") and "](" in line), None
    )
    if image_line_index is None:
        return False

    new_description = build_description(parse_frontmatter(content))
    updated_lines = lines[: image_line_index + 1] + [new_description]

    if updated_lines == lines:
        return False

    if not dry_run:
        path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    return True


def find_markdown_files(directory: Path) -> List[Path]:
    return sorted(directory.rglob("*.md"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update all item descriptions in output markdown files to a better standardized description."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which files would be updated without writing changes.",
    )
    parser.add_argument(
        "--directory",
        default=str(OUTPUT_DIR),
        help="Directory containing the markdown files (default: output).",
    )
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        raise SystemExit(f"Directory not found: {directory}")

    files = find_markdown_files(directory)
    if not files:
        raise SystemExit(f"No markdown files found in {directory}")

    updated_count = 0
    for path in files:
        changed = update_description_in_file(path, dry_run=args.dry_run)
        if changed:
            updated_count += 1
            print(f"Updated: {path}")
        elif args.dry_run:
            print(f"Would skip: {path}")

    action = "would be updated" if args.dry_run else "updated"
    print(f"\n{updated_count} files {action}.")


if __name__ == "__main__":
    main()
