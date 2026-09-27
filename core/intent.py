#!/usr/bin/env python3

import re
import sys


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text):
    text = str(text).lower()

    replacements = {
        "²": "^2",
        "³": "^3",
        "×": "*",
        "÷": "/",
        "−": "-",
        "–": "-",
        "—": "-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_any(text, words):
    return any(word in text for word in words)


# ============================================================
# MATHEMATICS
# ============================================================

def looks_like_math(text):

    t = normalize(text)

    math_terms = [
        "calculate",
        "calculation",
        "solve",
        "equation",
        "algebra",
        "quadratic",
        "linear equation",
        "derivative",
        "differentiate",
        "integral",
        "integrate",
        "factorial",
        "percentage",
        "percent",
        "probability",
        "matrix",
        "matrices",
        "logarithm",
        "log ",
        "sin(",
        "cos(",
        "tan(",
        "sqrt",
        "square root",
        "cube root",
        "arithmetic",
        "geometry",
        "trigonometry",
        "statistics",
        "mean",
        "median",
        "standard deviation",
    ]

    if contains_any(t, math_terms):
        return True

    # Simple arithmetic expression.
    if re.fullmatch(
        r"[\d\s\+\-\*\/\%\(\)\.\^]+",
        t
    ):
        return True

    # Equations with variables.
    if re.search(
        r"\b\d*\s*[a-z]\s*[\+\-\*\/\^=]",
        t
    ):
        return True

    # Polynomial-looking expressions.
    if re.search(
        r"[a-z]\s*\^?\s*\d+",
        t
    ) and "=" in t:
        return True

    return False


# ============================================================
# PHYSICS
# ============================================================

def looks_like_physics(text):

    t = normalize(text)

    physics_terms = [
        "physics",
        "velocity",
        "acceleration",
        "displacement",
        "distance",
        "speed",
        "force",
        "momentum",
        "impulse",
        "energy",
        "kinetic energy",
        "potential energy",
        "work done",
        "power",
        "gravity",
        "gravitational",
        "mass",
        "weight",
        "friction",
        "pressure",
        "density",
        "temperature",
        "heat",
        "thermodynamics",
        "electricity",
        "electric field",
        "magnetic field",
        "magnetism",
        "voltage",
        "current",
        "resistance",
        "ohm",
        "ohm's law",
        "circuit",
        "capacitor",
        "inductor",
        "frequency",
        "wavelength",
        "photon",
        "quantum",
        "relativity",
        "newton",
        "newton's law",
        "einstein",
        "black hole",
        "white dwarf",
        "neutron star",
        "supernova",
        "stellar",
        "star",
        "astrophysics",
        "astronomy",
        "chandrasekhar",
        "chandrasekhar limit",
        "degeneracy pressure",
        "electron degeneracy",
    ]

    if contains_any(t, physics_terms):
        return True

    return False


# ============================================================
# CHEMISTRY
# ============================================================

def looks_like_chemistry(text):

    t = normalize(text)

    chemistry_terms = [
        "chemistry",
        "chemical",
        "molecule",
        "molecular",
        "atom",
        "atomic",
        "element",
        "compound",
        "reaction",
        "chemical reaction",
        "molar mass",
        "molecular mass",
        "mole",
        "mol",
        "molarity",
        "molality",
        "ph",
        "acid",
        "base",
        "salt",
        "oxidation",
        "reduction",
        "redox",
        "catalyst",
        "catalysis",
        "organic chemistry",
        "inorganic chemistry",
        "pharmaceutical chemistry",
        "functional group",
        "alkane",
        "alkene",
        "alkyne",
        "benzene",
        "polymer",
        "periodic table",
        "valency",
        "valence",
        "electron configuration",
        "stoichiometry",
        "pka",
        "pkb",
    ]

    if contains_any(t, chemistry_terms):
        return True

    # Chemical formula patterns.
    if re.search(
        r"\b(?:NaCl|H2O|CO2|O2|N2|H2|HCl|NaOH|CaCO3)\b",
        text
    ):
        return True

    return False


# ============================================================
# CODING
# ============================================================

def looks_like_coding(text):

    t = normalize(text)

    coding_terms = [
        "python",
        "javascript",
        "typescript",
        "java ",
        "c++",
        "c programming",
        "rust",
        "golang",
        "code",
        "coding",
        "programming",
        "function",
        "class",
        "variable",
        "algorithm",
        "debug",
        "debugging",
        "bug",
        "compile",
        "compiler",
        "api",
        "endpoint",
        "json",
        "html",
        "css",
        "sql",
        "database",
        "flask",
        "django",
        "react",
        "github",
        "git ",
        "terminal",
        "bash",
        "shell script",
        "script",
        "program",
    ]

    return contains_any(
        t,
        coding_terms
    )


# ============================================================
# GOLD
# ============================================================

def looks_like_gold(text):

    t = normalize(text)

    gold_terms = [
        "gold rate",
        "gold price",
        "gold rates",
        "gold prices",
        "today gold",
        "gold today",
        "24k gold",
        "22k gold",
        "18k gold",
        "sona rate",
        "sona ka rate",
        "gold jewellery rate",
        "bullion rate",
    ]

    return contains_any(
        t,
        gold_terms
    )


# ============================================================
# WEATHER
# ============================================================

def looks_like_weather(text):

    t = normalize(text)

    weather_terms = [
        "weather",
        "temperature today",
        "temperature right now",
        "rain today",
        "raining",
        "rainfall",
        "forecast",
        "humidity",
        "wind speed",
        "will it rain",
        "weather today",
        "weather tomorrow",
    ]

    return contains_any(
        t,
        weather_terms
    )


# ============================================================
# STOCK / MARKET
# ============================================================

def looks_like_stock_market(text):

    t = normalize(text)

    terms = [
        "stock price",
        "share price",
        "stock market",
        "share market",
        "nifty",
        "sensex",
        "bank nifty",
        "nasdaq",
        "dow jones",
        "nyse",
        "market today",
        "ipo",
        "stock today",
        "stocks today",
        "share today",
        "option chain",
        "call option",
        "put option",
        "futures",
        "mcx",
        "commodity price",
    ]

    return contains_any(
        t,
        terms
    )


# ============================================================
# ECONOMICS
# ============================================================

def looks_like_economics(text):

    t = normalize(text)

    terms = [
        "inflation",
        "gdp",
        "interest rate",
        "repo rate",
        "reverse repo",
        "unemployment",
        "economic growth",
        "economy",
        "rbi policy",
        "monetary policy",
        "fiscal policy",
        "exchange rate",
        "currency rate",
        "rupee",
        "dollar rate",
    ]

    return contains_any(
        t,
        terms
    )


# ============================================================
# NEWS
# ============================================================

def looks_like_news(text):

    t = normalize(text)

    terms = [
        "latest news",
        "latest update",
        "breaking news",
        "today's news",
        "today news",
        "what happened",
        "recent news",
        "latest developments",
        "news about",
        "updates about",
        "recent update",
    ]

    return contains_any(
        t,
        terms
    )


# ============================================================
# HISTORY
# ============================================================

def looks_like_history(text):

    t = normalize(text)

    history_terms = [
        "history",
        "historical",
        "ancient",
        "medieval",
        "mughal empire",
        "maurya empire",
        "gupta empire",
        "indus valley",
        "british india",
        "world war",
        "first world war",
        "second world war",
        "independence movement",
        "freedom movement",
        "akbar",
        "ashoka",
        "aurangzeb",
        "shivaji",
        "gandhi",
        "napoleon",
        "roman empire",
        "ottoman empire",
    ]

    return contains_any(
        t,
        history_terms
    )


# ============================================================
# MEMORY
# ============================================================

def looks_like_memory(text):

    t = normalize(text)

    memory_terms = [
        "remember that",
        "remember this",
        "remember my",
        "don't forget",
        "do not forget",
        "keep in mind",
        "yaad rakh",
        "yaad rakhna",
        "yaad rkh",
        "bhoolna mat",
        "mat bhoolna",
        "meri baat yaad",
    ]

    return contains_any(
        t,
        memory_terms
    )


# ============================================================
# KNOWLEDGE / LEARNING
# ============================================================

def looks_like_knowledge_lookup(text):

    t = normalize(text)

    terms = [
        "what is",
        "what are",
        "who is",
        "who was",
        "explain",
        "define",
        "definition of",
        "meaning of",
        "how does",
        "how do",
        "why does",
        "why is",
        "tell me about",
        "batao",
        "btao",
        "kya hai",
        "kya hota hai",
    ]

    return contains_any(
        t,
        terms
    )


# ============================================================
# GENERAL WEB
# ============================================================

def looks_like_web(text):

    t = normalize(text)

    terms = [
        "search online",
        "search the web",
        "search internet",
        "google",
        "look it up",
        "find online",
        "on the internet",
        "latest information",
        "current information",
        "current data",
    ]

    return contains_any(
        t,
        terms
    )


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(question):

    t = normalize(question)

    # Specific/current intents first.
    if looks_like_memory(t):
        return "memory"

    if looks_like_gold(t):
        return "gold"

    if looks_like_weather(t):
        return "weather"

    if looks_like_stock_market(t):
        return "stock_market"

    if looks_like_news(t):
        return "news"

    if looks_like_economics(t):
        return "economics"

    # Scientific domains.
    if looks_like_chemistry(t):
        return "chemistry"

    if looks_like_physics(t):
        return "physics"

    if looks_like_math(t):
        return "mathematics"

    if looks_like_coding(t):
        return "coding"

    if looks_like_history(t):
        return "history"

    if looks_like_web(t):
        return "web"

    # General knowledge.
    if looks_like_knowledge_lookup(t):
        return "knowledge"

    return "general"


# ============================================================
# MODE
# ============================================================

def detect_mode(intent):

    offline_intents = {
        "memory",
        "mathematics",
        "physics",
        "chemistry",
        "coding",
    }

    online_intents = {
        "gold",
        "weather",
        "stock_market",
        "news",
        "economics",
        "web",
    }

    hybrid_intents = {
        "history",
        "knowledge",
        "general",
    }

    if intent in offline_intents:
        return "offline"

    if intent in online_intents:
        return "online"

    if intent in hybrid_intents:
        return "hybrid"

    return "offline"


# ============================================================
# CLASSIFY
# ============================================================

def classify(question):

    intent = detect_intent(
        question
    )

    mode = detect_mode(
        intent
    )

    return {
        "question": question,
        "intent": intent,
        "mode": mode
    }


# ============================================================
# CLI
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            'Usage:\n'
            '  python intent.py "your question"'
        )

        return

    question = " ".join(
        sys.argv[1:]
    )

    result = classify(
        question
    )

    print(
        "Intent:",
        result["intent"]
    )

    print(
        "Mode:",
        result["mode"]
    )


if __name__ == "__main__":
    main()
