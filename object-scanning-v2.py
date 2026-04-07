import os
import json
import base64
import re
import time
import uuid
from io import BytesIO

import requests
import urllib3
import cv2
import numpy as np
from PIL import Image
from openai import OpenAI


# -----------------------------
# CONFIG
# -----------------------------
OUTPUT_DIR_NAME = "output"
ASSETS_DIR_NAME = "assets"
AI_MODEL = "gpt-5.4"
AI_MAX_RETRIES = 3


# -----------------------------
# HELPERS
# -----------------------------
def slugify(text):
    """Create a safe filename slug."""
    text = str(text).lower().strip()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    text = text.strip("-")
    return text or "item"


def normalize_text(text):
    """Normalize text for case-insensitive matching."""
    text = str(text or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_json_parse(text):
    """
    Try to parse JSON robustly.
    Accepts plain JSON and JSON wrapped in code fences.
    """
    if not text:
        return {}

    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    # First attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract the first JSON object
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def get_text_input(prompt, required=True):
    """Get text input from the user."""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("This field is required. Please try again.")


def get_input_with_ai_fallback(prompt, ai_value="", required=True):
    """
    If AI has a value, show it as default.
    If AI has no value, prompt like the old version.
    """
    while True:
        if ai_value:
            user_input = input(f"{prompt} [{ai_value}]: ").strip()
            value = user_input if user_input else ai_value
        else:
            value = input(prompt).strip()

        if value or not required:
            return value

        print("This field is required. Please try again.")


def get_year_input():
    """Ask once for a year and reuse it for all items."""
    while True:
        year = input("Enter the year for all products: ").strip()
        if year.isdigit() and len(year) == 4:
            return year
        print("Please enter a valid 4-digit year (e.g. 2025).")


def get_rating_input(ai_value=""):
    """
    Validate rating.
    Allowed:
    - empty
    - integer 1..10
    """
    while True:
        if ai_value:
            user_input = input(f"Enter the product rating (1-10): [{ai_value}]: ").strip()
            value = user_input if user_input else ai_value
        else:
            value = input("Enter the product rating (1-10): ").strip()

        if value == "":
            return ""

        if value.isdigit():
            rating_num = int(value)
            if 1 <= rating_num <= 10:
                return str(rating_num)

        print("Please enter a whole number from 1 to 10, or leave empty.")


# -----------------------------
# CATEGORY LOGIC
# -----------------------------
def extract_existing_categories(output_dir):
    """
    Scan existing markdown files and collect categories from frontmatter lines like:
    category: 'Werkzeug'
    """
    categories = []
    seen = set()

    if not os.path.isdir(output_dir):
        return categories

    for filename in os.listdir(output_dir):
        if not filename.lower().endswith(".md"):
            continue

        md_path = os.path.join(output_dir, filename)

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(
                r"^category:\s*['\"]?(.*?)['\"]?\s*$",
                content,
                flags=re.MULTILINE,
            )
            if match:
                category = match.group(1).strip()
                if category:
                    norm = normalize_text(category)
                    if norm not in seen:
                        seen.add(norm)
                        categories.append(category)

        except Exception as e:
            print(f"Warning: Could not read category from {md_path}: {e}")

    categories.sort(key=lambda x: x.lower())
    return categories


def match_existing_category(candidate, existing_categories):
    """
    Return existing category if candidate matches one already present.
    Matching is normalization-based and also tolerant for singular/plural-like minor differences.
    """
    candidate = (candidate or "").strip()
    if not candidate:
        return ""

    norm_candidate = normalize_text(candidate)

    # Exact normalized match
    for existing in existing_categories:
        if normalize_text(existing) == norm_candidate:
            return existing

    # Loose containment match
    for existing in existing_categories:
        norm_existing = normalize_text(existing)
        if norm_candidate == norm_existing:
            return existing
        if norm_candidate in norm_existing or norm_existing in norm_candidate:
            return existing

    return ""


def choose_category(ai_value, existing_categories):
    """
    Category workflow:
    1. If AI category matches an existing one -> reuse existing category
    2. If AI category exists but is new -> user decides
    3. If AI category empty -> user enters category, ideally reusing existing
    """
    matched = match_existing_category(ai_value, existing_categories)
    if matched:
        print(f"Category matched existing category: {matched}")
        return matched

    if existing_categories:
        print("\nExisting categories:")
        for idx, cat in enumerate(existing_categories, start=1):
            print(f"  {idx}. {cat}")
    else:
        print("\nNo existing categories found yet.")

    if ai_value:
        print(f"\nAI suggested a new category: {ai_value}")
        print("Press Enter to keep it, type a number to choose an existing category, or type a new category name.")

        while True:
            user_input = input("Enter category choice: ").strip()

            if user_input == "":
                return ai_value

            if user_input.isdigit() and existing_categories:
                idx = int(user_input)
                if 1 <= idx <= len(existing_categories):
                    return existing_categories[idx - 1]

            # treat as manual category text
            manual = user_input.strip()
            if manual:
                matched_manual = match_existing_category(manual, existing_categories)
                return matched_manual if matched_manual else manual

            print("Invalid input. Try again.")
    else:
        print("\nNo AI category detected.")
        print("Type a number to choose an existing category, or enter a new category name.")

        while True:
            user_input = input("Enter the product category: ").strip()

            if user_input.isdigit() and existing_categories:
                idx = int(user_input)
                if 1 <= idx <= len(existing_categories):
                    return existing_categories[idx - 1]

            if user_input:
                matched_manual = match_existing_category(user_input, existing_categories)
                return matched_manual if matched_manual else user_input

            print("Please enter a category or choose a valid number.")


# -----------------------------
# CAMERA / IMAGE
# -----------------------------
def capture_image(camera_ip):
    """Capture an image from the IP camera."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.get(
            f"https://{camera_ip}:8080/photoaf.jpg",
            verify=False,
            timeout=10,
        )
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except requests.exceptions.RequestException as e:
        print(f"Error capturing image: {e}")
        return None
    except Exception as e:
        print(f"Unexpected image error: {e}")
        return None


def display_image(image):
    """Display the image using OpenCV."""
    try:
        img_array = np.array(image)

        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        cv2.imshow("Captured Image (Press any key to continue, ESC to reject)", img_array)
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()

        return key != 27
    except Exception as e:
        print(f"Could not display image: {e}")
        return True  # fail-open, damit der Workflow nicht blockiert


def pil_image_to_base64(image):
    """Convert PIL image to base64 JPEG."""
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# -----------------------------
# OPENAI / API
# -----------------------------
def get_openai_client():
    """Return OpenAI client if API key exists, else None."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def validate_openai_setup(client):
    """
    Validate that the API key exists and a minimal test call works.
    """
    if client is None:
        print("Error: OPENAI_API_KEY is not set.")
        print("Please set the environment variable OPENAI_API_KEY and restart the program.")
        return False

    try:
        print("Checking OpenAI API access...")
        response = client.responses.create(
            model=AI_MODEL,
            input="Reply with exactly: OK",
        )
        text = (response.output_text or "").strip()
        if "OK" not in text.upper():
            print("Warning: API test call returned an unexpected response, but access seems available.")
        print("OpenAI API check successful.")
        return True
    except Exception as e:
        print(f"Error: OpenAI API check failed: {e}")
        return False


def analyze_image_with_ai(client, image):
    """
    Analyze image with AI and return structured suggestions.
    Unknown values must be empty strings.
    Includes retry logic.
    """
    fallback = {
        "product_name": "",
        "company_name": "",
        "description": "",
        "rating": "",
        "category": "",
    }

    image_b64 = pil_image_to_base64(image)

    prompt = """
You analyze a product photo and return ONLY JSON.

Detect, if reasonably visible in the image:
- product_name: specific product name or short product label
- company_name: company/brand
- description: short factual description in 1-3 sentences
- rating: rough estimated rating from 1 to 10 as integer string, or empty string
- category: suitable category

Rules:
- No invented facts.
- If something is unclear, return an empty string.
- rating should only be returned if a rough visual estimate is reasonable.
- Return exactly this JSON object with exactly these keys:
  product_name, company_name, description, rating, category
"""

    for attempt in range(1, AI_MAX_RETRIES + 1):
        try:
            response = client.responses.create(
                model=AI_MODEL,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high",
                            },
                        ],
                    }
                ],
            )

            text = (response.output_text or "").strip()
            data = safe_json_parse(text)

            result = {
                "product_name": str(data.get("product_name", "")).strip(),
                "company_name": str(data.get("company_name", "")).strip(),
                "description": str(data.get("description", "")).strip(),
                "rating": str(data.get("rating", "")).strip(),
                "category": str(data.get("category", "")).strip(),
            }

            # sanitize rating from AI
            if result["rating"]:
                if result["rating"].isdigit() and 1 <= int(result["rating"]) <= 10:
                    pass
                else:
                    result["rating"] = ""

            return result

        except Exception as e:
            print(f"AI analysis attempt {attempt}/{AI_MAX_RETRIES} failed: {e}")
            if attempt < AI_MAX_RETRIES:
                time.sleep(1.5)

    print("AI analysis failed after retries. Falling back to manual input.")
    return fallback


# -----------------------------
# SAVE
# -----------------------------
def save_product_data(image, product_name, company_name, description, rating, category, year):
    """Save the image and create a markdown file with product details."""
    output_dir = os.path.join(os.getcwd(), OUTPUT_DIR_NAME)
    assets_dir = os.path.join(output_dir, ASSETS_DIR_NAME)

    os.makedirs(assets_dir, exist_ok=True)

    fileuuid = uuid.uuid4()
    safe_company = slugify(company_name)
    safe_product = slugify(product_name)
    base_filename = f"{safe_company}-{safe_product}-{fileuuid}"

    image_filename = f"{base_filename}.jpg"
    image_path = os.path.join(assets_dir, image_filename)
    md_path = os.path.join(output_dir, f"{base_filename}.md")

    relative_image_path = os.path.join(ASSETS_DIR_NAME, image_filename).replace("\\", "/")

    image.save(image_path)

    with open(md_path, "w", encoding="utf-8") as md_file:
        md_file.write(
            f"""---
product: '{product_name}'
company: '{company_name}'
rating: '{rating}'
category: '{category}'
year: '{year}'
---

# {company_name} - {product_name}
>
> {rating} / 10
>
> {category}
>
> Jahr: {year}

![{product_name}](./{relative_image_path})
{description}
"""
        )

    print(f"Image saved to: {image_path}")
    print(f"Markdown file created: {md_path}")
    return image_path, md_path


# -----------------------------
# MAIN
# -----------------------------
def main():
    client = get_openai_client()
    if not validate_openai_setup(client):
        return

    output_dir = os.path.join(os.getcwd(), OUTPUT_DIR_NAME)
    existing_categories = extract_existing_categories(output_dir)

    if existing_categories:
        print("\nLoaded existing categories:")
        for cat in existing_categories:
            print(f" - {cat}")
    else:
        print("\nNo existing categories found in output folder yet.")

    camera_ip = get_text_input("Enter the camera IP address: ")
    year = get_year_input()
    print(f"Using year '{year}' for all following products.\n")

    while True:
        print("Press Enter to capture an image (or 'q' to quit):")
        user_input = input().strip()

        if user_input.lower() == "q":
            break

        print("Capturing image...")
        image = capture_image(camera_ip)

        if image is None:
            print(f"Failed to capture image from {camera_ip}. Try again.")
            continue

        if not display_image(image):
            print("Image rejected. Try capturing again.")
            continue

        print("Analyzing image with AI...")
        ai_data = analyze_image_with_ai(client, image)

        print("\nAI suggestions:")
        print(json.dumps(ai_data, indent=2, ensure_ascii=False))

        product_name = get_input_with_ai_fallback(
            "Enter the product name: ",
            ai_value=ai_data["product_name"],
            required=True,
        )

        company_name = get_input_with_ai_fallback(
            "Enter the company name: ",
            ai_value=ai_data["company_name"],
            required=True,
        )

        description = get_input_with_ai_fallback(
            "Enter the product description: ",
            ai_value=ai_data["description"],
            required=False,
        )

        rating = get_rating_input(ai_value=ai_data["rating"])

        category = choose_category(
            ai_value=ai_data["category"],
            existing_categories=existing_categories,
        )

        _, _ = save_product_data(
            image=image,
            product_name=product_name,
            company_name=company_name,
            description=description,
            rating=rating,
            category=category,
            year=year,
        )

        # Category cache aktuell halten
        if category and not match_existing_category(category, existing_categories):
            existing_categories.append(category)
            existing_categories.sort(key=lambda x: x.lower())

        print("\nProduct data saved successfully!\n")

    print("Program finished. Goodbye!")


if __name__ == "__main__":
    main()