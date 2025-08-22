from app.utils import canonical_url
def test_canonical_url_normalizes_scheme_and_params():
    u = canonical_url('HTTP://Example.com:80/a?b=1&b=1')
    assert u.startswith('https://example.com/a')
