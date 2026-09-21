#!/usr/bin/env python3
"""
Build boletines.json for the ICOMadera Recursos page.

Reads the Camara Forestal (CFMI) bulletin index, finds the newest four
boletines, pulls a title out of each PDF, and writes boletines.json.

Run:  python scripts/build_boletines.py
Deps: requests, pdfminer.six

Nothing here needs credentials. Everything it reads is public.
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from pdfminer.high_level import extract_text

INDEX_URL = "https://www.camaraforestal.org/bolet%C3%ADn-informativo"

# Only ever trust PDF links served from this prefix.
PDF_PREFIX = "https://www.camaraforestal.org/_files/ugd/"

HOW_MANY = 4
TIMEOUT = 60
UA = "ICOMadera-boletines-bot/1.0 (+https://github.com/ICOMadera/boletines)"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "boletines.json"
OVERRIDES_PATH = ROOT / "overrides.json"

# Link labels look like "Boletin 34-2026", "Boletin 10_2026.pdf", "Boletin 09-2026".
# The 2021 bulletins use a month name instead ("Boletin 01-Mayo 2021") and are
# deliberately not matched -- they predate the current numbering.
LABEL_RE = re.compile(
    r"Bolet\s*[ií]n\s*(?P<num>\d{1,3})\s*[-_‐-―]\s*(?P<year>20\d{2})",
    re.IGNORECASE,
)
ANCHOR_RE = re.compile(
    r'<a\b[^>]*href="(?P<href>[^"]+\.pdf)"[^>]*>(?P<text>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Lines that are page furniture rather than the article title.
BOILERPLATE_PATTERNS = (
    "camara forestal madera e industria",
    "info@camaraforestal.org",
    "8485-1212",
    "8485 1212",
    "costa rica forestal",
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def fetch(url: str) -> bytes:
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
    resp.raise_for_status()
    return resp.content


def parse_index(page_html: str) -> list[dict]:
    """Return [{n, year, url}] for every boletin link on the index page.

    The website's LABEL number is authoritative. CFMI's file labels sometimes
    disagree with the number printed inside the PDF, and the label is what
    readers see, so never re-derive the number from the PDF text.
    """
    found: dict[tuple[int, int], str] = {}

    for m in ANCHOR_RE.finditer(page_html):
        href = html.unescape(m.group("href")).strip()
        if not href.startswith(PDF_PREFIX):
            continue

        # Anchor text is usually the label repeated twice; tags stripped out.
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group("text")))
        label = LABEL_RE.search(text)
        if not label:
            continue

        n = int(label.group("num"))
        year = int(label.group("year"))
        # First occurrence wins; the index repeats links in several columns.
        found.setdefault((n, year), href)

    items = [{"n": n, "year": y, "url": url} for (n, y), url in found.items()]
    items.sort(key=lambda b: (b["year"], b["n"]), reverse=True)
    return items


def clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        low = strip_accents(line).lower()
        if any(p in low for p in (strip_accents(b) for b in BOILERPLATE_PATTERNS)):
            continue
        if re.fullmatch(r"Bolet\s*[ií]n", line, re.IGNORECASE):
            continue
        if LABEL_RE.fullmatch(line.strip()):
            continue
        if re.fullmatch(r"\d{1,3}\s*[-_‐-―]\s*20\d{2}", line):
            continue
        if re.fullmatch(r"\d{1,3}", line):  # page number
            continue
        lines.append(line)
    return lines


def extract_title(pdf_bytes: bytes, n: int, year: int) -> str:
    """Pull the cover title off page 1.

    Layout varies: some issues print the title above the contact line, some
    below it. Stripping the furniture and taking what is left handles both.
    Anything that comes out implausible falls back to a generic label, and a
    human can pin the real title in overrides.json.
    """
    generic = f"Boletin {n}-{year} · Costa Rica Forestal"
    try:
        raw = extract_text(io.BytesIO(pdf_bytes), page_numbers=[0]) or ""
    except Exception as exc:  # noqa: BLE001 - a bad PDF must not kill the run
        log(f"  ! could not read PDF text for {n}-{year}: {exc}")
        return generic

    lines = clean_lines(raw)
    if not lines:
        return generic

    # Take consecutive lines until the title is long enough to stand alone.
    title_parts: list[str] = []
    for line in lines[:6]:
        title_parts.append(line)
        if len(" ".join(title_parts)) >= 60:
            break

    title = " ".join(title_parts).strip(" .;,-–—")
    title = " ".join(title.split())

    if not (15 <= len(title) <= 220):
        log(f"  ! title for {n}-{year} looked implausible ({len(title)} chars)")
        return generic
    return title


def load_overrides() -> dict:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log(f"! overrides.json is not valid JSON ({exc}); ignoring it")
        return {}
    return data.get("titles", {}) if isinstance(data, dict) else {}


def main() -> int:
    log(f"Reading {INDEX_URL}")
    page_html = fetch(INDEX_URL).decode("utf-8", errors="replace")

    all_items = parse_index(page_html)
    if not all_items:
        log("! no boletin links matched -- the page layout probably changed.")
        log("! leaving boletines.json untouched.")
        return 1

    newest = all_items[:HOW_MANY]
    log(f"Found {len(all_items)} boletines; newest: "
        + ", ".join(f"{b['n']}-{b['year']}" for b in newest))

    overrides = load_overrides()
    out = []
    for b in newest:
        key = f"{b['n']}-{b['year']}"
        if key in overrides:
            title = str(overrides[key]).strip()
            log(f"  {key}: using override")
        else:
            log(f"  {key}: reading PDF")
            try:
                title = extract_title(fetch(b["url"]), b["n"], b["year"])
            except Exception as exc:  # noqa: BLE001
                log(f"  ! download failed for {key}: {exc}")
                title = f"Boletin {b['n']}-{b['year']} · Costa Rica Forestal"
        out.append({"n": b["n"], "year": b["year"], "title": title, "url": b["url"]})

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": INDEX_URL,
        "boletines": out,
    }

    # Compare ignoring the timestamp so unchanged weeks produce no commit.
    if OUT_PATH.exists():
        try:
            prev = json.loads(OUT_PATH.read_text(encoding="utf-8"))
            if prev.get("boletines") == payload["boletines"]:
                log("No change -- boletines.json already current.")
                return 0
        except json.JSONDecodeError:
            pass

    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(f"Wrote {OUT_PATH.name}")
    for b in out:
        log(f"  {b['n']}-{b['year']}: {b['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
