# desktop/tests/test_slip.py

import pytest

from bootwire.protocol.slip import END, ESC, SlipReader, decode, encode


def test_encode_wraps_with_end():
    frame = encode(b"ABC")
    assert frame == bytes([END]) + b"ABC" + bytes([END])


def test_escape_sequences():
    assert encode(bytes([END, ESC])) == bytes([END, ESC, 0xDC, ESC, 0xDD, END])


def test_escape_sequences_roundtrip():
    data = bytes([END, ESC, 0x01, 0x02, END, ESC])
    assert decode(encode(data)) == data


@pytest.mark.parametrize("frame", [
    b"",
    b"ABC",
    bytes([END]),
    bytes([END]) + b"ABC",
    b"ABC" + bytes([END]),
])
def test_missing_delimiters_raises(frame):
    with pytest.raises(ValueError):
        decode(frame)


def test_unfinished_escape_raises():
    with pytest.raises(ValueError):
        decode(bytes([END, ESC, END]))


def test_invalid_escape_raises():
    with pytest.raises(ValueError):
        decode(bytes([END, ESC, 0x00, END]))


# ── stream reader (the same state machine the target runs) ──────────────────

def test_reader_byte_by_byte():
    reader = SlipReader()
    frames = []
    for b in encode(bytes([1, END, 2, ESC, 3])):
        frames += reader.feed(bytes([b]))
    assert frames == [bytes([1, END, 2, ESC, 3])]


def test_reader_several_frames_in_one_chunk():
    reader = SlipReader()
    assert reader.feed(encode(b"one") + encode(b"two")) == [b"one", b"two"]


def test_reader_drops_noise_before_first_end():
    reader = SlipReader()
    assert reader.feed(b"boot log text\r\n" + encode(b"frame")) == [b"frame"]


def test_reader_ignores_empty_frames():
    reader = SlipReader()
    assert reader.feed(bytes([END, END, END]) + encode(b"x")) == [b"x"]


def test_reader_drops_frame_with_bad_escape_and_recovers():
    reader = SlipReader()
    bad = bytes([END, 0x41, ESC, 0x00, 0x42, END])
    assert reader.feed(bad + encode(b"good")) == [b"good"]


def test_reader_drops_oversized_frame_and_recovers():
    reader = SlipReader(max_size=4)
    assert reader.feed(encode(b"too long") + encode(b"ok")) == [b"ok"]
