from scripts.cosine_sanity import score_from_distance


def test_score_from_distance_converts_cosine_distance():
    assert score_from_distance(0.0) == 1.0
    assert score_from_distance(0.12345) == 0.8765
