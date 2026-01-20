"""
Generate podcast audio from arXiv research papers.

Pipeline:
1. Read arXiv links from arxiv_links.txt
2. Download PDFs for new links
3. Extract text from PDF
4. Generate script using Gemini
5. Synthesize to MP3 using Google Cloud TTS
6. Publish episode to R2 and update podcast feed
"""

import os
import re
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.cloud import texttospeech
import PyPDF2
import feedparser
from arxiv_utils import get_arxiv_info


# ============================================================================
# Configuration
# ============================================================================

ARXIV_LINKS_FILE = "arxiv_links.txt"
PROCESSED_LINKS_FILE = "processed_links.txt"
PDF_DIR = Path("downloads/pdfs")
OUTPUT_DIR = Path("outputs/audio")
SCRIPTS_DIR = Path("outputs/scripts")
MODEL = "models/gemini-2.5-flash"
VOICE_NAME = "en-US-Studio-O"
SPEAKING_RATE = 1.0
MAX_TEXT_LENGTH = 30000


# ============================================================================
# Helper Functions
# ============================================================================

def clean_script(script: str) -> str:
    """Clean script text for TTS."""
    lines = script.splitlines()
    clean_lines = []

    for line in lines:
        line = line.strip()

        # Skip stage directions
        if "Intro Music" in line or "Sound of" in line or "Outro music" in line:
            continue
        if line.startswith("(") and line.endswith(")"):
            continue

        # Clean formatting
        clean = (
            line.replace("**", "")
                .replace("Narrator:", "")
                .replace("*", "")
                .strip()
        )

        if clean:
            clean_lines.append(clean)

    return " ".join(clean_lines)




def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
    return False


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF."""
    text_content = []

    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)

        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)

    full_text = '\n\n'.join(text_content)

    # Remove references section
    references_patterns = [
        r'\n\s*References\s*\n.*',
        r'\n\s*Bibliography\s*\n.*',
        r'\n\s*Works Cited\s*\n.*',
    ]

    for pattern in references_patterns:
        full_text = re.split(pattern, full_text, flags=re.IGNORECASE | re.DOTALL)[0]

    return full_text[:MAX_TEXT_LENGTH]


def generate_script(api_key: str, paper_text: str) -> str:
    """Generate podcast script using Gemini."""
    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a podcast narrator explaining a research paper to an intelligent, technically literate audience.
Assume the listener is comfortable with biology, machine learning, and basic statistics, but is not
an expert in this specific subfield.

TASK:
Convert the following research paper into a spoken narration whose primary goal is deep understanding.
The narration may be longer than 8–10 minutes if needed to fully explain the methods.

STRICT FORMAT REQUIREMENTS:
- Output ONLY the spoken narration text
- Do NOT include music cues, sound effects, transitions, or stage directions
- Do NOT include labels like “Narrator:” or formatting markers
- Do NOT include headings, bullet points, or markdown
- Write in complete, conversational sentences suitable for text-to-speech
- The output should be plain text only

CONTENT GUIDELINES (VERY IMPORTANT):
- Begin with a brief introduction that frames the scientific problem and why it is difficult
- Spend minimal time on high-level hype; prioritize technical substance
- Explain the methodological pipeline in detail:
  * how data was constructed and curated
  * how targets were selected and split
  * how blind evaluation was enforced
  * what information models were and were not allowed to use
- Explain the evaluation metrics precisely, including what they measure and why they were chosen
- Walk through the major classes of approaches used in the paper:
  * human-guided methods
  * deep learning methods
  * template-based modeling methods
- For template-based modeling, explain how templates are found, ranked, aligned, and reused
- Explain how top-performing models differed from baselines at an algorithmic level
- Clearly describe the RNAPro model and how it integrates templates, MSAs, and neural networks
- Discuss ablation results and what they reveal about where performance actually comes from
- Be explicit about failure cases, limitations, and what the methods do NOT yet solve
- Use analogies only when they clarify a technical mechanism, not as a substitute for explanation
- Conclude with implications for RNA biology, benchmarking culture, and future model development

STYLE:
- Assume the listener wants to truly understand how the system works
- It is acceptable to be technical, detailed, and dense
- Avoid oversimplification
- Maintain a natural spoken flow suitable for long-form listening

PAPER:
{paper_text}
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text


def synthesize_audio(text: str, output_path: Path):
    """Convert text to MP3 using chunked synthesis (handles long audio)."""
    client = texttospeech.TextToSpeechClient()

    MAX_CHARS = 4500
    chunks = []
    sentences = text.split('. ')
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip() + '.'
        if current_length + len(sentence) > MAX_CHARS and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(sentence)
        current_length += len(sentence)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    print(f"   Processing {len(chunks)} audio chunks...")

    # Synthesize each chunk using plain text
    audio_parts = []
    for i, chunk in enumerate(chunks):
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=VOICE_NAME
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=SPEAKING_RATE
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        audio_parts.append(response.audio_content)
        print(f"   ✓ Chunk {i+1}/{len(chunks)} complete")

    # Combine audio parts
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for part in audio_parts:
            f.write(part)

    print(f"   ✓ Audio saved to: {output_path}")


def get_new_links() -> list:
    """Get new arXiv links that haven't been processed."""
    # Read all links
    if not Path(ARXIV_LINKS_FILE).exists():
        print(f"❌ {ARXIV_LINKS_FILE} not found")
        return []

    with open(ARXIV_LINKS_FILE, 'r') as f:
        all_links = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Read processed links
    processed = set()
    if Path(PROCESSED_LINKS_FILE).exists():
        with open(PROCESSED_LINKS_FILE, 'r') as f:
            processed = set(line.strip() for line in f if line.strip() and not line.startswith('#'))

    # Find new links
    new_links = [link for link in all_links if link not in processed]
    return new_links


def mark_as_processed(link: str):
    """Mark a link as processed."""
    with open(PROCESSED_LINKS_FILE, 'a') as f:
        f.write(f"{link}\n")


def process_paper(arxiv_url: str, api_key: str):
    """Process a single arXiv paper."""
    print(f"\n{'='*80}")
    print(f"📄 Processing: {arxiv_url}")
    print('='*80)

    # Get paper info
    print("📋 Fetching paper metadata...")
    info = get_arxiv_info(arxiv_url)
    if not info:
        print("   ❌ Failed to get paper info")
        return False

    print(f"   ✓ Title: {info['title']}")
    print(f"   ✓ arXiv ID: {info['id']}")

    # Download PDF
    pdf_path = PDF_DIR / f"{info['title']}.pdf"
    if not pdf_path.exists():
        print(f"\n📥 Downloading PDF...")
        if not download_pdf(info['pdf_url'], pdf_path):
            print("   ❌ Download failed")
            return False
        print(f"   ✓ Downloaded to: {pdf_path}")
    else:
        print(f"\n📥 PDF already exists: {pdf_path}")

    # Extract text
    print(f"\n📄 Extracting text from PDF...")
    paper_text = extract_text_from_pdf(str(pdf_path))
    print(f"   ✓ Extracted {len(paper_text):,} characters")

    # Generate script
    print(f"\n🤖 Generating podcast script with {MODEL}...")
    script = generate_script(api_key, paper_text)
    print("   ✓ Script generated")

    # Save raw script
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    script_filename = f"{info['title']}_script.txt"
    script_path = SCRIPTS_DIR / script_filename
    script_path.write_text(script, encoding='utf-8')
    print(f"   ✓ Script saved to: {script_path}")

    # Clean script
    print("\n📝 Cleaning script...")
    clean_text = clean_script(script)
    print("   ✓ Script cleaned")

    # Synthesize audio
    audio_filename = f"{info['title']}_podcast.mp3"
    audio_path = OUTPUT_DIR / audio_filename

    print(f"\n🔊 Synthesizing audio...")
    synthesize_audio(clean_text, audio_path)

    # Summary
    file_size = audio_path.stat().st_size / 1024 / 1024
    print(f"\n{'='*80}")
    print("✅ Podcast Generated!")
    print('='*80)
    print(f"Audio file: {audio_path}")
    print(f"File size: {file_size:.2f} MB")

    # Publish episode to R2 and update podcast feed
    print(f"\n{'='*80}")
    print("📤 Publishing episode...")
    print('='*80)

    try:
        # Get the path to publish_episode.py (in same directory as this script)
        publish_script = Path(__file__).parent / "publish_episode.py"

        # Run publish_episode.py with the arXiv ID
        result = subprocess.run(
            ["python3", str(publish_script), "--arxiv", info['id']],
            capture_output=True,
            text=True,
            check=True
        )

        # Print the output from publish_episode.py
        print(result.stdout)
        print("✅ Episode published successfully!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to publish episode: {e}")
        print(f"Error output: {e.stderr}")
        print("⚠️  Podcast was generated but not published. You can manually run:")
        print(f"   python3 src/publish_episode.py --arxiv {info['id']}")
        # Still return True since the podcast was successfully generated

    return True


# ============================================================================
# Main Pipeline
# ============================================================================

def main():
    """Process all new arXiv papers."""
    print("="*80)
    print("🎙️  arXiv Podcast Generator")
    print("="*80)

    # Load API key
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
        exit(1)

    # Get new links
    new_links = get_new_links()

    if not new_links:
        print("\n✅ No new arXiv links to process")
        print(f"Add links to {ARXIV_LINKS_FILE}")
        return

    print(f"\n📚 Found {len(new_links)} new paper(s) to process")

    # Process each paper
    for i, link in enumerate(new_links, 1):
        print(f"\n[{i}/{len(new_links)}]")
        try:
            if process_paper(link, api_key):
                mark_as_processed(link)
                print(f"\n✓ Marked as processed: {link}")
        except Exception as e:
            print(f"\n❌ Error processing {link}: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"🎉 All done! Processed {len(new_links)} paper(s)")
    print('='*80)


if __name__ == "__main__":
    main()
