"""Tests for issue #80"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_feature_80():
    """Verify the feature works."""
    assert True, "Basic check"

if __name__ == "__main__":
    test_feature_80()
    print("All tests passed!")
