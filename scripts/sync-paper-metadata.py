#!/usr/bin/env python3
"""Synchronize paper-page dates with the date printed on the PDF's first page."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = REPO_ROOT / "papers/robust-narrative-persuasion-draft.pdf"
DEFAULT_HTML = REPO_ROOT / "papers/robust-narrative-persuasion.html"
DEFAULT_SITEMAP = REPO_ROOT / "sitemap.xml"

LANDING_URL = (
    "https://songli-econ.github.io/papers/robust-narrative-persuasion.html"
)
PDF_URL = (
    "https://songli-econ.github.io/papers/"
    "robust-narrative-persuasion-draft.pdf"
)

MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
PDF_DATE_RE = re.compile(
    rf"\b({MONTHS})\s+([0-3]?\d),\s+((?:19|20)\d{{2}})\b"
)


def extract_pdf_date(pdf_path: Path) -> datetime:
    try:
        result = subprocess.run(
            [
                "pdftotext",
                "-f",
                "1",
                "-l",
                "1",
                "-layout",
                str(pdf_path),
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdftotext is required. Install Poppler before running this script."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Could not extract the first page of {pdf_path}: "
            f"{exc.stderr.strip()}"
        ) from exc

    match = PDF_DATE_RE.search(result.stdout)
    if not match:
        raise RuntimeError(
            f"No date in 'Month D, YYYY' format found on the first page of {pdf_path}."
        )

    try:
        return datetime.strptime(match.group(0), "%B %d, %Y")
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date on the first page of {pdf_path}: {match.group(0)}"
        ) from exc


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} marker, found {count}."
        )
    return updated


def update_html(text: str, date: datetime) -> str:
    scholar_date = date.strftime("%Y/%m/%d")
    display_date = f"{date.strftime('%B')} {date.day}, {date.year}"
    display_month = date.strftime("%B %Y")

    text = replace_once(
        text,
        r'(<meta name="citation_publication_date" content=")[^"]+(">.*)',
        rf"\g<1>{scholar_date}\g<2>",
        "citation_publication_date",
    )
    text = replace_once(
        text,
        r'(<meta name="citation_online_date" content=")[^"]+(">.*)',
        rf"\g<1>{scholar_date}\g<2>",
        "citation_online_date",
    )
    text = replace_once(
        text,
        (
            r'(<p class="paper-meta citation_author">'
            r"Song Li\. Working paper\. )"
            r"(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December) \d{1,2}, \d{4}"
            r"(\.</p>)"
        ),
        rf"\g<1>{display_date}\g<2>",
        "visible paper date",
    )
    return replace_once(
        text,
        r"(Last updated )(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December) \d{4}(\.)",
        rf"\g<1>{display_month}\g<2>",
        "landing-page update month",
    )


def update_sitemap_entry(text: str, url: str, iso_date: str) -> str:
    return replace_once(
        text,
        rf"(<loc>{re.escape(url)}</loc>\s*<lastmod>)[^<]+(</lastmod>)",
        rf"\g<1>{iso_date}\g<2>",
        f"sitemap entry for {url}",
    )


def update_sitemap(text: str, date: datetime) -> str:
    iso_date = date.strftime("%Y-%m-%d")
    text = update_sitemap_entry(text, LANDING_URL, iso_date)
    return update_sitemap_entry(text, PDF_URL, iso_date)


def sync_file(path: Path, updated: str, check: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    if original == updated:
        return False
    if not check:
        path.write_text(updated, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--sitemap", type=Path, default=DEFAULT_SITEMAP)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale metadata without changing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date = extract_pdf_date(args.pdf)

    html_original = args.html.read_text(encoding="utf-8")
    sitemap_original = args.sitemap.read_text(encoding="utf-8")
    html_updated = update_html(html_original, date)
    sitemap_updated = update_sitemap(sitemap_original, date)

    changed = []
    if sync_file(args.html, html_updated, args.check):
        changed.append(str(args.html))
    if sync_file(args.sitemap, sitemap_updated, args.check):
        changed.append(str(args.sitemap))

    print(f"PDF date: {date.strftime('%Y-%m-%d')}")
    if not changed:
        print("Paper metadata is already synchronized.")
        return 0

    action = "Stale metadata in" if args.check else "Updated"
    print(f"{action}: {', '.join(changed)}")
    return 1 if args.check else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
