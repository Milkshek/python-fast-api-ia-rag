import pytest

from app.documents.chunking import TextChunker


@pytest.mark.parametrize(
    "content", ["", "   \n", "a", "abcdefgh", "abcdefghijk", "été 🐍 long texte"]
)
def test_windows_preserve_offsets_and_cover_non_whitespace(content):
    chunks = TextChunker(chunk_size=8, overlap=2).split(content)
    covered = set()
    for chunk in chunks:
        assert 0 < len(chunk.text) <= 8
        assert chunk.text.strip()
        assert chunk.text == content[chunk.start_offset : chunk.end_offset]
        covered.update(range(chunk.start_offset, chunk.end_offset))
    assert all(i in covered for i, char in enumerate(content) if not char.isspace())
    if len(content) == 8:
        assert len(chunks) == 1


def test_overlap_and_tail_are_exact():
    chunks = TextChunker(chunk_size=8, overlap=2).split("abcdefghijklmnopq")
    assert [(c.start_offset, c.end_offset, c.text) for c in chunks] == [
        (0, 8, "abcdefgh"),
        (6, 14, "ghijklmn"),
        (12, 17, "mnopq"),
    ]


@pytest.mark.parametrize(
    ("size", "overlap"), [(0, 0), (-1, 0), (8, -1), (8, 8), (8, 9)]
)
def test_invalid_windows_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        TextChunker(chunk_size=size, overlap=overlap)


def test_zero_overlap_is_supported():
    chunks = TextChunker(chunk_size=3, overlap=0).split("abcdefg")
    assert [c.text for c in chunks] == ["abc", "def", "g"]
