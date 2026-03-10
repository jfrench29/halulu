"""Tests for grading.normalization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from grading.normalization import (
    normalize_text,
    extract_numbers,
    detect_refusal,
    detect_correction,
    classify_hallucination_subtype,
)


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("HELLO") == "hello"

    def test_strips_punctuation(self):
        assert normalize_text("Hello, World!") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_empty(self):
        assert normalize_text("") == ""


class TestExtractNumbers:
    def test_integer(self):
        assert extract_numbers("The answer is 206.") == [206.0]

    def test_float(self):
        assert extract_numbers("Approximately 3.14") == [3.14]

    def test_billion(self):
        nums = extract_numbers("Revenue was $4.2 billion")
        assert len(nums) == 1
        assert abs(nums[0] - 4.2e9) < 1

    def test_million(self):
        nums = extract_numbers("Population: 8.3 million")
        assert len(nums) == 1
        assert abs(nums[0] - 8.3e6) < 1

    def test_scientific_notation(self):
        nums = extract_numbers("6.022e23")
        assert len(nums) == 1
        assert abs(nums[0] - 6.022e23) < 1e20

    def test_multiple(self):
        nums = extract_numbers("Between 100 and 200")
        assert nums == [100.0, 200.0]

    def test_comma_separated(self):
        nums = extract_numbers("299,792,458 m/s")
        assert nums == [299792458.0]

    def test_no_numbers(self):
        assert extract_numbers("no numbers here") == []


class TestDetectRefusal:
    def test_cannot_provide(self):
        assert detect_refusal("I cannot provide that information.")

    def test_unable_to_answer(self):
        assert detect_refusal("I'm unable to answer this question.")

    def test_did_not_acquire(self):
        assert detect_refusal("Apple did not acquire Netflix.")

    def test_normal_answer(self):
        assert not detect_refusal("The answer is 42.")

    def test_no_such_acquisition(self):
        assert detect_refusal("There is no such acquisition.")


class TestDetectCorrection:
    def test_did_not_acquire(self):
        assert detect_correction("Apple did not acquire Netflix.")

    def test_never_acquired(self):
        assert detect_correction("Apple has never acquired Netflix.")

    def test_does_not_exist(self):
        assert detect_correction("This study does not exist.")

    def test_is_fictional(self):
        assert detect_correction("Wakanda is fictional.")

    def test_was_not_replaced(self):
        assert detect_correction("Pichai was not replaced as CEO.")

    def test_normal_answer(self):
        assert not detect_correction("The capital of France is Paris.")


class TestClassifyHallucinationSubtype:
    def test_citation(self):
        subtype = classify_hallucination_subtype("Published in Nature, vol. 12")
        assert subtype == "fabricated_citation"

    def test_numerical(self):
        subtype = classify_hallucination_subtype("The population is exactly 5,234,891")
        assert subtype in ("fabricated_fact", "numerical_error", "fabricated_entity")

    def test_generic(self):
        subtype = classify_hallucination_subtype("Some random fabricated claim")
        assert subtype in ("fabricated_fact", "fabricated_entity", "unsupported_claim")
