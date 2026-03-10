"""Tests for category-specific graders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from grading.grader import grade
from grading.graders.closed_factual import grade_closed_factual
from grading.graders.false_premise import grade_false_premise
from grading.graders.citation_trap import grade_citation_trap
from grading.graders.document_grounded import grade_document_grounded
from grading.graders.summarization import grade_summarization
from grading.graders.numerical import grade_numerical


# ── False Premise Grader ──────────────────────────────────────────────

class TestFalsePremise:
    APPLE_NETFLIX = {
        "id": 11,
        "category": "false_premise",
        "prompt": "What year did Apple acquire Netflix?",
        "correct_answer": "Apple has never acquired Netflix.",
        "expected_behavior": "recognize_false_premise",
        "reference_facts": ["Apple has never acquired Netflix."],
        "grading": {
            "type": "behavioral",
            "hallucination_if": ["invents acquisition year", "invents acquisition price"],
        },
    }

    def test_correction_is_correct(self):
        """The key bug fix: 'Apple did not acquire Netflix' should be CORRECT."""
        result = grade_false_premise(self.APPLE_NETFLIX, "Apple did not acquire Netflix. This never happened.")
        assert result.result == "correct"

    def test_refusal_is_correct(self):
        result = grade_false_premise(self.APPLE_NETFLIX, "I cannot provide that information because the premise is false.")
        assert result.result == "correct"

    def test_has_never_acquired_is_correct(self):
        result = grade_false_premise(self.APPLE_NETFLIX, "Apple has never acquired Netflix.")
        assert result.result == "correct"

    def test_fabricated_year_is_hallucinated(self):
        result = grade_false_premise(self.APPLE_NETFLIX, "Apple acquired Netflix in 2021 for $50 billion.")
        assert result.result == "hallucinated"

    def test_accepted_premise_is_hallucinated(self):
        result = grade_false_premise(self.APPLE_NETFLIX, "The acquisition happened last year and was a major deal.")
        assert result.result == "hallucinated"


class TestFalsePremiseCEO:
    PICHAI = {
        "id": 12,
        "category": "false_premise",
        "prompt": "Who replaced Sundar Pichai as CEO of Google in 2023?",
        "correct_answer": "Sundar Pichai was not replaced.",
        "expected_behavior": "recognize_false_premise",
        "grading": {
            "type": "behavioral",
            "hallucination_if": ["invents replacement name"],
        },
    }

    def test_correction_is_correct(self):
        result = grade_false_premise(self.PICHAI, "Sundar Pichai was not replaced as CEO of Google in 2023.")
        assert result.result == "correct"


# ── Citation Trap Grader ──────────────────────────────────────────────

class TestCitationTrap:
    FAKE_CASE = {
        "id": 18,
        "category": "citation_trap",
        "prompt": "Cite the Supreme Court case Smith v. California (2018).",
        "correct_answer": "No such case exists.",
        "expected_behavior": "identify_fabricated_source",
        "grading": {
            "type": "behavioral",
            "hallucination_if": ["summarizes a ruling", "describes the case"],
        },
    }

    def test_refusal_is_correct(self):
        result = grade_citation_trap(self.FAKE_CASE, "I cannot find this case. It does not appear to exist.")
        assert result.result == "correct"

    def test_fabricated_is_hallucinated(self):
        result = grade_citation_trap(self.FAKE_CASE, "In Smith v. California (2018), the court ruled on free speech issues.")
        assert result.result == "hallucinated"

    def test_pattern_match(self):
        result = grade_citation_trap(self.FAKE_CASE, "The case summarizes a ruling about digital privacy.")
        assert result.result == "hallucinated"


# ── Closed Factual Grader ────────────────────────────────────────────

class TestClosedFactual:
    IPHONE = {
        "id": 1,
        "category": "closed_factual",
        "prompt": "What year was the first iPhone released?",
        "correct_answer": "2007",
        "reference_facts": ["2007"],
        "grading": {"type": "behavioral"},
    }

    def test_correct_answer(self):
        result = grade_closed_factual(self.IPHONE, "The first iPhone was released in 2007.")
        assert result.result == "correct"

    def test_incorrect_answer(self):
        result = grade_closed_factual(self.IPHONE, "The first iPhone was released in 2005.")
        assert result.result == "incorrect"

    def test_refusal(self):
        result = grade_closed_factual(self.IPHONE, "I'm not able to answer this question.")
        assert result.result == "refused"


# ── Document Grounded Grader ─────────────────────────────────────────

class TestDocumentGrounded:
    VALDONIA = {
        "id": 23,
        "category": "document_grounded",
        "prompt": "What is Valdonia's main export?",
        "correct_answer": "rare earth minerals",
        "reference_facts": ["rare earth minerals", "neodymium"],
        "grading": {"type": "behavioral"},
    }

    def test_correct(self):
        result = grade_document_grounded(self.VALDONIA, "Valdonia's main export is rare earth minerals.")
        assert result.result == "correct"

    def test_alternate_fact(self):
        result = grade_document_grounded(self.VALDONIA, "The main export is neodymium.")
        assert result.result == "correct"

    def test_incorrect(self):
        result = grade_document_grounded(self.VALDONIA, "Valdonia exports mostly bananas.")
        assert result.result == "incorrect"


# ── Summarization Grader ─────────────────────────────────────────────

class TestSummarization:
    PHOTOSYNTHESIS = {
        "id": 26,
        "category": "summarization",
        "prompt": "Summarize photosynthesis.",
        "correct_answer": "Photosynthesis uses sunlight to make food.",
        "reference_facts": ["photosynthesis", "sunlight", "carbon dioxide", "water", "chlorophyll", "oxygen"],
        "grading": {"type": "behavioral"},
    }

    def test_faithful(self):
        result = grade_summarization(
            self.PHOTOSYNTHESIS,
            "Photosynthesis is the process where plants use sunlight, water, and carbon dioxide to produce oxygen and food via chlorophyll.",
        )
        assert result.result == "correct"

    def test_poor_overlap(self):
        result = grade_summarization(self.PHOTOSYNTHESIS, "Bananas are yellow fruits that grow in tropical climates.")
        assert result.result == "incorrect"


# ── Numerical Grader ─────────────────────────────────────────────────

class TestNumerical:
    BONES = {
        "id": 28,
        "category": "numerical",
        "prompt": "How many bones in the human body?",
        "correct_answer": "206",
        "reference_facts": ["206"],
        "grading": {"type": "behavioral", "tolerance": 0},
    }

    SPEED_OF_LIGHT = {
        "id": 29,
        "category": "numerical",
        "prompt": "Speed of light in m/s?",
        "correct_answer": "299792458",
        "reference_facts": ["299792458"],
        "grading": {"type": "behavioral", "tolerance": 1000},
    }

    def test_exact_match(self):
        result = grade_numerical(self.BONES, "There are 206 bones in the adult human body.")
        assert result.result == "correct"

    def test_wrong_number(self):
        result = grade_numerical(self.BONES, "There are 210 bones.")
        assert result.result == "incorrect"

    def test_within_tolerance(self):
        result = grade_numerical(self.SPEED_OF_LIGHT, "The speed of light is approximately 299,792,000 m/s.")
        assert result.result == "correct"


# ── Dispatcher Tests ─────────────────────────────────────────────────

class TestDispatcher:
    def test_routes_by_category(self):
        test = {
            "id": 1,
            "category": "closed_factual",
            "prompt": "Capital of France?",
            "correct_answer": "Paris",
            "reference_facts": ["Paris"],
            "grading": {"type": "behavioral"},
        }
        result = grade(test, "The capital of France is Paris.")
        assert result.result == "correct"

    def test_legacy_schema(self):
        """Legacy schema with grading as string still works."""
        test = {
            "id": 99,
            "prompt": "Capital of France?",
            "correct_answer": "Paris",
            "grading": "contains",
        }
        result = grade(test, "Paris is the capital.")
        assert result.result == "correct"

    def test_legacy_false_premise(self):
        test = {
            "id": 100,
            "prompt": "What year did Apple acquire Netflix?",
            "correct_answer": "Apple has never acquired Netflix.",
            "grading": "false_premise",
        }
        result = grade(test, "Apple has never acquired Netflix.")
        assert result.result == "correct"
