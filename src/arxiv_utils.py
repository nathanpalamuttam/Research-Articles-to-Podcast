import re
import requests
import feedparser

import re
import requests
import feedparser

def get_arxiv_info(arxiv_id_or_url: str) -> dict:
    # ---------- bioRxiv ----------
    # Detect bioRxiv by URL or DOI pattern (10.1101/... or 10.64898/...)
    if "biorxiv.org" in arxiv_id_or_url or re.match(r'^10\.(1101|64898)/', arxiv_id_or_url):
        # Extract paper ID from URL or use the DOI directly
        if "biorxiv.org" in arxiv_id_or_url:
            m = re.search(r"biorxiv\.org/content/(10\.\d{4,9}/[^/?#]+)", arxiv_id_or_url)
            if not m:
                raise ValueError("Invalid bioRxiv URL")
            paper_id = m.group(1)
        else:
            # It's just the DOI
            paper_id = arxiv_id_or_url

        # Strip display suffixes
        paper_id = re.sub(r"(\.full(\.pdf)?|\.full-text)$", "", paper_id)

        # API generally expects DOI without version suffix (v1, v2, ...)
        doi_no_ver = re.sub(r"v\d+$", "", paper_id)

        api_url = f"https://api.biorxiv.org/details/biorxiv/{doi_no_ver}/na/json"
        resp = requests.get(api_url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("collection"):
            raise RuntimeError("No bioRxiv entry found")

        rec = data["collection"][0]
        title = rec["title"].strip()

        clean_title = re.sub(r"[^\w\s-]", "", title)
        clean_title = re.sub(r"[-\s]+", "_", clean_title)

        # PDF URLs on biorxiv use the versioned path (…v1.full.pdf)
        pdf_url = f"https://www.biorxiv.org/content/{paper_id}.full.pdf"

        return {
            "id": paper_id,  # keep same behavior: include vN if present in the URL
            "title": title,
            "title_clean": clean_title[:100],
            "pdf_url": pdf_url,
        }

    # ---------- arXiv ----------
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
