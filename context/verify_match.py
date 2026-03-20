"""
verify_match.py

Score how likely a retrieved paper matches a reference.

Inputs:
- ParsedReference
- PaperMatch

Outputs:
- score (0–1)
- confidence (high/medium/low)
- reasons (why low confidence)

Approach:
- title similarity (main signal)
- year match
- first author match

Do not fix mismatches — just flag uncertainty.
"""