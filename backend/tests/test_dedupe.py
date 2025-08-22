from app.dedupe import DupeFilter
def test_dupefilter_basic():
    d = DupeFilter()
    seen,_ = d.seen('a','hello world')
    assert seen is False
    seen,_ = d.seen('b','hello world!')
    assert seen is True
