"""제목 분리 · 문장 경계 · 붙은 문장 중복 테스트. 예시는 실제 폰 촬영 테스트(10-27)에서 나온 OCR 결과."""
import pytest
from PIL import Image

from app import config
from app.pipeline import OCREngine, Pipeline, clean_card, is_title_line, mark_paragraph_ends, split_sentences


@pytest.mark.parametrize("line", ["How BREAD FAILS", "ON Losing Things", "NOTES On HANDWRITING",
                                  "INSTRCCTIONS FOR THE NEW", "EETTLE", "Notes on Reading Speed"])
def test_mixed_case_titles_are_detected(line):
    assert is_title_line(line)


@pytest.mark.parametrize("line", ["Keys are never lost in interesting places.",
                                  "Dear Miriam, the fog arrived on Tuesday and has",
                                  "1. Remove all packaging and rinse the",
                                  "Salt is not optional."])
def test_body_lines_are_not_titles(line):
    assert not is_title_line(line)


def test_title_is_split_off_and_returned():
    title, text = clean_card([("How BREAD FAILS", 0.9),
                              ("A dense loaf usually means the yeast was tired.", 0.9)])
    assert title == "How Bread Fails"
    assert text == "A dense loaf usually means the yeast was tired."


def test_two_line_title():
    title, text = clean_card([("INSTRUCTIONS FOR THE NEW", 0.9), ("KETTLE", 0.9),
                              ("1. Remove all packaging and rinse the interior.", 0.9)])
    assert title == "Instructions For The New Kettle"
    assert text.startswith("1. Remove")


def test_no_title_when_card_top_is_cut():
    title, _ = clean_card([("there is a second city that almost no one sees.", 0.9)])
    assert title is None


def test_dropped_low_confidence_line_keeps_sentence_end():
    # 'hand.' 를 신뢰도가 낮아 버려도 'copied by' 와 다음 문장이 붙지 않아야 한다
    _, text = clean_card([("A pen moves faster when documents were copied by", 0.9), ("hand.", 0.1),
                          ("Ballpoints changed the geometry of writing.", 0.9)])
    assert split_sentences(text) == ["A pen moves faster when documents were copied by.",
                                     "Ballpoints changed the geometry of writing."]


def test_missed_period_before_sentence_starter():
    _, text = clean_card([("Cursive was taught for speed, not beauty A pen that never leaves the page.", 0.9)])
    assert split_sentences(text) == ["Cursive was taught for speed, not beauty.",
                                     "A pen that never leaves the page."]


def test_proper_nouns_mid_sentence_are_left_alone():
    _, text = clean_card([("They are found in the coat you wore on Thursday, in the bag.", 0.9),
                          ("Paper reached Samarkand around 751 and Baghdad by 793.", 0.9)])
    assert len(split_sentences(text)) == 2


def test_colon_misread_period_at_paragraph_end_is_not_doubled():
    lines = [("The bag you already searched twice,", 0.9), ("on the hook where they belong:", 0.9),
             ("The search itself is the punishment.", 0.9)]
    out = mark_paragraph_ends(lines, [100, 140, 205])
    assert out[1][0] == "on the hook where they belong."


class FakeReader:
    def __init__(self, rows):
        self.rows = rows  # [(y, text)]

    def readtext(self, *_, **__):
        return [([[300, y], [800, y], [800, y + 14], [300, y + 14]], text, 0.9) for y, text in self.rows]


def test_paragraph_gap_ends_sentence_when_last_word_is_missed(monkeypatch):
    monkeypatch.setattr(config, "FAKE_MODELS", False)
    eng = OCREngine("easyocr")
    # 줄 간격 40, 문단 사이만 62 → 'copied by' 뒤에서 문단이 바뀐 것 ('hand.' 는 OCR 이 아예 못 찾음)
    eng._reader = FakeReader([(100, "A pen that never leaves the page moves"),
                              (140, "faster when documents were copied by"),
                              (202, "Ballpoints changed the geometry."),
                              (242, "They need pressure and dislike sharp turns.")])
    [col] = eng.read_columns(Image.new("RGB", (1200, 900)))
    assert col[1][0] == "faster when documents were copied by."
    assert col[0][0] == "A pen that never leaves the page moves"  # 보통 줄 간격에는 안 붙인다


@pytest.fixture()
def pipe(monkeypatch):
    monkeypatch.setattr(config, "FAKE_MODELS", True)
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    p = Pipeline()
    p.load()
    return p


def frame(pipe, monkeypatch, lines):
    monkeypatch.setattr(pipe.ocr, "read_columns", lambda img: [[(t, 0.9) for t in lines]])
    return pipe.process_frame(b"", session="t", frame_no=1, img=Image.new("RGB", (10, 10)))


def test_title_is_saved_in_meta(pipe, monkeypatch):
    r = frame(pipe, monkeypatch, ["ON Losing Things", "Keys are never lost in interesting places."])
    assert [(s["text"], s["meta"]["title"]) for s in r["stored"]] == [
        ("Keys are never lost in interesting places.", "On Losing Things")]


def test_title_keeps_apostrophe():
    title, _ = clean_card([("THE CARTOGRAPHER'S COMPLAINT", 0.9), ("Every map is a lie told for a good reason.", 0.9)])
    assert title == "The Cartographer's Complaint"


def test_glued_sentence_containing_a_stored_one_is_a_duplicate(pipe, monkeypatch):
    frame(pipe, monkeypatch, ["Cursive was taught for speed, not beauty."])
    r = frame(pipe, monkeypatch, ["Cursive was taught for speed, not beautyA pen that never leaves the page."])
    assert r["stored"] == []
    assert r["duplicates"] == 1
