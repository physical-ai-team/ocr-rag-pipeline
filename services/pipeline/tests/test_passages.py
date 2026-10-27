from app.passages import group_passages


def test_groups_by_title_and_merges_ocr_variants():
    rows = [
        {"title": "How Bread Fails", "ts": 1},
        {"title": "How Bread Fails", "ts": 2},
        {"title": "Instructions For The New Kettle", "ts": 3},
        {"title": "Instrcctions For The New Eettle", "ts": 4},   # OCR 오타 → 같은 지문
        {"title": None, "ts": 5},                                # 카드 윗부분이 잘려 제목 없음
        {"title": "Instructions For The New Kettle", "ts": 6},
    ]
    out = group_passages(rows)
    assert [(p["no"], p["title"], p["sentences"]) for p in out["passages"]] == [
        (1, "How Bread Fails", 2),
        (2, "Instructions For The New Kettle", 3),   # 가장 많이 나온 표기가 대표 제목
    ]
    assert out["passages"][1]["last_ts"] == 6
    assert out["untitled_sentences"] == 1
    assert out["total_sentences"] == 6


def test_different_passages_are_not_merged():
    out = group_passages([{"title": "Notes on Reading Speed", "ts": 1},
                          {"title": "Notes on Handwriting", "ts": 2},
                          {"title": "On Losing Things", "ts": 3}])
    assert len(out["passages"]) == 3
