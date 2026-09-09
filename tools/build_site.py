#!/usr/bin/env python3
"""Build a static academic website from the LaTeX CV and BibTeX files."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site_src"
OUTPUT = ROOT / "dist"


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def braced(text: str, start: int) -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"Expected '{{' near character {start}")
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == "{" and (pos == 0 or text[pos - 1] != "\\"):
            depth += 1
        elif text[pos] == "}" and (pos == 0 or text[pos - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start + 1 : pos], pos + 1
    raise ValueError("Unbalanced braces in LaTeX source")


def commands(text: str, name: str, arguments: int = 1) -> list[tuple[str, ...]]:
    results: list[tuple[str, ...]] = []
    needle = "\\" + name
    pos = 0
    while True:
        found = text.find(needle, pos)
        if found < 0:
            break
        cursor = found + len(needle)
        values = []
        try:
            for _ in range(arguments):
                value, cursor = braced(text, cursor)
                values.append(value)
        except ValueError:
            pos = found + len(needle)
            continue
        results.append(tuple(values))
        pos = cursor
    return results


ACCENTS = {
    r"\'a": "á", r"\'e": "é", r"\'i": "í", r"\'o": "ó", r"\'u": "ú",
    r"\'A": "Á", r"\'E": "É", r"\'I": "Í", r"\'O": "Ó", r"\'U": "Ú",
    r"\~n": "ñ", r"\~N": "Ñ", r'\"u': "ü", r'\"o': "ö",
    r"\v{s}": "š", r"\v{S}": "Š", r"\v{c}": "č", r"\v{C}": "Č",
    r"\v{z}": "ž", r"\v{Z}": "Ž", r"\c{c}": "ç", r"\c{C}": "Ç",
    r"{\'a}": "á", r"{\'e}": "é", r"{\'i}": "í", r"{\'o}": "ó", r"{\'u}": "ú",
}

COMBINING_ACCENTS = {
    "'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302",
    "~": "\u0303", ".": "\u0307", "=": "\u0304", "u": "\u0306",
    "v": "\u030c", "H": "\u030b", "c": "\u0327", "k": "\u0328",
}


def latex_text(value: str) -> str:
    value = strip_comments(value).strip()
    value = value.replace(r"\underline", "")
    for source, target in ACCENTS.items():
        value = value.replace(source, target)
    value = re.sub(
        r"\{?\\(['\"`\^~=\.uvHck])\{?([A-Za-z])\}?\}?",
        lambda match: unicodedata.normalize("NFC", match.group(2) + COMBINING_ACCENTS[match.group(1)]),
        value,
    )
    value = re.sub(r"\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}", r"\1", value)
    wrappers = ("textbf", "textit", "emph", "underline", "entrytitle", "institution", "headername", "headerline")
    for _ in range(8):
        before = value
        for wrapper in wrappers:
            value = re.sub(rf"\\{wrapper}\s*\{{([^{{}}]*)\}}", r"\1", value)
        if value == before:
            break
    value = re.sub(r"\\textbullet\b", " • ", value)
    value = re.sub(r"\\(?:small|normalsize|bfseries|itshape|par)\b", "", value)
    value = re.sub(r"\\begin\{(?:itemize|enumerate|cvlist)\}|\\end\{(?:itemize|enumerate|cvlist)\}", " ", value)
    value = re.sub(r"\\item\s*", " • ", value)
    value = value.replace(r"\&", "&").replace(r"\%", "%").replace(r"\$", "$")
    value = value.replace("---", "—").replace("--", "–")
    value = re.sub(r"\\\\(?:\[[^]]*\])?", " ", value)
    value = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", "", value)
    value = value.replace("{", "").replace("}", "").replace("~", " ")
    return re.sub(r"\s+", " ", value).strip(" •")


def safe(value: str) -> str:
    return html.escape(latex_text(value), quote=True)


def split_items(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"\\item(?:\s*\[[^]]*\])?\s*", text)[1:] if item.strip()]


def header_data() -> dict[str, object]:
    source = (ROOT / "sections/header.tex").read_text(encoding="utf-8")
    names = commands(source, "headername")
    lines = commands(source, "headerline")
    hrefs = commands(source, "href", 2)
    name = latex_text(names[0][0]) if names else "Academic profile"
    affiliation = latex_text(lines[0][0]) if lines else ""
    links = []
    for url, label in hrefs:
        clean_url = url.strip()
        clean_label = latex_text(label)
        if clean_url.startswith("mailto:"):
            links.append((clean_url, "Email"))
        elif "scholar.google" in clean_url:
            links.append((clean_url, "Google Scholar"))
        elif clean_label:
            links.append((clean_url, clean_label))
    return {"name": name, "affiliation": affiliation, "links": links}


def parse_cvitems(path: Path) -> list[tuple[str, str]]:
    text = strip_comments(path.read_text(encoding="utf-8"))
    return [(latex_text(year), latex_text(body)) for year, body in commands(text, "cvitem", 2)]
    
def parse_research_outputs() -> list[tuple[str, str, str]]:
    path = ROOT / "sections/research_outputs.tex"

    if not path.exists():
        return []

    text = strip_comments(path.read_text(encoding="utf-8"))
    outputs = []

    for year, body in commands(text, "cvitem", 2):
        urls = commands(body, "url")
        url = urls[0][0].strip() if urls else ""

        # Remove \url{...} before converting the remaining LaTeX to text.
        description_source = re.sub(
            r"\\url\s*\{[^{}]*\}",
            "",
            body,
        )
        description = latex_text(description_source)

        # Remove redundant link-introduction text from the card.
        description = re.sub(
            r"\s*(?:Available at|Data and code available at):\s*$",
            "",
            description,
            flags=re.IGNORECASE,
        ).rstrip(". ")

        outputs.append(
            (
                latex_text(year),
                description,
                url,
            )
        )

    return outputs

def parse_talks() -> list[str]:
    text = strip_comments((ROOT / "sections/invited_talks.tex").read_text(encoding="utf-8"))
    match = re.search(r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}", text, re.S)
    return [latex_text(item) for item in split_items(match.group(1) if match else "")]


def parse_service() -> list[tuple[str, list[str]]]:
    text = strip_comments((ROOT / "sections/service.tex").read_text(encoding="utf-8"))
    matches = list(re.finditer(r"\\subsection\{([^{}]+)\}", text))
    groups = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        environment = re.search(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", block, re.S)
        items = [latex_text(item) for item in split_items(environment.group(1) if environment else "")]
        groups.append((latex_text(match.group(1)), items))
    return groups


def bib_entries(path: Path, kind: str) -> list[dict[str, str]]:
    text = strip_comments(path.read_text(encoding="utf-8"))
    entries: list[dict[str, str]] = []
    cursor = 0
    while True:
        match = re.search(r"@(\w+)\s*\{\s*([^,]+),", text[cursor:], re.I)
        if not match:
            break
        start = cursor + match.start()
        open_brace = text.find("{", start)
        try:
            body, end = braced(text, open_brace)
        except ValueError:
            break
        key_end = body.find(",")
        key = body[:key_end].strip()
        fields_text = body[key_end + 1 :]
        fields: dict[str, str] = {"key": key, "entry_type": match.group(1).lower(), "kind": kind}
        pos = 0
        while pos < len(fields_text):
            field_match = re.search(r"([A-Za-z][\w-]*)\s*=\s*", fields_text[pos:])
            if not field_match:
                break
            field = field_match.group(1).lower()
            value_start = pos + field_match.end()
            while value_start < len(fields_text) and fields_text[value_start].isspace():
                value_start += 1
            if value_start < len(fields_text) and fields_text[value_start] == "{":
                try:
                    value, next_pos = braced(fields_text, value_start)
                except ValueError:
                    break
            elif value_start < len(fields_text) and fields_text[value_start] == '"':
                next_quote = fields_text.find('"', value_start + 1)
                if next_quote < 0:
                    break
                value, next_pos = fields_text[value_start + 1 : next_quote], next_quote + 1
            else:
                comma = fields_text.find(",", value_start)
                next_pos = len(fields_text) if comma < 0 else comma
                value = fields_text[value_start:next_pos]
            fields[field] = value.strip()
            pos = next_pos + 1
        entries.append(fields)
        cursor = end
    return entries


def author_html(raw: str) -> str:
    authors = re.split(r"\s+and\s+", raw.strip())
    formatted = []
    for author in authors:
        owner = r"\textbf" in author or "Moro-Velazquez" in author
        supervised = r"\underline" in author
        clean = latex_text(author)
        if "," in clean:
            family, given = [part.strip() for part in clean.split(",", 1)]
            clean = f"{given} {family}"
        escaped = html.escape(clean)
        if supervised:
            escaped = f"<u>{escaped}</u>"
        if owner:
            escaped = f"<strong>{escaped}</strong>"
        formatted.append(escaped)
    return ", ".join(formatted)


def publication_html(entry: dict[str, str]) -> str:
    year = latex_text(entry.get("year", "n.d."))
    title = safe(entry.get("title", "Untitled"))
    venue = safe(entry.get("journal") or entry.get("booktitle") or entry.get("publisher", ""))
    kind = entry["kind"]
    label = "Journal" if kind == "journal" else "Conference"
    doi = latex_text(entry.get("doi", ""))
    url = latex_text(entry.get("url", ""))
    link = ""
    if doi:
        link = f'<a class="publication-link" href="https://doi.org/{quote(doi, safe="/:._-")}">DOI ↗</a>'
    elif url.startswith(("http://", "https://")):
        link = f'<a class="publication-link" href="{html.escape(url, quote=True)}">Paper ↗</a>'
    return (
        f'<article class="publication-card" data-type="{kind}" data-year="{html.escape(year)}">'
        f'<div class="publication-year">{html.escape(year)}</div>'
        f'<div><h4 class="publication-title">{title}</h4>'
        f'<p class="publication-authors">{author_html(entry.get("author", ""))}</p>'
        f'<p class="publication-venue">{venue}</p>{link}</div>'
        f'<span class="publication-kind">{label}</span></article>'
    )


def talk_html(talks: list[str]) -> str:
    cards = []
    for index, talk in enumerate(talks, 1):
        title, separator, detail = talk.partition(". ")
        if not separator:
            title, detail = talk, ""
        cards.append(
            f'<article class="talk-card"><span class="talk-index">{index:02d}</span>'
            f'<h3>{html.escape(title.rstrip("."))}</h3><p>{html.escape(detail)}</p></article>'
        )
    return "".join(cards)


def main() -> None:
    config = json.loads((ROOT / "site_config.json").read_text(encoding="utf-8"))
    header = header_data()
    journals = bib_entries(ROOT / "list.bib", "journal")
    conferences = bib_entries(ROOT / "conferences.bib", "conference")
    publications = journals + conferences
    publications.sort(key=lambda item: int(re.sub(r"\D", "", latex_text(item.get("year", "0"))) or 0), reverse=True)
    by_key = {entry["key"]: entry for entry in publications}
    selected = [by_key[key] for key in config.get("selected_publication_keys", []) if key in by_key]
    if not selected:
        selected = publications[:6]

    research_outputs = parse_research_outputs()
    awards = parse_cvitems(ROOT / "sections/awards.tex")
    talks = parse_talks()
    service = parse_service()
    profile_links = list(header["links"])
    #if os.environ.get("CV_AVAILABLE") == "1" or (ROOT / "main.pdf").exists():
    #    profile_links.insert(1, ("CV_Laureano_Moro-Velazquez.pdf", "Download CV"))

    portrait_file = next((ROOT / "assets" / filename for filename in ("profile.jpg", "profile.jpeg", "profile.png", "profile.webp") if (ROOT / "assets" / filename).exists()), None)
    portrait = (
        f'<img class="portrait" src="assets/{html.escape(portrait_file.name)}" alt="Portrait of {html.escape(str(header["name"]))}">'
        if portrait_file else '<div class="monogram" aria-label="Laureano Moro-Velazquez">LMV</div>'
    )
    themes = "".join(
        f'<article class="theme-card"><span class="theme-number">{html.escape(theme["number"])}</span>'
        f'<h3>{html.escape(theme["title"])}</h3><p>{html.escape(theme["description"])}</p></article>'
        for theme in config["research_themes"]
    )
    awards_html = "".join(
        f'<article class="timeline-item"><div class="timeline-year">{html.escape(year)}</div><p>{html.escape(body)}</p></article>'
        for year, body in awards
    )
    service_html = "".join(
        f'<section class="service-group"><h3>{html.escape(title)}</h3><ul>'
        + "".join(f"<li>{html.escape(item)}</li>" for item in items)
        + "</ul></section>" for title, items in service
    )
    years = sorted({latex_text(entry.get("year", "")) for entry in publications if entry.get("year")}, reverse=True)
    research_outputs_html = "".join(
    f'''
    <article class="timeline-item">
      <div class="timeline-year">{html.escape(year)}</div>
      <div>
        <p>{html.escape(description)}</p>
        {
            f'<a class="publication-link" '
            f'href="{html.escape(url, quote=True)}">'
            f'View resource ↗</a>'
            if url.startswith(("https://", "http://"))
            else ""
        }
      </div>
    </article>
    '''
    for year, description, url in research_outputs
    )    
    replacements = {
        "NAME": html.escape(str(header["name"])), "TITLE": html.escape(config["title"]),
        "AFFILIATION": html.escape(str(header["affiliation"])), "LOCATION": html.escape(config["location"]),
        "SHORT_INTRO": html.escape(config["short_intro"]), "META_DESCRIPTION": html.escape(config["short_intro"], quote=True),
        "ABOUT": html.escape(config["about"]),
        "PROFILE_LINKS": "".join(f'<a class="button-link" href="{html.escape(url, quote=True)}">{html.escape(label)}</a>' for url, label in profile_links),
        "PORTRAIT": portrait, "JOURNAL_COUNT": str(len(journals)), "CONFERENCE_COUNT": str(len(conferences)),
        "LATEST_YEAR": html.escape(years[0] if years else "—"), "RESEARCH_THEMES": themes,
        "SELECTED_PUBLICATIONS": "".join(publication_html(entry) for entry in selected),
        "ALL_PUBLICATIONS": "".join(publication_html(entry) for entry in publications),
        "YEAR_OPTIONS": "".join(f'<option value="{html.escape(year)}">{html.escape(year)}</option>' for year in years),
        "RESEARCH_OUTPUTS": research_outputs_html,
        "AWARDS": awards_html, "TALKS": talk_html(talks), "SERVICE": service_html,
        "UPDATED": html.escape(os.environ.get("SITE_UPDATED", date.today().isoformat())),
    }

    page = (SOURCE / "index.template.html").read_text(encoding="utf-8")
    for key, value in replacements.items():
        page = page.replace("{{" + key + "}}", value)
    unresolved = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if unresolved:
        raise RuntimeError(f"Unresolved template variables: {', '.join(unresolved)}")

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "assets").mkdir(parents=True)
    (OUTPUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copy2(SOURCE / "styles.css", OUTPUT / "styles.css")
    shutil.copy2(SOURCE / "site.js", OUTPUT / "site.js")
    for asset in (ROOT / "assets").iterdir():
        if asset.is_file() and asset.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            shutil.copy2(asset, OUTPUT / "assets" / asset.name)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {OUTPUT / 'index.html'} with {len(publications)} publications")


if __name__ == "__main__":
    main()
