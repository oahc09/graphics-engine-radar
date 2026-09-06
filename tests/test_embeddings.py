from radar_intelligence.embeddings import HashingEmbedder, cosine

SAME = "wgpu adds new WebGPU backend with compute shader support"
DIFF = "Blender releases Cycles GPU rendering improvement for production"


def test_hashing_embedder_dim_and_norm():
    e = HashingEmbedder(256)
    v = e.embed(SAME)
    assert len(v) == 256
    assert abs(sum(x * x for x in v) - 1.0) < 1e-6


def test_similar_texts_score_higher_than_unrelated():
    e = HashingEmbedder(256)
    a = e.embed(SAME)
    b = e.embed(SAME + " (release notes)")
    c = e.embed(DIFF)
    assert cosine(a, b) > cosine(a, c)
    assert cosine(a, b) > 0.5
    assert cosine(a, c) < cosine(a, b)


def test_cosine_self_is_one():
    e = HashingEmbedder(256)
    v = e.embed(SAME)
    assert abs(cosine(v, v) - 1.0) < 1e-6
