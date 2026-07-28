"""iso8583-fps — a small, dependency-free ISO 8583 codec with a UK Faster Payments profile.

ISO 8583 is the classic card / interbank message format: a 4-digit MTI, a primary
(and optional secondary) bitmap flagging which data elements are present, and typed
data elements framed as fixed / LLVAR / LLLVAR. UK Faster Payments is ISO 8583:1993-based.

This module implements a real, round-trippable codec in two on-the-wire encodings:
  * ASCII  (default)  — printable: hex bitmap, ASCII digits, ASCII length prefixes.
  * binary (binary=True) — how switches actually send it: a raw-byte bitmap, BCD-packed
    numerics (two digits/byte), and BCD length prefixes.

`pack()` and `unpack()` are proven inverses over the field registry. A small FPS message
profile (`fps_request` / `fps_response`) shows how a payment maps onto DEs.

Honest boundary: this is a *structurally-real, FPS-flavoured* profile — not the bit-exact,
licensed Pay.UK data-element map (which is member-only). Swapping in the real assignments
is a data change to `FIELDS`, not a rewrite.

MIT-licensed. From the KibiPay payments-interoperability project — https://kibipay.com
"""

from __future__ import annotations

# ── Data-element registry ─────────────────────────────────────────────────────
# de: (content_type, length_type, max_len, label)
#   content_type: 'n' numeric (left zero-padded fixed), 'an'/'ans' alphanumeric (right space-padded fixed)
#   length_type:  'fixed' | 'llvar' (2-digit len prefix) | 'lllvar' (3-digit)
FIELDS: dict[int, tuple[str, str, int, str]] = {
    3:   ("n",   "fixed",  6,  "Processing code"),
    4:   ("n",   "fixed",  12, "Amount, transaction (minor units)"),
    7:   ("n",   "fixed",  10, "Transmission date & time (MMDDhhmmss)"),
    11:  ("n",   "fixed",  6,  "System trace audit number (STAN)"),
    32:  ("n",   "llvar",  11, "Acquiring institution id (sort code)"),
    37:  ("an",  "fixed",  12, "Retrieval reference number"),
    39:  ("an",  "fixed",  2,  "Response code"),
    49:  ("n",   "fixed",  3,  "Currency code (ISO 4217 numeric)"),
    102: ("ans", "llvar",  28, "Account identification 1 (from)"),
    103: ("ans", "llvar",  28, "Account identification 2 (to)"),
    120: ("ans", "lllvar", 99, "Private: creditor name"),
    121: ("ans", "lllvar", 99, "Private: remittance / reference"),
}

_CCY_NUM = {"GBP": "826", "USD": "840", "EUR": "978", "JPY": "392"}


# ── Bitmap + BCD helpers ──────────────────────────────────────────────────────
def _bits_of(raw: bytes) -> list[int]:
    return [(byte >> (7 - k)) & 1 for byte in raw for k in range(8)]


def _bitmap_bytes(present: list[int]) -> bytes:
    use_secondary = any(de > 64 for de in present)
    raw = bytearray(16 if use_secondary else 8)
    marks = set(present) | ({1} if use_secondary else set())
    for de in marks:
        raw[(de - 1) // 8] |= 1 << (7 - ((de - 1) % 8))
    return bytes(raw)


def _digits_to_bcd(digits: str) -> bytes:
    if len(digits) % 2:
        digits = "0" + digits
    return bytes.fromhex(digits)


# ── pack / unpack ─────────────────────────────────────────────────────────────
def pack(mti: str, fields: dict[int, object], *, binary: bool = False):
    """Encode MTI + {de: value} into an ISO 8583 message (str if ASCII, bytes if binary)."""
    if len(mti) != 4 or not mti.isdigit():
        raise ValueError(f"MTI must be 4 digits, got {mti!r}")
    present = sorted(fields)
    for de in present:
        if de not in FIELDS:
            raise ValueError(f"unknown data element {de}")

    if binary:
        out = bytearray(_digits_to_bcd(mti)) + _bitmap_bytes(present)
        for de in present:
            ctype, ltype, maxlen, _ = FIELDS[de]
            val = str(fields[de])
            if ltype == "fixed":
                out += _digits_to_bcd(val.zfill(maxlen)) if ctype == "n" \
                    else val[:maxlen].ljust(maxlen).encode("ascii")
            else:
                v = val[:maxlen]
                out += _digits_to_bcd(f"{len(v):02d}") if ltype == "llvar" else _digits_to_bcd(f"{len(v):04d}")
                out += _digits_to_bcd(v) if ctype == "n" else v.encode("ascii")
        return bytes(out)

    parts = [mti, _bitmap_bytes(present).hex().upper()]
    for de in present:
        ctype, ltype, maxlen, _ = FIELDS[de]
        val = str(fields[de])
        if ltype == "fixed":
            parts.append(val.zfill(maxlen) if ctype == "n" else val[:maxlen].ljust(maxlen))
        elif ltype == "llvar":
            v = val[:maxlen]; parts.append(f"{len(v):02d}{v}")
        else:
            v = val[:maxlen]; parts.append(f"{len(v):03d}{v}")
    return "".join(parts)


def unpack(message, *, binary: bool = False) -> tuple[str, dict[int, str]]:
    """Decode an ISO 8583 message (str if ASCII, bytes if binary) into (mti, {de: value})."""
    if binary:
        buf = message
        mti = buf[:2].hex(); pos = 2
        bits = _bits_of(buf[pos:pos + 8]); pos += 8
        if bits[0] == 1:
            bits += _bits_of(buf[pos:pos + 8]); pos += 8
        else:
            bits += [0] * 64
        fields: dict[int, str] = {}
        for i in range(1, 128):
            if not bits[i]:
                continue
            de = i + 1; ctype, ltype, maxlen, _ = FIELDS[de]
            if ltype == "fixed":
                if ctype == "n":
                    nb = (maxlen + 1) // 2
                    fields[de] = buf[pos:pos + nb].hex()[-maxlen:]; pos += nb
                else:
                    fields[de] = buf[pos:pos + maxlen].decode("ascii").rstrip(); pos += maxlen
            else:
                if ltype == "llvar":
                    ln = int(buf[pos:pos + 1].hex()); pos += 1
                else:
                    ln = int(buf[pos:pos + 2].hex()); pos += 2
                if ctype == "n":
                    nb = (ln + 1) // 2
                    fields[de] = buf[pos:pos + nb].hex()[-ln:] if ln else ""; pos += nb
                else:
                    fields[de] = buf[pos:pos + ln].decode("ascii"); pos += ln
        return mti, fields

    mti = message[:4]; pos = 4
    bits = _bits_of(bytes.fromhex(message[pos:pos + 16])); pos += 16
    if bits[0] == 1:
        bits += _bits_of(bytes.fromhex(message[pos:pos + 16])); pos += 16
    else:
        bits += [0] * 64
    fields = {}
    for i in range(1, 128):
        if not bits[i]:
            continue
        de = i + 1; ctype, ltype, maxlen, _ = FIELDS[de]
        if ltype == "fixed":
            val = message[pos:pos + maxlen]; pos += maxlen
            if ctype in ("an", "ans"):
                val = val.rstrip()
        elif ltype == "llvar":
            ln = int(message[pos:pos + 2]); pos += 2
            val = message[pos:pos + ln]; pos += ln
        else:
            ln = int(message[pos:pos + 3]); pos += 3
            val = message[pos:pos + ln]; pos += ln
        fields[de] = val
    return mti, fields


# ── FPS profile (works on a plain dict — no framework needed) ─────────────────
def fps_request(payment: dict, *, binary: bool = False):
    """Build an FPS-profiled ISO 8583 financial request (MTI 0200) from a dict:
        {id, reference, amount, currency, debtor:{sort_code,account_number,...},
         creditor:{name,sort_code,account_number}, remittance}
    Processing code 50 = credit push (illustrative, not a licensed Pay.UK code).
    """
    debtor = payment.get("debtor", {}) or {}
    creditor = payment.get("creditor", {}) or {}
    amount_minor = int(round(float(payment.get("amount", 0)) * 100))
    da = f"{debtor.get('sort_code','')}{debtor.get('account_number','')}"
    ca = f"{creditor.get('sort_code','')}{creditor.get('account_number','')}"
    f: dict[int, object] = {
        3: "500000",
        4: amount_minor,
        11: str(payment.get("stan", "000001")).zfill(6)[-6:],
        37: str(payment.get("reference") or payment.get("id", ""))[:12].upper(),
        49: _CCY_NUM.get(str(payment.get("currency", "GBP")).upper(), "826"),
    }
    if debtor.get("sort_code"):
        f[32] = debtor["sort_code"]
    if da:
        f[102] = da
    if ca:
        f[103] = ca
    if creditor.get("name"):
        f[120] = creditor["name"]
    if payment.get("remittance") or payment.get("reference"):
        f[121] = payment.get("remittance") or payment.get("reference")
    return pack("0200", f, binary=binary)


def fps_response(response_code: str, retrieval_ref: str, currency_num: str = "826",
                 amount_minor: int = 0, *, binary: bool = False):
    """Build an FPS ISO 8583 response (MTI 0210) carrying DE39 (response) + DE37 (ref)."""
    return pack("0210", {3: "500000", 4: amount_minor, 37: retrieval_ref[:12].upper(),
                         39: response_code, 49: currency_num}, binary=binary)
