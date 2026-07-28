"""Runnable example: build an FPS-profiled ISO 8583 payment, decode it, and show
that the BCD/binary encoding round-trips. Run:  python example.py"""

from iso8583_fps import fps_request, fps_response, unpack, FIELDS

payment = {
    "reference": "INV-9",
    "amount": "123.45",
    "currency": "GBP",
    "debtor":   {"sort_code": "123456", "account_number": "00087654"},
    "creditor": {"name": "Bob Builder", "sort_code": "654321", "account_number": "00012345"},
    "remittance": "invoice 9",
}

# --- ASCII encoding ---------------------------------------------------------
msg = fps_request(payment)
print("ASCII request :", msg)
mti, fields = unpack(msg)
print("MTI           :", mti)
for de, val in sorted(fields.items()):
    print(f"  DE {de:<3} {FIELDS[de][3]:<34} = {val!r}")

# --- BCD / binary encoding round-trips --------------------------------------
raw = fps_request(payment, binary=True)
mti_b, fields_b = unpack(raw, binary=True)
assert fields_b[4] == fields[4], "amount must survive the binary round-trip"
print("\nbinary bytes  :", raw.hex())
print("binary MTI    :", mti_b, "amount DE4 =", fields_b[4])

# --- A response (MTI 0210, DE39 approved) -----------------------------------
resp = fps_response("00", retrieval_ref="INV-9", amount_minor=12345)
rmti, rfields = unpack(resp)
print("\nresponse MTI  :", rmti, "code DE39 =", rfields[39])
