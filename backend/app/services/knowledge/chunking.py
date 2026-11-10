"""Section-aware chunking.

Why this strategy: fixed-size character splits cut explanations in half and mix chapters. Here we
split into sentences, group them up to ~220 words *inside one book section*, and carry a ~40 word
sentence overlap into the next chunk so a definition and its example stay retrievable together.
Every chunk keeps its section title and page range for citation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[\"“])")
_HEADING = re.compile(
    r"^(?:Chapter\s+\d+[:.\s].{0,70}|\d{1,2}(?:\.\d{1,2}){0,2}\s+[A-Z][A-Za-z0-9 ,:;&'()/\-–]{3,70})$"
)
SKIP_SECTIONS = {"index", "references", "bibliography", "acknowledgments", "acknowledgements", "copyright",
                 "contents", "table of contents"}


@dataclass(frozen=True)
class PageText:
    page: int  # 1-based
    text: str


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    section: str
    page_start: int
    page_end: int
    roles: list[str] = field(default_factory=list)


def embedding_text(chunk: Chunk) -> str:
    """Prefix the section title so short chunks still carry their topic into the embedding."""
    return f"{chunk.section}\n{chunk.text}"


def clean_text(raw: str) -> str:
    text = raw.replace("\u00ad", "").replace("\r", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if not re.fullmatch(r"\d{1,4}", ln)]  # bare page numbers
    paragraphs, current = [], []
    for ln in lines:
        if ln:
            current.append(ln)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(re.sub(r"\s+", " ", p) for p in paragraphs)


def make_section_lookup(toc: list, pages: list[PageText]) -> Callable[[int], str]:
    """Prefer the PDF's own table of contents; otherwise detect numbered headings; otherwise bucket pages."""
    if toc:
        entries = sorted((int(p), str(title).strip()) for _, title, p in toc if int(p) > 0)

        def from_toc(page: int) -> str:
            current = None
            for p, title in entries:
                if p <= page:
                    current = title
                else:
                    break
            return current or "Front matter"

        return from_toc

    by_page: dict[int, str | None] = {}
    current, found = None, False
    for pg in pages:
        for line in pg.text.split("\n"):
            s = line.strip()
            if _HEADING.match(s) and not s.endswith("."):
                current, found = s, True
        by_page[pg.page] = current
    if found:
        return lambda page: by_page.get(page) or "Front matter"
    return lambda page: f"Pages {((page - 1) // 10) * 10 + 1}-{((page - 1) // 10) * 10 + 10}"


def _is_prose(text: str) -> bool:
    letters = sum(c.isalpha() for c in text)
    return len(text) > 0 and letters / len(text) >= 0.6 and text.count("....") == 0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:40] or "book"


def _wc(sentence: str) -> int:
    return len(sentence.split())


def build_chunks(
    pages: list[PageText],
    *,
    source: str,
    lookup: Callable[[int], str],
    target_words: int = 220,
    overlap_words: int = 40,
    min_words: int = 60,
    roles: list[str] | None = None,
) -> list[Chunk]:
    units: list[tuple[str, int, str]] = []  # (sentence, page, section)
    for pg in pages:
        section = lookup(pg.page)
        if section.strip().lower() in SKIP_SECTIONS:
            continue
        for para in clean_text(pg.text).split("\n\n"):
            for sent in _SENT_SPLIT.split(para):
                sent = sent.strip()
                if _wc(sent) >= 3:
                    units.append((sent, pg.page, section))

    chunks: list[Chunk] = []
    buf: list[tuple[str, int, str]] = []
    fresh = 0  # words added since the last emit (overlap does not count)

    def emit() -> None:
        if not buf or fresh < min_words // 2:
            return
        text = " ".join(u[0] for u in buf)
        if not _is_prose(text):
            return
        chunks.append(
            Chunk(
                id=f"{_slug(source)}:{len(chunks):05d}",
                text=text,
                source=source,
                section=buf[0][2],
                page_start=buf[0][1],
                page_end=buf[-1][1],
                roles=list(roles or []),
            )
        )

    for unit in units:
        if buf and unit[2] != buf[0][2]:  # never let a chunk straddle two sections
            emit()
            buf, fresh = [], 0
        buf.append(unit)
        fresh += _wc(unit[0])
        if sum(_wc(u[0]) for u in buf) >= target_words:
            emit()
            tail, words = [], 0
            for u in reversed(buf):
                tail.insert(0, u)
                words += _wc(u[0])
                if words >= overlap_words:
                    break
            buf, fresh = tail, 0
    emit()
    return chunks
