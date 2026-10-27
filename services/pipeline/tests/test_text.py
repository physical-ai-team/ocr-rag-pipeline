"""OCR 결과 정리 규칙 테스트 (모델 없이 가짜 박스로 확인)"""
from PIL import Image

from app import config
from app.pipeline import OCREngine, clean_text, is_heading


def test_heading_line_is_removed_from_first_sentence():
    lines = [("THE QUIET MACHINERT 0F CITIES", 0.9),
             ("Beneath every pavement there is a second city.", 0.9)]
    assert clean_text(lines) == "Beneath every pavement there is a second city."


def test_heading_only_removed_at_top():
    assert is_heading("NOTES ON READING SPEED")
    assert not is_heading("Fill to a level between the MIN and MAX marks.")
    lines = [("Read the warning below carefully.", 0.9), ("DO NOT IMMERSE THE BASE IN WATER", 0.9)]
    assert "DO NOT IMMERSE" in clean_text(lines)


def test_ampersand_between_words_becomes_a():
    assert clean_text([("there is & second city that almost no one sees.", 0.9)]) == \
        "there is a second city that almost no one sees."
    assert "Smith & Wesson" in clean_text([("Made by Smith & Wesson in 1899.", 0.9)])


class FakeReader:
    def __init__(self, boxes):
        self.boxes = boxes

    def readtext(self, *_, **__):
        return [([[x0, y], [x1, y], [x1, y + 14], [x0, y + 14]], text, 0.9)
                for x0, x1, y, text in self.boxes]


def card(x0, x1, name):
    return [(x0, x1, 100 + i * 20, f"{name} line {i} of the card.") for i in range(4)]


def test_cut_cards_are_dropped(monkeypatch):
    monkeypatch.setattr(config, "FAKE_MODELS", False)
    monkeypatch.setattr(config, "FULL_SENTENCES", True)
    eng = OCREngine("easyocr")
    eng._reader = FakeReader(
        card(0, 250, "left-edge")      # 이미지 왼쪽 끝에 닿음 → 버림
        + card(300, 600, "full-a")
        + card(650, 950, "full-b")
        + card(1000, 1150, "narrow")   # 다른 카드보다 좁음(옆이 잘림) → 버림
    )
    cols = eng.read_columns(Image.new("RGB", (1600, 900)))
    names = [c[0][0].split()[0] for c in cols]
    assert names == ["full-a", "full-b"]
