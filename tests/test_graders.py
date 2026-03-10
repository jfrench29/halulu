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


# ── Substring Boundary Tests ────────────────────────────────────────

class TestSubstringBoundary:
    """Audit finding: short facts like 'Au' could match inside longer words."""

    GOLD = {
        "id": 2,
        "category": "closed_factual",
        "prompt": "What is the chemical symbol for gold?",
        "correct_answer": "Au",
        "reference_facts": ["Au"],
        "grading": {"type": "behavioral"},
    }

    C_LANG = {
        "id": 7,
        "category": "closed_factual",
        "prompt": "What programming language was the original Unix kernel written in?",
        "correct_answer": "C",
        "reference_facts": ["C"],
        "grading": {"type": "behavioral"},
    }

    def test_au_exact_match(self):
        result = grade_closed_factual(self.GOLD, "The chemical symbol for gold is Au.")
        assert result.result == "correct"

    def test_au_not_in_automatic(self):
        """'Au' should NOT match inside 'automatic' or 'authority'."""
        result = grade_closed_factual(self.GOLD, "The automatic authority handled it.")
        assert result.result == "incorrect"

    def test_au_not_in_because(self):
        result = grade_closed_factual(self.GOLD, "Because autumn is beautiful.")
        assert result.result == "incorrect"

    def test_c_exact_match(self):
        result = grade_closed_factual(self.C_LANG, "The Unix kernel was written in C.")
        assert result.result == "correct"

    def test_c_not_in_contain(self):
        """'C' should NOT match inside 'contain' or 'code'."""
        result = grade_closed_factual(self.C_LANG, "This code will contain the result.")
        assert result.result == "incorrect"

    def test_document_grounded_short_fact(self):
        """Document grounded grader also uses boundary matching for short facts."""
        test = {
            "id": 99,
            "category": "document_grounded",
            "prompt": "What percentage?",
            "correct_answer": "34%",
            "reference_facts": ["34"],
            "grading": {"type": "behavioral"},
        }
        result = grade_document_grounded(test, "The result was 34 percent.")
        assert result.result == "correct"


# ── Numerical Edge Cases ────────────────────────────────────────────

class TestNumericalEdgeCases:
    """Audit finding: missing edge case tests for numerical grader."""

    def test_billion_scale_word(self):
        test = {
            "id": 31,
            "category": "numerical",
            "prompt": "GDP of Brazil?",
            "correct_answer": "2.13 trillion",
            "reference_facts": ["2130000000000"],
            "grading": {"type": "behavioral", "tolerance": 200000000000},
        }
        result = grade_numerical(test, "Brazil's GDP is approximately $2.1 trillion.")
        assert result.result == "correct"

    def test_scientific_notation_response(self):
        test = {
            "id": 1009,
            "category": "numerical",
            "prompt": "Avogadro's number?",
            "correct_answer": "6.022e23",
            "reference_facts": ["6.022e23"],
            "grading": {"type": "behavioral", "tolerance": 1e20},
        }
        result = grade_numerical(test, "Avogadro's number is approximately 6.022 × 10^23.")
        assert result.result == "correct"

    def test_no_numbers_in_response(self):
        test = {
            "id": 28,
            "category": "numerical",
            "prompt": "How many bones?",
            "correct_answer": "206",
            "grading": {"type": "behavioral", "tolerance": 0},
        }
        result = grade_numerical(test, "There are many bones in the human body.")
        assert result.result == "incorrect"

    def test_refusal(self):
        test = {
            "id": 28,
            "category": "numerical",
            "prompt": "How many bones?",
            "correct_answer": "206",
            "grading": {"type": "behavioral", "tolerance": 0},
        }
        result = grade_numerical(test, "I cannot provide that information.")
        assert result.result == "refused"

    def test_small_tolerance(self):
        """Gravitational constant with tight tolerance."""
        test = {
            "id": 35,
            "category": "numerical",
            "prompt": "Gravitational constant G?",
            "correct_answer": "6.674e-11",
            "grading": {"type": "behavioral", "tolerance": 1e-13},
        }
        result = grade_numerical(test, "The gravitational constant is 6.674e-11 m^3 kg^-1 s^-2.")
        assert result.result == "correct"


# ── Summarization Edge Cases ────────────────────────────────────────

class TestSummarizationEdgeCases:
    """Audit finding: missing threshold boundary and empty refs tests."""

    def test_threshold_boundary_just_above(self):
        """Exactly at 40% overlap should pass."""
        test = {
            "id": 99,
            "category": "summarization",
            "prompt": "Summarize.",
            "correct_answer": "",
            "reference_facts": ["alpha", "beta", "gamma", "delta", "epsilon"],
            "grading": {"type": "behavioral"},
        }
        # 2 out of 5 = 40%
        result = grade_summarization(test, "This discusses alpha and beta topics.")
        assert result.result == "correct"

    def test_threshold_boundary_just_below(self):
        """Below 40% overlap should fail."""
        test = {
            "id": 99,
            "category": "summarization",
            "prompt": "Summarize.",
            "correct_answer": "",
            "reference_facts": ["alpha", "beta", "gamma", "delta", "epsilon"],
            "grading": {"type": "behavioral"},
        }
        # 1 out of 5 = 20%
        result = grade_summarization(test, "This discusses alpha and nothing else relevant.")
        assert result.result == "incorrect"

    def test_empty_reference_facts(self):
        """Empty reference_facts with empty correct_answer → correct (no comparison)."""
        test = {
            "id": 99,
            "category": "summarization",
            "prompt": "Summarize.",
            "correct_answer": "",
            "reference_facts": [],
            "grading": {"type": "behavioral"},
        }
        result = grade_summarization(test, "Some summary text.")
        assert result.result == "correct"

    def test_refusal(self):
        test = {
            "id": 99,
            "category": "summarization",
            "prompt": "Summarize.",
            "correct_answer": "A summary.",
            "reference_facts": ["summary"],
            "grading": {"type": "behavioral"},
        }
        result = grade_summarization(test, "I'm unable to summarize this.")
        assert result.result == "refused"
