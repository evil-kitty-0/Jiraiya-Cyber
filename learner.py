#!/usr/bin/env python3

import sys
import re
import time
from pathlib import Path
from urllib.parse import urlparse

BASE = Path.home() / "jiraiya"

sys.path.insert(0, str(BASE / "knowledge"))
sys.path.insert(0, str(BASE / "web"))

from knowledge import search_knowledge, add_knowledge
from web import search_web, read_page


LOCAL_CONFIDENCE_THRESHOLD = 0.75
LEARN_CONFIDENCE_THRESHOLD = 0.70

MAX_SOURCES = 4
MAX_PAGE_CHARS = 7000

STOP_WORDS = {
    "what", "is", "are", "was", "were", "the", "a", "an",
    "of", "to", "for", "in", "on", "and", "or", "how",
    "why", "when", "where", "which", "who", "does", "do",
    "explain", "tell", "me", "about", "please",
    "kya", "hai", "h", "ka", "ke", "ki", "ko", "me",
    "mein", "batao", "btao", "hota", "hoti"
}


def normalize(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\u0900-\u097f\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokens(text):
    return {
        word
        for word in normalize(text).split()
        if len(word) >= 3 and word not in STOP_WORDS
    }


def similarity(text_a, text_b):
    a = tokens(text_a)
    b = tokens(text_b)

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


# ============================================================
# LOCAL KNOWLEDGE RELEVANCE
# ============================================================

def local_relevance(query, item):
    """
    Check whether a local knowledge result actually belongs
    to the requested topic.
    """

    query_tokens = tokens(query)

    topic = item.get("topic", "")
    content = item.get("content", "")

    topic_tokens = tokens(topic)
    content_tokens = tokens(content)

    if not query_tokens:
        return 0.0

    # Strong match against topic.
    topic_match = len(query_tokens & topic_tokens) / len(query_tokens)

    # Match against content.
    content_match = len(query_tokens & content_tokens) / len(query_tokens)

    # Topic is more important than generic content.
    score = (topic_match * 0.70) + (content_match * 0.30)

    return min(score, 1.0)


def check_local_knowledge(query):
    try:
        results = search_knowledge(query)

        if not results:
            return {
                "found": False,
                "confidence": 0.0,
                "results": []
            }

        candidates = []

        for item in results:

            if int(item.get("verified", 0)) != 1:
                continue

            relevance = local_relevance(query, item)

            confidence = float(
                item.get("confidence", 0.0)
            )

            combined = (
                relevance * 0.70
                + confidence * 0.30
            )

            candidates.append(
                (
                    combined,
                    relevance,
                    confidence,
                    item
                )
            )

        if not candidates:
            return {
                "found": False,
                "confidence": 0.0,
                "results": results
            }

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        combined, relevance, confidence, best = candidates[0]

        # IMPORTANT:
        # High database confidence alone is NOT enough.
        # Topic relevance must also be high.
        found = (
            relevance >= 0.45
            and combined >= LOCAL_CONFIDENCE_THRESHOLD
        )

        return {
            "found": found,
            "confidence": round(combined, 3),
            "relevance": round(relevance, 3),
            "best": best,
            "results": results
        }

    except Exception as exc:
        return {
            "found": False,
            "confidence": 0.0,
            "results": [],
            "error": str(exc)
        }


# ============================================================
# WEB
# ============================================================

def extract_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def collect_web_sources(query):

    try:
        search_results = search_web(query)
    except Exception as exc:
        return {
            "ok": False,
            "sources": [],
            "error": str(exc)
        }

    if not search_results:
        return {
            "ok": False,
            "sources": [],
            "error": "No web search results found."
        }

    sources = []
    seen_domains = set()

    for result in search_results:

        if len(sources) >= MAX_SOURCES:
            break

        url = result.get("url")

        if not url:
            continue

        domain = extract_domain(url)

        if domain and domain in seen_domains:
            continue

        try:
            page = read_page(url)
        except Exception:
            continue

        if not page:
            continue

        text = clean_text(
            page.get("text", "")
        )

        if len(text) < 100:
            continue

        text = text[:MAX_PAGE_CHARS]

        sources.append({
            "title": (
                page.get("title")
                or result.get("title")
                or ""
            ),
            "url": url,
            "domain": domain,
            "text": text
        })

        if domain:
            seen_domains.add(domain)

    return {
        "ok": bool(sources),
        "sources": sources,
        "error": None if sources else
                 "No readable web sources found."
    }


# ============================================================
# WEB SOURCE RELEVANCE
# ============================================================

def source_relevance(query, source):

    query_tokens = tokens(query)
    text_tokens = tokens(source.get("text", ""))

    if not query_tokens or not text_tokens:
        return 0.0

    return min(
        len(query_tokens & text_tokens)
        / len(query_tokens),
        1.0
    )


# ============================================================
# VERIFICATION
# ============================================================

def verify_sources(query, sources):

    if not sources:
        return {
            "verified": False,
            "confidence": 0.0,
            "reason": "No sources."
        }

    relevance_scores = [
        source_relevance(query, source)
        for source in sources
    ]

    average_relevance = (
        sum(relevance_scores)
        / len(relevance_scores)
    )

    useful_sources = [
        source
        for source, score in zip(
            sources,
            relevance_scores
        )
        if score >= 0.30
    ]

    if not useful_sources:
        return {
            "verified": False,
            "confidence": 0.0,
            "reason": "Sources were not sufficiently relevant."
        }

    agreement_scores = []

    for i in range(len(useful_sources)):
        for j in range(i + 1, len(useful_sources)):

            score = similarity(
                useful_sources[i]["text"],
                useful_sources[j]["text"]
            )

            agreement_scores.append(score)

    if agreement_scores:
        average_agreement = (
            sum(agreement_scores)
            / len(agreement_scores)
        )
    else:
        average_agreement = 0.30

    domains = {
        source.get("domain")
        for source in useful_sources
        if source.get("domain")
    }

    domain_count = len(domains)

    if domain_count >= 3:
        source_bonus = 0.20
    elif domain_count == 2:
        source_bonus = 0.12
    else:
        source_bonus = 0.05

    confidence = (
        average_relevance * 0.50
        + average_agreement * 0.30
        + source_bonus
    )

    confidence = max(
        0.0,
        min(confidence, 1.0)
    )

    verified = (
        confidence >= LEARN_CONFIDENCE_THRESHOLD
        and average_relevance >= 0.30
    )

    if verified:
        reason = (
            "Relevant sources showed sufficient agreement."
        )
    else:
        reason = (
            "Verification confidence was too low. "
            "Knowledge was not stored."
        )

    return {
        "verified": verified,
        "confidence": round(confidence, 3),
        "average_relevance": round(
            average_relevance, 3
        ),
        "average_agreement": round(
            average_agreement, 3
        ),
        "source_count": len(useful_sources),
        "independent_domains": domain_count,
        "reason": reason
    }


# ============================================================
# KNOWLEDGE CONTENT
# ============================================================

def build_knowledge_content(query, sources):

    parts = []

    for source in sources[:MAX_SOURCES]:

        title = (
            source.get("title")
            or source.get("domain")
            or "Source"
        )

        text = clean_text(
            source.get("text", "")
        )

        if len(text) > 1800:
            text = text[:1800] + "..."

        parts.append(
            f"[{title}]\n"
            f"{text}\n"
            f"Source: {source.get('url', '')}"
        )

    return (
        f"Question/topic: {query}\n\n"
        + "\n\n".join(parts)
    )


# ============================================================
# LEARNING ENGINE
# ============================================================

def learn(query, category="general"):

    query = clean_text(query)

    if not query:
        return {
            "ok": False,
            "status": "empty_query"
        }

    # --------------------------------------------------------
    # 1. LOCAL KNOWLEDGE
    # --------------------------------------------------------

    local = check_local_knowledge(query)

    if local.get("found"):

        return {
            "ok": True,
            "status": "local_knowledge",
            "source": "knowledge_store",
            "confidence": local["confidence"],
            "relevance": local.get("relevance", 0.0),
            "knowledge": local.get("best"),
            "web_used": False
        }

    # --------------------------------------------------------
    # 2. ONLINE SEARCH
    # --------------------------------------------------------

    web = collect_web_sources(query)

    if not web.get("ok"):

        return {
            "ok": False,
            "status": "web_unavailable",
            "web_used": True,
            "error": web.get("error")
        }

    sources = web["sources"]

    # --------------------------------------------------------
    # 3. VERIFY
    # --------------------------------------------------------

    verification = verify_sources(
        query,
        sources
    )

    if not verification["verified"]:

        return {
            "ok": False,
            "status": "verification_failed",
            "web_used": True,
            "sources": sources,
            "verification": verification
        }

    # --------------------------------------------------------
    # 4. STORE
    # --------------------------------------------------------

    content = build_knowledge_content(
        query,
        sources
    )

    primary = sources[0]

    saved = add_knowledge(
        topic=query,
        category=category,
        content=content,
        source=(
            primary.get("domain")
            or "web"
        ),
        source_url=primary.get("url"),
        confidence=verification["confidence"],
        verified=True
    )

    return {
        "ok": True,
        "status": "learned",
        "web_used": True,
        "knowledge_id": saved,
        "confidence": verification["confidence"],
        "sources": sources,
        "verification": verification
    }


# ============================================================
# OUTPUT
# ============================================================

def print_result(result):

    print()

    status = result.get("status")

    if status == "local_knowledge":

        print("🧠 Local knowledge found.")
        print(
            f"Confidence: "
            f"{result.get('confidence')}"
        )
        print(
            f"Relevance: "
            f"{result.get('relevance')}"
        )
        print()

        knowledge = result.get(
            "knowledge",
            {}
        )

        print(
            knowledge.get(
                "content",
                ""
            )
        )

        return

    if status == "learned":

        print(
            "🧠 Knowledge learned and stored."
        )

        print(
            f"Knowledge ID: "
            f"{result.get('knowledge_id')}"
        )

        print(
            f"Confidence: "
            f"{result.get('confidence')}"
        )

        verification = result.get(
            "verification",
            {}
        )

        print(
            f"Sources: "
            f"{verification.get('source_count', 0)}"
        )

        print(
            f"Independent domains: "
            f"{verification.get('independent_domains', 0)}"
        )

        print()

        for i, source in enumerate(
            result.get("sources", []),
            1
        ):
            print(
                f"{i}. "
                f"{source.get('title') or source.get('domain')}"
            )
            print(
                f"   {source.get('url')}"
            )

        return

    if status == "verification_failed":

        print(
            "⚠️ Knowledge NOT stored."
        )

        verification = result.get(
            "verification",
            {}
        )

        print(
            f"Confidence: "
            f"{verification.get('confidence', 0)}"
        )

        print(
            verification.get(
                "reason",
                ""
            )
        )

        print()
        print("Sources checked:")

        for source in result.get(
            "sources",
            []
        ):
            print(
                f"- {source.get('url')}"
            )

        return

    print("❌ Learning failed.")

    print(
        result.get(
            "error",
            "Unknown error."
        )
    )


# ============================================================
# CLI
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            'Usage:\n'
            '  python ~/jiraiya/learner.py '
            '"your question"\n\n'
            'Example:\n'
            '  python ~/jiraiya/learner.py '
            '"What is the Chandrasekhar limit" physics'
        )

        return

    query = sys.argv[1]

    category = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else "general"
    )

    start = time.time()

    result = learn(
        query,
        category
    )

    print_result(result)

    print()
    print(
        f"Time: "
        f"{time.time() - start:.2f}s"
    )


if __name__ == "__main__":
    main()
