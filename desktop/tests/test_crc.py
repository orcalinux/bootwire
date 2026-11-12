from bootwire.protocol.crc import crc16

def test_crc_empty():
    # CRC of empty data should equal initial seed 0xFFFF
    assert crc16(b"") == 0xFFFF

def test_crc_ccitt_false():
    # "123456789" → 0x29B1 under CCITT-False
    assert crc16(b"123456789", seed=0xFFFF, xorout=0x0000) == 0x29B1

def test_crc_genibus():
    # "123456789" → 0xD64E under CRC-16/Genibus (xorout=0xFFFF)
    assert crc16(b"123456789", seed=0xFFFF, xorout=0xFFFF) == 0xD64E


def test_crc_with_seed_zero():
    # With zero seed, CRC of single 0x00 is 0x0000
    assert crc16(b"\x00", seed=0x0000) == 0x0000

def test_crc_consistency():
    data = b"hello world"
    # CRC should be deterministic across calls
    assert crc16(data) == crc16(data)
