import pytest
from src.crawler import build_search_query, TokenManager

def test_build_search_query():
    # Test basic query
    query = build_search_query(min_stars=100, language="python")
    assert "language:python" in query
    assert "stars:>=100" in query
    
    # Test with date range
    query = build_search_query(
        min_stars=100,
        language="python",
        created_after="2024-01-01",
        created_before="2024-12-31"
    )
    assert "created:2024-01-01..2024-12-31" in query
    
    # Test with keywords
    query = build_search_query(
        min_stars=100,
        keywords=["machine learning", "AI"]
    )
    assert "machine learning" in query
    assert "AI" in query
    assert "stars:>=100" in query

def test_token_manager():
    # Test single token
    tm = TokenManager("test-token")
    assert tm.get_token() == "test-token"
    
    # Test multiple tokens
    tokens = ["token1", "token2", "token3"]
    tm = TokenManager(tokens)
    
    # Test round-robin behavior
    assert tm.get_token() == "token1"
    assert tm.get_token() == "token2"
    assert tm.get_token() == "token3"
    assert tm.get_token() == "token1"  # Back to first token 