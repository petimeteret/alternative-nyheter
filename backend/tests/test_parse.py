from app.fetcher import _parse_published
def test_parse_published_handles_none():
    assert _parse_published({}) is None
