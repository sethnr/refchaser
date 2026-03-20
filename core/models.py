from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ParsedReference:
    raw_reference: str
    title: Optional[str] = None
    authors: List[str] | None = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None

@dataclass
class PaperMatch:
    found: bool
    match_score: float
    paper_id: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    authors: List[str] | None = None