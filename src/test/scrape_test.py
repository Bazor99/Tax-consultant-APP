import pytest
from server.tools import search_website  

@pytest.mark.timeout(30)
def test_search_website_returns_chunks():
    # Use a lightweight, stable page for testing
    url = "https://www.irs.gov/"  
    chunks = search_website(url, chunk_size=500, overlap=50)
    
    # 1. You should get at least one chunk
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    
    # 2. Chunks shouldn’t be empty strings
    assert all(isinstance(c, str) and len(c) > 0 for c in chunks)
    
    # 3. Check that some known text appears
    concatenated = " ".join(chunks).lower()
    assert "example domain" in concatenated

@pytest.mark.parametrize("bad_url", ["not a url", "https://doesnotexist.tld"])
def test_search_website_handles_errors_gracefully(bad_url):
    with pytest.raises(Exception):
        search_website(bad_url)
