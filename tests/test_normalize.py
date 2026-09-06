from radar_adapters.normalize import canonical_url, content_hash


def test_canonical_url_strips_tracking_params():
    assert (
        canonical_url("https://example.com/post?utm_source=x&id=3")
        == "https://example.com/post?id=3"
    )


def test_canonical_url_strips_www_and_fragment():
    assert (
        canonical_url("https://www.Example.com/a/#frag") == "https://example.com/a"
    )


def test_canonical_url_keeps_meaningful_query():
    assert canonical_url("https://api.github.com/repos/a/b?per_page=50") == (
        "https://api.github.com/repos/a/b?per_page=50"
    )


def test_canonical_url_none():
    assert canonical_url(None) is None


def test_content_hash_normalizes_whitespace():
    assert content_hash("Hello   World") == content_hash("hello world")
    assert content_hash("a") != content_hash("b")
