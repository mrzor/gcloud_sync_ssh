from gcloud_sync_ssh.util.globbing import matches_any, looks_like_pattern, has_pattern


def test_looks_like_pattern():
    assert looks_like_pattern("a*b")
    assert looks_like_pattern("*ba")
    assert looks_like_pattern("ba*")
    assert looks_like_pattern("b[abc]")
    assert looks_like_pattern("a?c")
    assert not looks_like_pattern("ab")
    assert not looks_like_pattern("")


def test_has_pattern():
    assert has_pattern("a*")
    assert has_pattern(["a?c", "", "ab"])
    assert not has_pattern("toto")
    assert not has_pattern(["", "x", "abc", "def"])


def test_matches_any_without_globs():
    assert matches_any("placeholder")
    assert matches_any("placeholder", [])
    assert matches_any("placeholder", None)


def test_matches_any():
    assert matches_any("aab", ["aa?"])
    assert matches_any("aab", ["a*"])
    assert matches_any("aab", ["aa[ab]"])

    assert not matches_any("aab", ["bb?"])
    assert not matches_any("aab", ["b*b"])
    assert not matches_any("aab", ["[cb][cd][ce]"])
