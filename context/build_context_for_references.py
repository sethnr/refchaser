import re
from unittest import result
import requests
import time
import os
from core.call_openai_json import call_openai_json
from core.models import PaperMatch
import json
from pathlib import Path

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


# ----------------------------
# 0. S2 reference cache
# ----------------------------
CACHE_PATH = Path("s2_cache.json")

if CACHE_PATH.exists():
    with open(CACHE_PATH) as f:
        CACHE = json.load(f)
else:
    CACHE = {}

def normalize_doi(doi):
    if not doi:
        return None
    doi = doi.lower().strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi

def build_cache_key(ref, query):
    doi = normalize_doi(getattr(ref, "doi", None))
    if doi:
        return f"doi:{doi}"

    # fallback: normalized query
    return f"query:{query.lower().strip()}"    

def cache_get(key):
    if key in CACHE:
        return PaperMatch(**CACHE[key])
    return None

def cache_set(key, result):
    CACHE[key] = result

# ----------------------------
# 1. Find citation context
# ----------------------------
def find_citation_context_author(main_text, ref, pre_window=200, post_window=80):
    hits = []
    patterns = []

    if ref.authors and ref.year:
        surname = ref.authors[0].split()[-1]

        patterns.extend([
            rf"{surname}[^.\n]{{0,50}}{ref.year}",        # Smith ... 2020
            rf"{ref.year}[^.\n]{{0,50}}{surname}",        # 2020 ... Smith
            rf"\({surname}.*?{ref.year}\)",              # (Smith et al., 2020)
            rf"{surname} et al\.?,? {ref.year}",         # Smith et al. 2020
        ])
    
    for pattern in patterns:
        for m in re.finditer(pattern, main_text, re.IGNORECASE):
            start = max(0, m.start() - pre_window)
            end = min(len(main_text), m.end() + post_window)

            snippet = main_text[start:end].replace("\n", " ")
            snippet = re.sub(r"\s+", " ", snippet)

            hits.append(snippet)

            if len(hits) >= 3:
                break

        if hits:
            break   # ← stop once we find matches
            
    return {
        "found_in_main_text": len(hits) > 0,
        "context_snippets": hits[:3],
    }

def find_citation_context_numeric(main_text, ref_number, pre_window=200, post_window=80):
    import re

    pattern = r"\(\s*\d+([,\-–]\d+)*\s*\)"
    hits = []

    for m in re.finditer(pattern, main_text):
        citation = m.group()

        nums = [int(n) for n in re.findall(r"\d+", citation)]

        if ref_number not in nums:
            continue

        start = max(0, m.start() - pre_window)
        end = min(len(main_text), m.end() + post_window)

        snippet = main_text[start:end].replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet)

        hits.append(snippet)

        if len(hits) >= 3:
            break

    return {
        "found_in_main_text": len(hits) > 0,
        "context_snippets": hits,
    }

# ----------------------------
# 2. Search paper
# ----------------------------

# Query builders
def query_numeric(ref):
    return ref.title or ref.raw_reference


def query_author(ref):
    if ref.title:
        return ref.title
    if ref.authors:
        return f"{ref.authors[0]} {ref.year}"
    return ref.raw_reference


# Master search function
def search_paper(ref, citation_style="numeric", max_retries=3):
    headers = {}
    if os.getenv("S2_API_KEY"):
        headers["x-api-key"] = os.getenv("S2_API_KEY")

    # Get query
    if citation_style == "author_date":
        query = query_author(ref)
    else:
        query = query_numeric(ref)

    params = {
        "query": query,
        "limit": 3,
        "fields": "title,year,abstract,authors,url",
    }


    # ----------------------------
    # Check cache for prior search result
    # ----------------------------
    key = build_cache_key(ref, query)

    cached = cache_get(key)
    if cached:
        print("-", end="", flush=True)
        return cached


    # ----------------------------
    # Execute request with retry
    # ----------------------------
    

    for attempt in range(max_retries):
        r = requests.get(S2_URL, params=params, headers=headers)

        if r.status_code == 200:
            print("+", end="", flush=True)
            break

        if r.status_code == 429:
            print(".", end="", flush=True)
            time.sleep(2 ** attempt)
            continue

        r.raise_for_status()
    else:
        return PaperMatch(found=False, match_score=0)

    data = r.json().get("data", [])
    if not data:
        return PaperMatch(found=False, match_score=0)

    # ----------------------------
    # Select best match
    # ----------------------------
    best = None
    best_score = 0

    for cand in data:
        score = 0

        if ref.title and cand.get("title"):
            if ref.title.lower() in cand["title"].lower():
                score += 1

        if ref.year == cand.get("year"):
            score += 0.5

        if score > best_score:
            best = cand
            best_score = score

    if best:
        result = {
            "found": True,
            "match_score": best_score,
            "title": best.get("title"),
            "year": best.get("year"),
            "abstract": best.get("abstract"),
            "url": best.get("url"),
            "authors": [a["name"] for a in best.get("authors", [])],
        }

        cache_set(key, result)
        return PaperMatch(**result)

    result = {"found": False, "match_score": 0}
    cache_set(key, result)
    return PaperMatch(**result)

# ----------------------------
# 3. Summarise linked paper
# ----------------------------
def summarise_linked_paper(ref, match, context_snippets):
    if not match.found:
        return "Paper not found.", 0

    prompt = f"""
Return JSON with:
- summary

Summarise what this referenced paper is about and what role it plays.

Reference:
{ref.raw_reference}

Abstract:
{match.abstract}

Citation context:
{" ".join(context_snippets[:2])}
"""

    result, usage = call_openai_json(prompt)
    summary = result.get("summary", "")

    return summary, usage["cost_usd"]

# ----------------------------
# 4. Build full context
# ----------------------------
def build_context_for_references(main_text, references, style):
    results = []
    total_cost = 0

    for i, ref in enumerate(references, start=1):

        if style == "numeric":
            ctx = find_citation_context_numeric(main_text, i)
        elif style == "author_date":
            ctx = find_citation_context_author(main_text, ref)
        else:
            ctx = {"found_in_main_text": False, "context_snippets": []}

        paper = search_paper(ref)
        summary, cost = summarise_linked_paper(ref, paper, ctx["context_snippets"])
        total_cost += cost

        results.append({
            "reference": ref.__dict__,
            "citation_context": ctx,
            "paper_lookup": paper.__dict__,
            "linked_paper_summary": summary,
        })
    print("\n", end="", flush=True) # newline after progress indicators
            
    with open(CACHE_PATH, "w") as f:
        json.dump(CACHE, f)

    return results, total_cost