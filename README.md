# refchaser

Refchaser takes a scientific paper and builds structured context from its references.

Given a PDF, it:
- extracts the reference list
- parses each citation into structured metadata
- finds the referenced papers (via Semantic Scholar)
- pulls citation context from the main text
- generates short summaries of what each reference contributes

The result is a per-reference “context view” of the paper: what each citation is, whether it appears in the text, and how it is being used.

---

## Why this exists

I'm too lazy to chase down all my references any more

You see:
> “as previously shown (34)”

…and have to:
- scroll
- find the reference
- figure out what it is
- guess why it’s cited

Refchaser does that upfront:
- resolves the reference
- shows where it appears
- summarises its role

---

## What it does

For each reference, refchaser produces:

- **parsed citation** (title, authors, year, DOI)
- **citation context** (snippets from the main text)
- **paper lookup** (matched external record, if found)
- **short summary** (what the cited work is and why it’s used)

---



## Quickstart

### 1. Setup environment
```bash
conda env create -f context-engine-env.yml
conda activate context-engine

export OPENAI_API_KEY=<<key>>
export S2_API_KEY=<<key>>
```
### 2. Run refchaser
```bash
python run_paper_context.py kalinich-et-al-2026.pdf
```
### Example output (simplified)

```json
{
  "reference": "O’Toole et al. 2021...",
  "found_in_main_text": true,
  "context_snippets": [
    "…used to assign viral lineages (3)…"
  ],
  "paper_lookup": {
    "title": "Assignment of epidemiological lineages...",
    "year": 2021
  },
  "summary": "Introduces the pangolin tool used for lineage assignment in viral genomics."
}
```

