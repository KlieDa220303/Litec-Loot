#!/usr/bin/env python3
"""
Script to add year 2026 to all existing markdown items in the output directory.
"""

import os
import re
from pathlib import Path


def add_year_to_markdown(file_path, year=2026):
    """
    Add year to markdown file's YAML front matter if not present.
    
    Args:
        file_path: Path to the markdown file
        year: Year to add (default: 2026)
    
    Returns:
        True if modified, False otherwise
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file starts with --- (YAML front matter)
    if not content.startswith('---'):
        print(f"⚠️  {file_path.name} - No YAML front matter found, skipping")
        return False
    
    # Check if year already exists
    if f"year:" in content:
        print(f"✓ {file_path.name} - Year already exists, skipping")
        return False
    
    # Find the closing --- of the front matter
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        print(f"⚠️  {file_path.name} - Could not parse YAML front matter, skipping")
        return False
    
    front_matter = match.group(1)
    front_matter_end = match.end(0)
    
    # Add year before the closing ---
    new_front_matter = front_matter.rstrip() + f"\nyear: {year}"
    new_content = content[:match.start(0)] + f"---\n{new_front_matter}\n---" + content[front_matter_end:]
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ {file_path.name} - Year {year} added")
    return True


def main():
    output_dir = Path("output")
    
    if not output_dir.exists():
        print(f"❌ Error: '{output_dir}' directory not found!")
        return
    
    md_files = list(output_dir.glob("*.md"))
    
    if not md_files:
        print(f"⚠️  No markdown files found in '{output_dir}'")
        return
    
    print(f"Found {len(md_files)} markdown files\n")
    
    modified = 0
    for file_path in sorted(md_files):
        if add_year_to_markdown(file_path, year=2026):
            modified += 1
    
    print(f"\n{'='*50}")
    print(f"✓ Done! Modified {modified} out of {len(md_files)} files")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
