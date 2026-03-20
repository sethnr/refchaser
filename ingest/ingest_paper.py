import re
import fitz
import time

from core.call_openai_json import call_openai_json
from core.models import ParsedReference


# ----------------------------
# 1. Extract raw text
# ----------------------------
def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text("text") for page in doc)


# ----------------------------
# 2. Split main vs references
# ----------------------------
def split_main_text_and_references(full_text: str):
    patterns = [
        "\nReferences\n",
        "\nREFERENCES\n",
        "\nBibliography\n",
    ]

    for p in patterns:
        m = re.search(p, full_text)
        if m:
            return full_text[:m.start()], full_text[m.start():]

    return full_text, ""


# ----------------------------
# 3. Extract references with LLM
# ----------------------------
def extract_references(reference_text: str):
    prompt = f"""
Extract references as JSON array with:
raw_reference, title, authors, year, venue, doi.

Text:
{reference_text[:50000]}
"""

    data, _ = call_openai_json(prompt)

    # handle weird nested list outputs
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
        data = data[0]

    refs = []

    for r in data:
        if not isinstance(r, dict):
            continue

        refs.append(
            ParsedReference(
                raw_reference=r.get("raw_reference", ""),
                title=r.get("title"),
                authors=r.get("authors") or [],
                year=r.get("year"),
                venue=r.get("venue"),
                doi=r.get("doi"),
            )
        )

    return refs


# ----------------------------
# 4. determine ref style
# ----------------------------
def detect_citation_style_from_references(reference_text):
    lines = [l.strip() for l in reference_text.split("\n") if l.strip()][:20]

    numeric_hits = 0
    author_date_hits = 0

    for l in lines:
        if re.match(r"^\d+\s*[\.\)]?", l):
            numeric_hits += 1
        elif re.match(r"^[A-Z][a-zA-Z\-']+", l) and re.search(r"\(\d{4}\)", l):
            author_date_hits += 1

    print(f"DEBUG numeric={numeric_hits}, author_date={author_date_hits}")

    if numeric_hits >= 3:
        return "numeric"

    if author_date_hits >= 3:
        return "author_date"

    return "unknown"


# ----------------------------
# 5. Public entrypoint
# ----------------------------
def ingest_paper(pdf_path: str):
    start = time.time()
    text = extract_text_from_pdf(pdf_path)
    print(f"PDF read: {time.time() - start:.2f}s")

    start = time.time()
    main_text, reference_text = split_main_text_and_references(text)

    # normalise whitespace in main text
    main_text = main_text.replace("\n", " ")
    main_text = re.sub(r"\s+", " ", main_text)

    print(f"Split: {time.time() - start:.2f}s")

    start = time.time()

    citation_style = detect_citation_style_from_references(reference_text)
    references = extract_references(reference_text)

    print(f"Reference extraction: {time.time() - start:.2f}s")

    return main_text, references, citation_style