import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mock_data import PROBLEM_ANALYSES
from app.stable_data import (
    CURATED_PROBLEMS, CURATED_PROBLEM_SPECS, CURATED_RELATED_PROBLEMS, validate_curated_data,
)


EXPECTED_SLUGS = {
    "two-sum", "contains-duplicate", "valid-anagram", "group-anagrams",
    "valid-palindrome", "two-sum-ii-input-array-is-sorted", "3sum",
    "best-time-to-buy-and-sell-stock", "longest-substring-without-repeating-characters",
    "longest-repeating-character-replacement", "valid-parentheses", "min-stack",
    "daily-temperatures", "binary-search", "search-in-rotated-sorted-array",
    "reverse-linked-list", "merge-two-sorted-lists", "maximum-depth-of-binary-tree",
    "number-of-islands", "climbing-stairs",
}


class CuratedDataTests(unittest.TestCase):
    def test_catalog_has_the_requested_twenty_problems_and_valid_approaches(self):
        validate_curated_data()
        self.assertEqual(set(CURATED_PROBLEMS), EXPECTED_SLUGS)
        self.assertEqual(set(CURATED_PROBLEM_SPECS), EXPECTED_SLUGS)
        self.assertEqual(set(CURATED_RELATED_PROBLEMS), EXPECTED_SLUGS)
        self.assertEqual(sum(len(p["approaches"]) for p in CURATED_PROBLEMS.values()), 41)
        self.assertEqual(sum(
            len(a["recognitionSignals"]["bullets"])
            for p in CURATED_PROBLEMS.values() for a in p["approaches"]
        ), 84)
        self.assertEqual(sum(
            len(cards) for groups in CURATED_RELATED_PROBLEMS.values() for cards in groups.values()
        ), 68)
        for slug, spec in CURATED_PROBLEM_SPECS.items():
            with self.subTest(problem_spec=slug):
                self.assertIn(spec["difficulty"], {"Easy", "Medium", "Hard"})
                self.assertTrue(spec["title"].strip())
                self.assertTrue(spec["summary"].strip())
                self.assertGreaterEqual(len(spec["constraints"]), 1)
                self.assertGreaterEqual(len(spec["examples"]), 1)
                self.assertEqual(set(spec["submissionTemplates"]), {"python", "java", "javascript", "cpp"})
        key_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for slug, problem in CURATED_PROBLEMS.items():
            with self.subTest(slug=slug):
                approaches = problem["approaches"]
                self.assertIn(len(approaches), (1, 2, 3))
                self.assertEqual(sum(a["isPrimary"] for a in approaches), 1)
                self.assertEqual([a["displayOrder"] for a in approaches], list(range(1, len(approaches) + 1)))
                self.assertEqual(len({a["id"] for a in approaches}), len(approaches))
                for approach in approaches:
                    self.assertRegex(approach["id"], key_pattern)
                    for field in ("name", "pattern", "summary"):
                        self.assertTrue(approach[field].strip())
                    self.assertGreaterEqual(len(approach["thinkingSteps"]), 2)
                    signals = approach["recognitionSignals"]
                    self.assertIn(len(signals["bullets"]), (2, 3))
                    self.assertTrue(all(text.strip() for text in signals["bullets"]))
                    if signals.get("quote") is not None:
                        self.assertTrue(signals["quote"].strip())

    def test_related_cards_are_curated_without_requiring_every_category(self):
        empty_categories = 0
        for slug, groups in CURATED_RELATED_PROBLEMS.items():
            with self.subTest(slug=slug):
                self.assertEqual(set(groups), {"easier", "similar", "harder"})
                cards = [card for category in groups.values() for card in category]
                self.assertGreaterEqual(len(cards), 2)
                self.assertEqual(len({card["slug"] for card in cards}), len(cards))
                self.assertNotIn(slug, {card["slug"] for card in cards})
                empty_categories += sum(not category for category in groups.values())
                for card in cards:
                    self.assertIn(card["difficulty"], {"Easy", "Medium", "Hard"})
                    self.assertTrue(card["title"].strip())
                    self.assertTrue(card["reason"].strip())
        self.assertGreater(empty_categories, 0)

    def test_full_mock_guidance_remains_limited_to_original_three(self):
        self.assertEqual(set(PROBLEM_ANALYSES), {
            "two-sum", "valid-parentheses", "longest-substring-without-repeating-characters"
        })
        self.assertLess(set(PROBLEM_ANALYSES), set(CURATED_PROBLEMS))
