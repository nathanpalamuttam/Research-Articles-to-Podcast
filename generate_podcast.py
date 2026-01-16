"""
Generate podcast script from research papers and convert to SSML.

This script:
1. Extracts text content from a PDF research paper
2. Generates an engaging podcast script using Gemini
3. Converts the script to SSML format for text-to-speech
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

import extract_pdf_text
import script_to_ssml


# Configuration
PDF_FILE = "Pearl-Placing Every Atom in the Right Location.pdf"
OUTPUT_DIR = Path("outputs/scripts")
MODEL = "models/gemini-2.5-flash"
MAX_TEXT_LENGTH = 30000  # Characters to send to model


def setup_environment():
    """Load environment variables and validate API key."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment")
        print("Get your API key from: https://aistudio.google.com/apikey")
        print("Then add it to your .env file: GOOGLE_API_KEY=your-key-here")
        exit(1)

    return api_key


def extract_paper_content(pdf_path: str) -> str:
    """Extract text content from PDF research paper."""
    print(f"📄 Extracting content from: {pdf_path}")

    paper_content = extract_pdf_text.extract_content_from_pdf(pdf_path)
    paper_text = paper_content['text']

    print(f"   ✓ Extracted {len(paper_text):,} characters")
    print(f"   ✓ Found {len(paper_content['images'])} relevant images")

    return paper_text


def generate_script(client: genai.Client, paper_text: str) -> str:
    """Generate podcast script using Gemini."""
    print(f"\n🤖 Generating podcast script with {MODEL}...")

    # Truncate text if needed
    text_to_use = paper_text[:MAX_TEXT_LENGTH]
    if len(paper_text) > MAX_TEXT_LENGTH:
        print(f"   ⚠ Text truncated to {MAX_TEXT_LENGTH:,} chars")

    prompt = f"""
You are a podcast narrator explaining a research paper to an intelligent but non-expert audience.

Convert the following research paper into an engaging 8–10 minute podcast episode.
- Start with a motivating intro
- Explain the problem and why it matters
- Summarize the key ideas and results
- Avoid equations unless necessary
- Use clear analogies
- End with implications and future work

Paper:
{text_to_use}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text


def save_script(script: str, output_dir: Path) -> Path:
    """Save generated script to file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = output_dir / "podcast_script.txt"

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    return script_path


def main():
    """Main execution flow."""
    print("="*80)
    print("🎙️  Podcast Generator")
    print("="*80)

    # Setup
    api_key = setup_environment()
    client = genai.Client(api_key=api_key)

    # Step 1: Extract PDF content
    paper_text = extract_paper_content(PDF_FILE)

    # Step 2: Generate podcast script
    script = generate_script(client, paper_text)

    # Step 3: Save script
    script_path = save_script(script, OUTPUT_DIR)
    print(f"\n✓ Script saved to: {script_path}")

    # Step 4: Convert to SSML
    print(f"\n🔊 Converting script to SSML...")
    ssml_path = script_to_ssml.convert_script_file(script_path)
    print(f"✓ SSML saved to: {ssml_path}")

    # Display summary
    print("\n" + "="*80)
    print("📊 Summary")
    print("="*80)
    print(f"Script length: {len(script):,} characters")
    print(f"Script file: {script_path}")
    print(f"SSML file: {ssml_path}")
    print("\n✅ Done! You can now use the SSML file with Google Cloud TTS.")


if __name__ == "__main__":
    main()
