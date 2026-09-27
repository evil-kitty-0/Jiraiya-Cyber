#!/usr/bin/env python3

import sys
import re
import json
import html
import urllib.request
import urllib.parse
from html.parser import HTMLParser


# ============================================================
# CONFIG
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 15) "
    "AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"
)

TIMEOUT = 15

MAX_SEARCH_RESULTS = 8
MAX_PAGE_CHARS = 12000


# ============================================================
# HTTP
# ============================================================

def fetch_url(url, timeout=TIMEOUT):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:

        data = response.read()

        charset = response.headers.get_content_charset()

        if charset:
            encoding = charset
        else:
            encoding = "utf-8"

        return data.decode(
            encoding,
            errors="ignore"
        )


# ============================================================
# HTML PARSER
# ============================================================

class PageParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.title = []
        self.text = []

        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None

        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "noscript",
            "svg"
        }:
            self.skip_depth += 1
            return

        if self.skip_depth:
            return

        if tag == "title":
            self.current_title = True
        else:
            self.current_title = False

        if tag == "table":
            self.current_table = []

        elif tag == "tr" and self.current_table is not None:
            self.current_row = []

        elif tag in {"td", "th"}:
            self.current_cell = []

    def handle_endtag(self, tag):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "noscript",
            "svg"
        }:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if self.skip_depth:
            return

        if tag in {"td", "th"}:

            if (
                self.current_cell is not None
                and self.current_row is not None
            ):
                value = clean_text(
                    " ".join(
                        self.current_cell
                    )
                )

                self.current_row.append(value)

            self.current_cell = None

        elif tag == "tr":

            if (
                self.current_row is not None
                and self.current_table is not None
            ):
                if any(self.current_row):
                    self.current_table.append(
                        self.current_row
                    )

            self.current_row = None

        elif tag == "table":

            if (
                self.current_table is not None
                and self.current_table
            ):
                self.tables.append(
                    self.current_table
                )

            self.current_table = None

    def handle_data(self, data):

        if self.skip_depth:
            return

        value = clean_text(data)

        if not value:
            return

        if getattr(
            self,
            "current_title",
            False
        ):
            self.title.append(value)

        if self.current_cell is not None:

            self.current_cell.append(value)

        else:

            self.text.append(value)


def clean_text(text):

    text = html.unescape(
        str(text)
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# READ WEB PAGE
# ============================================================

def read_page(url):

    try:

        raw = fetch_url(url)

        parser = PageParser()

        parser.feed(raw)

        title = clean_text(
            " ".join(parser.title)
        )

        text = clean_text(
            " ".join(parser.text)
        )

        return {
            "ok": True,
            "url": url,
            "title": title,
            "text": text[:MAX_PAGE_CHARS],
            "tables": parser.tables
        }

    except Exception as exc:

        return {
            "ok": False,
            "url": url,
            "title": "",
            "text": "",
            "tables": [],
            "error": str(exc)
        }


# ============================================================
# TEXT TOKENIZATION
# ============================================================

STOP_WORDS = {
    "what", "is", "are", "was", "were",
    "the", "a", "an", "of", "to", "for",
    "in", "on", "at", "and", "or",
    "how", "why", "when", "where",
    "which", "who", "does", "do",
    "can", "could", "would", "should",
    "tell", "me", "about", "please",

    "kya", "hai", "h", "ka", "ke", "ki",
    "ko", "me", "mein", "batao", "btao",
    "hota", "hoti", "hain"
}


def normalize(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\u0900-\u097f\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokens(text):

    return {
        word
        for word in normalize(text).split()
        if len(word) >= 3
        and word not in STOP_WORDS
    }


def relevance_score(query, text):

    q = tokens(query)
    t = tokens(text)

    if not q or not t:
        return 0.0

    return len(q & t) / len(q)


# ============================================================
# GOOGLE SEARCH
# ============================================================

def google_search(query):

    encoded = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://www.google.com/search"
        f"?q={encoded}&num=10"
    )

    try:

        raw = fetch_url(url)

    except Exception:
        return []

    # Google sometimes returns an access/help page
    # instead of actual search results.
    if (
        "If you're having trouble accessing Google Search"
        in raw
    ):
        return []

    results = []

    # --------------------------------------------------------
    # Result blocks
    # --------------------------------------------------------

    patterns = [
        r'<a href="/url\?q=(https?://[^&"]+)[^"]*"[^>]*>(.*?)</a>',
        r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>'
    ]

    seen = set()

    for pattern in patterns:

        matches = re.findall(
            pattern,
            raw,
            flags=re.I | re.S
        )

        for url, title_html in matches:

            if len(results) >= MAX_SEARCH_RESULTS:
                break

            url = html.unescape(
                urllib.parse.unquote(url)
            )

            title = re.sub(
                r"<[^>]+>",
                " ",
                title_html
            )

            title = clean_text(title)

            if not url.startswith("http"):
                continue

            if (
                "google.com" in url
                or "accounts.google.com" in url
            ):
                continue

            if url in seen:
                continue

            seen.add(url)

            results.append({
                "title": title,
                "url": url,
                "source": "Google"
            })

    return results


# ============================================================
# BING SEARCH
# ============================================================

def bing_search(query):

    encoded = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://www.bing.com/search"
        f"?q={encoded}&count=10"
    )

    try:

        raw = fetch_url(url)

    except Exception:
        return []

    results = []

    pattern = (
        r'<li class="b_algo".*?>'
        r'.*?<h2>.*?'
        r'<a href="([^"]+)"[^>]*>'
        r'(.*?)</a>'
    )

    matches = re.findall(
        pattern,
        raw,
        flags=re.I | re.S
    )

    seen = set()

    for url, title_html in matches:

        if len(results) >= MAX_SEARCH_RESULTS:
            break

        title = re.sub(
            r"<[^>]+>",
            " ",
            title_html
        )

        title = clean_text(title)

        if not url.startswith("http"):
            continue

        if url in seen:
            continue

        seen.add(url)

        results.append({
            "title": title,
            "url": html.unescape(url),
            "source": "Bing"
        })

    return results


# ============================================================
# DUCKDUCKGO HTML SEARCH
# ============================================================

def duckduckgo_search(query):

    encoded = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://html.duckduckgo.com/html/"
        f"?q={encoded}"
    )

    try:

        raw = fetch_url(url)

    except Exception:
        return []

    results = []

    pattern = (
        r'class="result__a"[^>]*href="([^"]+)"'
        r'[^>]*>(.*?)</a>'
    )

    matches = re.findall(
        pattern,
        raw,
        flags=re.I | re.S
    )

    seen = set()

    for url, title_html in matches:

        if len(results) >= MAX_SEARCH_RESULTS:
            break

        title = re.sub(
            r"<[^>]+>",
            " ",
            title_html
        )

        title = clean_text(title)

        url = html.unescape(url)

        # DDG can return redirect links.
        if "uddg=" in url:

            parsed = urllib.parse.urlparse(
                url
            )

            params = urllib.parse.parse_qs(
                parsed.query
            )

            if "uddg" in params:
                url = params["uddg"][0]

        if not url.startswith("http"):
            continue

        if url in seen:
            continue

        seen.add(url)

        results.append({
            "title": title,
            "url": url,
            "source": "DuckDuckGo"
        })

    return results


# ============================================================
# SEARCH RESULT FILTER
# ============================================================

def filter_results(query, results):

    filtered = []

    seen_urls = set()

    for result in results:

        url = result.get("url", "")

        if not url:
            continue

        if url in seen_urls:
            continue

        title = result.get(
            "title",
            ""
        )

        score = relevance_score(
            query,
            title
        )

        result = dict(result)

        result["relevance"] = round(
            score,
            3
        )

        filtered.append(result)

        seen_urls.add(url)

    filtered.sort(
        key=lambda x: x.get(
            "relevance",
            0
        ),
        reverse=True
    )

    return filtered


# ============================================================
# GENERAL WEB SEARCH
# ============================================================

def search_web(query):

    query = clean_text(query)

    if not query:
        return []

    all_results = []

    # --------------------------------------------------------
    # Google
    # --------------------------------------------------------

    all_results.extend(
        google_search(query)
    )

    # --------------------------------------------------------
    # Bing fallback
    # --------------------------------------------------------

    if len(all_results) < 3:

        all_results.extend(
            bing_search(query)
        )

    # --------------------------------------------------------
    # DuckDuckGo fallback
    # --------------------------------------------------------

    if len(all_results) < 3:

        all_results.extend(
            duckduckgo_search(query)
        )

    results = filter_results(
        query,
        all_results
    )

    return results[:MAX_SEARCH_RESULTS]


# ============================================================
# GOLD ENGINE
# ============================================================

CITY_SLUGS = {
    "lucknow": "lucknow",
    "delhi": "delhi",
    "mumbai": "mumbai",
    "kolkata": "kolkata",
    "chennai": "chennai",
    "hyderabad": "hyderabad",
    "bengaluru": "bangalore",
    "bangalore": "bangalore",
    "jaipur": "jaipur",
    "kanpur": "kanpur",
    "gorakhpur": "gorakhpur",
    "agra": "agra",
    "varanasi": "varanasi",
    "noida": "noida",
    "gurgaon": "gurgaon",
    "pune": "pune",
    "ahmedabad": "ahmedabad",
}


def clean_number(value):

    if value is None:
        return None

    value = str(value)

    value = value.replace(
        "₹",
        ""
    )

    value = value.replace(
        ",",
        ""
    )

    match = re.search(
        r"\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:
        return float(
            match.group()
        )
    except Exception:
        return None


def extract_gold_rates(tables):

    for table in tables:

        if not table:
            continue

        headers = [
            normalize(x)
            for x in table[0]
        ]

        if not any(
            "24k" in h
            for h in headers
        ):
            continue

        rates = {}

        for row in table[1:]:

            if len(row) < 4:
                continue

            row_text = [
                normalize(x)
                for x in row
            ]

            if row_text[0] in {
                "gram",
                "1",
                "10"
            }:

                for i, header in enumerate(
                    headers
                ):

                    if i >= len(row):
                        continue

                    if "24k" in header:
                        rates["24K"] = clean_number(
                            row[i]
                        )

                    elif "22k" in header:
                        rates["22K"] = clean_number(
                            row[i]
                        )

                    elif "18k" in header:
                        rates["18K"] = clean_number(
                            row[i]
                        )

                if rates:
                    return rates

    return {}


def extract_date(text):

    patterns = [
        r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"([A-Za-z]+\s+\d{1,2},\s+\d{4})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            return match.group(1)

    return None


def city_from_query(query):

    normalized = normalize(
        query
    )

    for city in CITY_SLUGS:

        if city in normalized:
            return city

    return "lucknow"


def goodreturns_gold(city):

    slug = CITY_SLUGS.get(
        city,
        city
    )

    url = (
        "https://www.goodreturns.in/"
        f"gold-rates/{slug}.html"
    )

    page = read_page(url)

    if not page.get("ok"):
        return None

    rates = extract_gold_rates(
        page.get("tables", [])
    )

    if not rates:
        return None

    return {
        "source": "GoodReturns",
        "url": url,
        "category": "RETAIL INDIA",
        "date": extract_date(
            page.get("text", "")
        ),
        "rates": rates
    }


def bullionlive_gold(city):

    if city == "lucknow":

        url = (
            "https://bullionlive.app/"
            "gold-rate/uttar-pradesh/lucknow"
        )

    else:

        url = (
            "https://bullionlive.app/"
            f"gold-rate/{city}"
        )

    page = read_page(url)

    if not page.get("ok"):
        return None

    rates = extract_gold_rates(
        page.get("tables", [])
    )

    if not rates:

        text = page.get(
            "text",
            ""
        )

        found = {}

        patterns = {
            "24K": r"24K[^₹0-9]*₹?([\d,]+)",
            "22K": r"22K[^₹0-9]*₹?([\d,]+)",
            "18K": r"18K[^₹0-9]*₹?([\d,]+)"
        }

        for key, pattern in patterns.items():

            match = re.search(
                pattern,
                text,
                flags=re.I
            )

            if match:
                found[key] = clean_number(
                    match.group(1)
                )

        rates = found

    if not rates:
        return None

    return {
        "source": "BullionLive",
        "url": url,
        "category": "IBJA / BULLION",
        "date": extract_date(
            page.get("text", "")
        ),
        "rates": rates
    }


def gold_search(query):

    city = city_from_query(
        query
    )

    sources = []

    primary = goodreturns_gold(
        city
    )

    if primary:
        sources.append(primary)

    secondary = bullionlive_gold(
        city
    )

    if secondary:
        sources.append(secondary)

    return sources


def gold_summary(query):

    sources = gold_search(
        query
    )

    if not sources:

        return {
            "ok": False,
            "query": query,
            "error": "Gold data unavailable."
        }

    return {
        "ok": True,
        "query": query,
        "city": city_from_query(query),
        "primary": sources[0],
        "sources": sources
    }


# ============================================================
# CLI OUTPUT
# ============================================================

def cli_search(query):

    results = search_web(
        query
    )

    print(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False
        )
    )


def cli_gold(query):

    result = gold_summary(
        query
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


def cli_read(url):

    result = read_page(
        url
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 3:

        print(
            "Usage:\n"
            "  python web.py search \"query\"\n"
            "  python web.py gold \"query\"\n"
            "  python web.py read \"url\""
        )

        return

    command = sys.argv[1].lower()

    value = " ".join(
        sys.argv[2:]
    )

    if command == "search":

        cli_search(
            value
        )

    elif command == "gold":

        cli_gold(
            value
        )

    elif command == "read":

        cli_read(
            value
        )

    else:

        print(
            f"Unknown command: {command}"
        )


if __name__ == "__main__":
    main()
