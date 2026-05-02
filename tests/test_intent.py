# tests/test_intent.py
import unittest
import sys
import os

# Add project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.intent_parser import parse_intent, extract_features

class TestIntentParser(unittest.TestCase):
    """Unit tests for the intent_parser module."""

    def test_parse_intent(self):
        """Test the intent parsing logic."""
        self.assertEqual(parse_intent("推荐一部科幻电影"), "recommend")
        self.assertEqual(parse_intent("有没有类似黑客帝国的电影"), "recommend")
        self.assertEqual(parse_intent("搜索一下《流浪地球》"), "search")
        self.assertEqual(parse_intent("为什么给我推荐这个？"), "explain")
        self.assertEqual(parse_intent("一部关于太空旅行的电影"), "recommend") # Default case

    def test_extract_features(self):
        """Test the feature extraction logic."""
        # Test keyword extraction
        features1 = extract_features("推荐类似流浪地球的电影")
        self.assertIn("流浪地球", features1["keywords"])

        features2 = extract_features("找一部关于星际穿越的片子")
        self.assertIn("星际穿越", features2["keywords"])

        # Test genre extraction
        features3 = extract_features("我想看一部科幻喜剧电影")
        self.assertIn("科幻", features3["genres"])
        self.assertIn("喜剧", features3["genres"])

        # Test no features found
        features4 = extract_features("随便来点什么")
        self.assertEqual(features4["keywords"], [])
        self.assertEqual(features4["genres"], [])

        # Test mood (should be None)
        self.assertIsNone(features1["mood"])

if __name__ == '__main__':
    print("--- Running Unit Tests for intent_parser.py ---")
    unittest.main(verbosity=2)
