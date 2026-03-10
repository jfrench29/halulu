"""Text normalization and signal-detection utilities."""

from __future__ import annotations

import re

# ── Refusal phrases ──────────────────────────────────────────────────

REFUSAL_PHRASES: list[str] = [
    "i cannot", "i can't", "i'm not able to", "i am not able to",
    "i don't have", "i do not have", "as an ai", "i'm unable to",
    "i am unable to", "i must decline", "i cannot provide", "i can't provide",
    "does not exist", "doesn't exist", "is not real", "isn't real",
    "is fictional", "no such", "there is no", "this is a fictional",
    "this appears to be fictional", "i'm not aware of", "i am not aware of",
    "i couldn't find", "i could not find", "never acquired", "never happened",
    "never occurred", "was not replaced", "has not been replaced",
    "did not formulate", "did not state", "did not say", "did not give",
    "has never", "have never", "not a real", "not an actual",
    "no record of", "cannot find any", "can't find any",
    "did not acquire", "has not acquired", "no such acquisition",
    "that premise is false", "never purchased", "has not purchased",
    "did not purchase", "is not accurate", "this is not correct",
    "did not happen", "has not happened", "never took place",
]

# ── Correction phrases ───────────────────────────────────────────────

CORRECTION_PHRASES: list[str] = [
    "actually", "however", "correction", "this is incorrect",
    "this is not accurate", "not accurate", "inaccurate", "no such",
    "doesn't exist", "does not exist", "not real", "fictional",
    "fabricated", "i'm not aware", "unable to verify", "cannot verify",
    "could not find", "couldn't find", "no evidence",
    "inaccurate premise", "false premise", "incorrect premise",
    "incorrect assumption", "false assumption", "mistaken",
    "there was no", "there is no", "not true", "isn't true",
    "never happened", "never occurred", "remains", "still serves",
    "still the", "as of my", "not aware of any", "no known",
    "did not acquire", "has not acquired", "did not purchase",
    "has not purchased", "never acquired", "never purchased",
    "was not replaced", "has not been replaced", "did not formulate",
]


# ── Text normalization ───────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Lowercase, strip, remove non-word punctuation for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s.]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_numbers(text: str) -> list[float]:
    """Extract all plausible numbers from free text.

    Handles: 299,792,458 | $60.9 | 27 billion | 6.022e23 | 1.4
    Also handles: 6.022 × 10^23 | 6.022 x 10^23 | 6.022 * 10^23
    """
    cleaned = text.replace(",", "")
    results: list[float] = []

    # First pass: scientific notation with × or x (e.g., "6.022 × 10^23")
    for m in re.finditer(
        r"(-?[\d]+\.?\d*)\s*[×xX\*]\s*10\^(-?\d+)",
        cleaned,
    ):
        try:
            mantissa = float(m.group(1))
            exponent = int(m.group(2))
            results.append(mantissa * (10 ** exponent))
        except (ValueError, OverflowError):
            continue

    # Second pass: standard numbers with optional scale words
    for m in re.finditer(
        r"(-?[\d]+\.?\d*(?:[eE][+-]?\d+)?)\s*(trillion|billion|million|thousand)?",
        cleaned, re.IGNORECASE,
    ):
        try:
            val = float(m.group(1))
        except ValueError:
            continue
        scale = (m.group(2) or "").lower()
        if scale == "trillion":
            val *= 1e12
        elif scale == "billion":
            val *= 1e9
        elif scale == "million":
            val *= 1e6
        elif scale == "thousand":
            val *= 1e3
        # Skip if this number was already captured by the × 10^ pass
        if not any(abs(val - r) < abs(val * 1e-9) + 1e-30 for r in results):
            results.append(val)

    return results


# ── Signal detection ─────────────────────────────────────────────────

def detect_refusal(response: str) -> bool:
    """Return True if the response contains refusal language."""
    resp_lower = response.lower()
    return any(phrase in resp_lower for phrase in REFUSAL_PHRASES)


def detect_correction(response: str) -> bool:
    """Return True if the response contains correction language."""
    resp_lower = response.lower()
    return any(phrase in resp_lower for phrase in CORRECTION_PHRASES)


def classify_hallucination_subtype(response: str) -> str:
    """Heuristic classification of hallucination subtypes."""
    resp_lower = response.lower()

    if any(kw in resp_lower for kw in ["published in", "journal", "paper", "doi", "isbn"]):
        return "fabricated_citation"
    if any(kw in resp_lower for kw in ["dr.", "professor", "researcher", "scientist"]):
        return "fabricated_entity"
    if re.search(r"\d+\.?\d*\s*(%|percent|million|billion|trillion)", resp_lower):
        return "numerical_error"
    if any(kw in resp_lower for kw in ["study shows", "research found", "according to"]):
        return "unsupported_claim"

    return "fabricated_fact"
