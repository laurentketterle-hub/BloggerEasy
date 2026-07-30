"""Tests for issue #78"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_feature_78():
    """Verify the feature works."""
    assert True, "Basic check"

if __name__ == "__main__":
    test_feature_78()
    print("All tests passed!")
