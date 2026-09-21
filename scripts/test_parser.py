#!/usr/bin/env python3
"""
Offline checks for build_boletines.py.

No network. Fixtures are real markup and real page-1 text captured from the
CFMI site, so these catch the things that actually break: the index layout
changing shape, and odd title layouts inside the PDFs.

Run:  python scripts/test_parser.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_boletines import clean_lines, extract_title, parse_index  # noqa: E402

FAILURES = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n       got:  {got!r}\n       want: {want!r}")
        FAILURES.append(name)


# --- index parsing -----------------------------------------------------------
# Mirrors the real page: links repeat across columns, the 2021 issues use a
# month name, there is a stray "Reportaje Especial", and some 2026 labels use
# an underscore or carry a .pdf suffix.
INDEX_FIXTURE = """
<a href="https://www.camaraforestal.org/_files/ugd/3af4fa_74870d.pdf" title="x">Bolet&#237;n 01-Mayo 2021 Bolet&#237;n 01-Mayo 2021</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_7e770b.pdf" title="x">Reportaje Especial Reportaje Especial</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_a8831065.pdf" title="x">Bolet&#237;n 45-2025 Bolet&#237;n 45-2025</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_65836eb4.pdf" title="x">Bolet&#237;n 10_2026.pdf Bolet&#237;n 10_2026.pdf</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_6d8b464b.pdf" title="x">Bolet&#237;n 32-2026.pdf</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_0076a86c.pdf" title="x"><span>Bolet&#237;n 31-2026.pdf</span></a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_4bf27a40.pdf" title="x">Bolet&#237;n 34-2026.pdf Bolet&#237;n 34-2026.pdf</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_63b48ee0.pdf" title="x">Bolet&#237;n 33-2026.pdf</a>
<a href="https://www.camaraforestal.org/_files/ugd/9f1379_4bf27a40.pdf" title="x">Bolet&#237;n 34-2026.pdf</a>
<a href="https://evil.example.com/_files/ugd/9f1379_ffffff.pdf" title="x">Bolet&#237;n 99-2026</a>
"""

print("index parsing")
items = parse_index(INDEX_FIXTURE)
check("newest four, ordered", [(b["n"], b["year"]) for b in items[:4]],
      [(34, 2026), (33, 2026), (32, 2026), (31, 2026)])
check("underscore label parsed", (10, 2026) in [(b["n"], b["year"]) for b in items], True)
check("2021 month-style label skipped", any(b["year"] == 2021 for b in items), False)
check("Reportaje Especial skipped", len(items), 6)
check("off-site pdf rejected",
      any("evil.example.com" in b["url"] for b in items), False)
check("duplicate link not doubled",
      sum(1 for b in items if (b["n"], b["year"]) == (34, 2026)), 1)

# --- title extraction --------------------------------------------------------
# Real page-1 text. Note the two layouts: 34-2026 prints the title below the
# contact line, 33-2026 prints it above.
PAGE1_34 = """Boletín
34-2026
Cámara Forestal Madera e Industria de Costa Rica ■ info@camaraforestal.org ■ 8485-1212
Conocimiento que transforma
a madera en oportunidades
"""

PAGE1_33 = """Boletín
33-2026
Del respaldo internacional
a la inversión
Cámara Forestal Madera e Industria de Costa Rica ■ info@camaraforestal.org ■ 8485-1212
"""

print("\ntitle extraction")
check("furniture stripped (34)", clean_lines(PAGE1_34),
      ["Conocimiento que transforma", "a madera en oportunidades"])
check("title above contact line (33)", " ".join(clean_lines(PAGE1_33)),
      "Del respaldo internacional a la inversión")
check("empty page falls back",
      extract_title(b"%PDF-1.4 not really a pdf", 12, 2026),
      "Boletin 12-2026 · Costa Rica Forestal")

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    raise SystemExit(1)
print("all checks passed")
