"""Round-trip + edge tests. Run:  python -m pytest  (or: python test_iso8583_fps.py)"""

from iso8583_fps import pack, unpack, fps_request, fps_response, FIELDS


def test_pack_unpack_ascii_roundtrip():
    fields = {3: "500000", 4: 12345, 37: "INV9", 49: "826", 102: "12345600087654"}
    mti, out = unpack(pack("0200", fields))
    assert mti == "0200"
    assert out[4] == "000000012345"      # n12, zero-padded
    assert out[37] == "INV9"             # an, trailing spaces stripped
    assert out[102] == "12345600087654"  # llvar


def test_binary_roundtrip_matches_ascii_fields():
    fields = {3: "500000", 4: 999, 37: "REF1", 49: "840", 120: "Alice", 121: "rent"}
    _, a = unpack(pack("0200", fields))
    _, b = unpack(pack("0200", fields, binary=True), binary=True)
    assert a == b


def test_secondary_bitmap_for_high_des():
    # DE 120/121 are > 64, forcing a secondary bitmap; must still decode.
    mti, out = unpack(pack("0210", {39: "00", 120: "Bob", 121: "ref"}))
    assert mti == "0210" and out[120] == "Bob" and out[121] == "ref"


def test_fps_request_amount_and_currency():
    _, f = unpack(fps_request({"amount": "10.00", "currency": "EUR", "reference": "X"}))
    assert f[4] == "000000001000" and f[49] == "978"


def test_fps_response_carries_de39():
    _, f = unpack(fps_response("00", "REF", amount_minor=500))
    assert f[39] == "00" and f[4] == "000000000500"


def test_unknown_de_rejected():
    try:
        pack("0200", {99: "x"})
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown DE")


def test_field_registry_is_consistent():
    for de, (ctype, ltype, maxlen, label) in FIELDS.items():
        assert ctype in ("n", "an", "ans") and ltype in ("fixed", "llvar", "lllvar")
        assert maxlen > 0 and label


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("ok", name)
    print("all passed")
