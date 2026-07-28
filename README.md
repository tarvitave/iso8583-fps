# iso8583-fps

A small, dependency-free **ISO 8583 codec** in Python, with a **UK Faster Payments (FPS)** message profile — in both **ASCII** and **BCD/binary** encodings.

ISO 8583 is the classic card / interbank message format (4-digit MTI, a primary + optional
secondary bitmap flagging which data elements are present, and typed data elements framed as
`fixed` / `LLVAR` / `LLLVAR`). **UK Faster Payments is ISO 8583:1993-based**, yet there's almost
no small, readable, open implementation to point people at. This is that.

- **Real codec, two encodings.** `pack()` / `unpack()` are proven inverses over a data-element
  registry — an **ASCII** form (hex bitmap, ASCII digits) and a **BCD/binary** form (raw-byte
  bitmap, BCD-packed numerics) — the way switches actually send it.
- **Zero dependencies.** Pure standard library. One file.
- **FPS profile.** `fps_request()` maps a payment onto an MTI `0200`; `fps_response()` builds an
  MTI `0210` with a response code. Works on a plain `dict` — no framework.

```python
from iso8583_fps import fps_request, unpack, FIELDS

msg = fps_request({
    "reference": "INV-9",
    "amount": "123.45",
    "currency": "GBP",
    "debtor":   {"sort_code": "123456", "account_number": "00087654"},
    "creditor": {"name": "Bob", "sort_code": "654321", "account_number": "00012345"},
    "remittance": "invoice 9",
})
print(msg)                       # 0200B0200000... (ASCII)

mti, fields = unpack(msg)
print(mti)                       # 0200
for de, val in sorted(fields.items()):
    print(de, FIELDS[de][3], "=", val)   # 4 Amount = 000000012345, 49 Currency = 826, ...

# BCD/binary encoding — how a switch actually sends it:
raw = fps_request({...}, binary=True)     # -> bytes
mti, fields = unpack(raw, binary=True)     # round-trips
```

## Install

Copy the single file, or:

```bash
pip install iso8583-fps        # once published to PyPI
```

## Data elements (FPS profile)

| DE | Meaning | Format |
|----|---------|--------|
| 3   | Processing code | n6 |
| 4   | Amount (minor units) | n12 |
| 7   | Transmission date/time | n10 |
| 11  | STAN | n6 |
| 32  | Acquiring institution (sort code) | LLVAR n |
| 37  | Retrieval reference | an12 |
| 39  | Response code | an2 |
| 49  | Currency (ISO 4217 numeric) | n3 |
| 102 | Account id — from | LLVAR ans |
| 103 | Account id — to | LLVAR ans |
| 120 | Creditor name (private) | LLLVAR ans |
| 121 | Remittance / reference (private) | LLLVAR ans |

## Honest boundary

This is a **structurally-real, FPS-flavoured** profile — **not** the bit-exact, licensed Pay.UK /
Vocalink data-element map (that specification is member-only and not public). The MTIs, processing
codes and DE assignments here are reasonable conventions. Swapping in the licensed assignments is a
data change to the `FIELDS` registry, not a rewrite. The generic `pack()`/`unpack()` are standard
ISO 8583 and are correct as-is.

## Why this exists

Built as part of **[KibiPay](https://kibipay.com)** — a payments-interoperability platform that maps
UK bank rails, Mojaloop mobile money, and Solana settlement onto one canonical model (an ISO 20022
superset), so a payment can arrive as ISO 8583 on FPS and leave as ISO 20022 `pacs.008` on another
rail. Free interactive tools (an ISO 8583 decoder, an ISO 20022 viewer, an MT↔MX mapper) live at
**[kibipay.com](https://kibipay.com)**.

## License

MIT — see [LICENSE](LICENSE).
