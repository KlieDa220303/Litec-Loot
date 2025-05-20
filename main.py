import os
import requests
import urllib3
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import uuid


def capture_image(camera_ip):
    """Capture an image from the IP camera."""
    # Disable SSL warnings for self-signed certificates
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.get(f"https://{camera_ip}:8080/photoaf.jpg", verify=False)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.RequestException as e:
        print(f"Error capturing image: {e}")
        return None


def display_image(image):
    """Display the image using OpenCV."""
    # Convert PIL Image to OpenCV format
    img_array = np.array(image)
    # Convert RGB to BGR (OpenCV uses BGR)
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    cv2.imshow("Captured Image (Press any key to continue, ESC to reject)", img_array)

    # Wait for key press
    key = cv2.waitKey(0) & 0xFF
    cv2.destroyAllWindows()

    # ESC key to reject
    return key != 27  # Return True if not ESC


def save_product_data(image, product_name, company_name, description, rating, category):
    """Save the image and create a markdown file with product details."""
    # Create output directory structure if not exists
    output_dir = os.path.join(os.getcwd(), "output")
    assets_dir = os.path.join(output_dir, "assets")

    os.makedirs(assets_dir, exist_ok=True)

    # Create filenames
    fileuuid = uuid.uuid4()
    base_filename = f"{company_name}-{product_name}-{fileuuid}".lower().replace(
        " ", "-"
    )
    image_filename = f"{base_filename}.jpg"
    image_path = os.path.join(assets_dir, image_filename)
    md_path = os.path.join(output_dir, f"{base_filename}.md")

    # Create relative path for markdown file
    relative_image_path = os.path.join("assets", image_filename)

    # convert \ to /
    relative_image_path = relative_image_path.replace("\\", "/")

    # Save the image
    image.save(image_path)

    # Create markdown file
    with open(md_path, "w", encoding="utf-8") as md_file:
        md_file.write(
            f"""---
product: '{product_name}'
company: '{company_name}'
rating: '{rating}'
category: '{category}'
---

# {company_name} - {product_name}
>
> {rating} / 10
>
> {category}

![{product_name}](./{relative_image_path})
{description}
"""
        )

    print(f"Image saved to: {image_path}")
    print(f"Markdown file created: {md_path}")
    return image_path, md_path


def get_text_input(prompt, required=True):
    """Get text input from the user."""
    while True:
        value = input(prompt)
        if value or not required:
            return value
        print("This field is required. Please try again.")


def main():
    # Get camera IP address
    camera_ip = get_text_input("Enter the camera IP address: ")

    while True:
        print("\nPress Enter to capture an image (or 'q' to quit):")
        user_input = input()

        if user_input.lower() == "q":
            break

        print("Capturing image...")
        image = capture_image(camera_ip)

        if image is None:
            print(f"Failed to capture image from {camera_ip}. Try again.")
            continue

        # Display image and get approval
        if not display_image(image):
            print("Image rejected. Try capturing again.")
            continue

        # Get product details
        product_name = get_text_input("Enter the product name: ")
        company_name = get_text_input("Enter the company name: ")
        description = get_text_input("Enter the product description: ", required=False)
        rating = get_text_input("Enter the product rating (1-10): ", required=False)
        category = get_text_input("Enter the product category: ", required=False)

        # Save data
        image_path, md_path = save_product_data(
            image, product_name, company_name, description, rating, category
        )
        print(f"\nProduct data saved successfully!")

    print("Program finished. Goodbye!")


if __name__ == "__main__":
    main()
