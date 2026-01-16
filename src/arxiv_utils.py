import re
import feedparser

def get_arxiv_info(arxiv_id_or_url: str) -> dict:
    # Accept either ID or URL
    if "arxiv.org" in arxiv_id_or_url:
        match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', arxiv_id_or_url)
        if not match:
            raise ValueError("Invalid arXiv URL")
        arxiv_id = match.group(1)
    else:
        arxiv_id = arxiv_id_or_url

    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    feed = feedparser.parse(api_url)

    if not feed.entries:
        raise RuntimeError("No arXiv entry found")

    title = feed.entries[0].title.strip()

    clean_title = re.sub(r'[^\w\s-]', '', title)
    clean_title = re.sub(r'[-\s]+', '_', clean_title)

    return {
        "id": arxiv_id,
        "title": title,
        "title_clean": clean_title[:100],
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    }
