# utils/save_urls.py

import os
import re
import requests
import streamlit as st
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import List, Tuple


def slugify(text: str) -> str:
    """Generate a filesystem-safe slug from the given text."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')


def extract_all_visible_text(html: bytes) -> str:
    """
    Extracts all visible text from an HTML document,
    excluding scripts, styles, and other non-content elements.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript", "meta", "iframe"]):
        tag.decompose()

    # Extract text
    raw_text = soup.get_text(separator="\n")

    # Normalize whitespace
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    return "\n\n".join(lines)


def save_url_to_vectordb(
    url: str,
    existing_docs: List[str],
    docs_dir: str = "docs"
) -> Tuple[str, str]:
    """
    Fetch a URL (HTML or PDF), save it to `docs/`, and tell the caller
    what filename was written and of which type.

    Returns:
      (filename, file_type) where file_type is "pdf" or "html".
      If nothing was written (already exists or error), filename == "".
    """
    # 1) Fetch the URL content
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TNTBot/1.0)"},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        st.error(f"❌ Failed to fetch {url}: {e}")
        return "", ""

    # 2) Ensure docs directory exists
    os.makedirs(docs_dir, exist_ok=True)

    # 3) Generate a safe base filename
    parsed = urlparse(url)
    base = slugify(parsed.netloc + parsed.path)

    # 4) Determine content type
    ctype = resp.headers.get("Content-Type", "").lower()
    is_pdf = url.lower().endswith(".pdf") or "application/pdf" in ctype

    if is_pdf:
        fname = f"{base}.pdf"
        if fname in existing_docs:
            return "", "pdf"
        path = os.path.join(docs_dir, fname)
        with open(path, "wb") as f:
            f.write(resp.content)
        st.success(f"✅ Saved PDF to `{path}`")
        return fname, "pdf"

    # --- HTML content branch ---
    text = extract_all_visible_text(resp.content)
    if not text:
        st.warning(f"⚠️ No textual content found at {url}")
        return "", "html"

    fname = f"{base}.txt"
    if fname in existing_docs:
        return "", "html"
    path = os.path.join(docs_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    st.success(f"✅ Saved text to `{path}`")
    return fname, "html"
