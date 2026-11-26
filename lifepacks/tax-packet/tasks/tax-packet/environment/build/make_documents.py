#!/usr/bin/env python3
"""Generate the synthetic source documents D01-D12 and the gold table for Task #102.

Deterministic: the same script always writes byte-identical PDFs (no timestamps or
random IDs). Every page carries "SYNTHETIC BENCHMARK NOT FOR FILING". All people,
employers, banks, brokerages and amounts are fictional.

Outputs (relative to this script's task directory):
  environment/workspace/documents/D01-...pdf .. D12-...pdf
  tests/gold.json   (private to the verifier; never mounted for the agent)

Run:  python3 -I environment/build/make_documents.py
"""
import hashlib
import json
import os
import sys

TASK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(TASK, "environment", "workspace", "documents")
GOLD = os.path.join(TASK, "tests", "gold.json")
WATERMARK = "SYNTHETIC BENCHMARK NOT FOR FILING"


def money(cents):
    return f"{cents / 100:,.2f}"


def pdf_bytes(title, lines):
    """A one-page PDF 1.4 with a Helvetica text layer and a correct xref table."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    body = [WATERMARK, title, ""] + lines + ["", WATERMARK]
    ops = ["BT", "/F1 11 Tf", "13 TL", "54 760 Td"]
    for i, line in enumerate(body):
        ops.append(f"({esc(line)}) Tj" if i == 0 else f"T* ({esc(line)}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Title (" + esc(title).encode("latin-1") + b") /Producer (PALE synthetic fixture) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


# ---- document facts (amounts in cents) ----
W2 = {
    "atlas": dict(employer="Atlas Labs, Inc.", period="January 1 to June 13, 2025", wages=4_000_000, wh=450_000),
    "brook": dict(employer="Brook Systems LLC", period="June 30 to December 31, 2025", wages=6_000_000, wh=750_000),
}
NF_ORIG = dict(div1a=46_000, div1b=40_000, proceeds=1_200_000, basis=1_090_000)
NF_CORR = dict(div1a=50_000, div1b=40_000, proceeds=1_200_000, basis=1_170_000)
RW = dict(div1a=30_000, div1b=20_000, proceeds=800_000, basis=760_000,
          trades=[("RW-25-0412", "2025-04-12", 300_000, 285_000), ("RW-25-0807", "2025-08-07", 280_000, 271_000), ("RW-25-1119", "2025-11-19", 220_000, 204_000)])
NF_2024 = dict(div1a=41_000, div1b=35_000, proceeds=650_000, basis=610_000)
CEDAR_INT = 30_000
BAYVIEW_INT = 7_500


def w2(key, doc_id):
    d = W2[key]
    return pdf_bytes(f"Form W-2 Wage and Tax Statement 2025 - {d['employer']}", [
        f"Employer: {d['employer']}", "Employee: Rowan Ellis", "Employee ID: last four 7731",
        f"Employment period: {d['period']}",
        f"Box 1  Wages, tips, other compensation: {money(d['wages'])}",
        f"Box 2  Federal income tax withheld: {money(d['wh'])}",
        "Issued: 2026-01-27", f"Document reference: {doc_id}",
    ])


def nf_statement(vals, status, issued, extra):
    return pdf_bytes(f"Northfield Brokerage 2025 Consolidated Form 1099 {status}".strip(), [
        "Account holder: Rowan Ellis", "Account: individual brokerage, last four 2208", f"Issued: {issued}",
        "Form 1099-DIV",
        f"  Box 1a  Total ordinary dividends: {money(vals['div1a'])}",
        f"  Box 1b  Qualified dividends: {money(vals['div1b'])}",
        "Form 1099-B (covered securities, basis reported to the IRS)",
        f"  Total proceeds: {money(vals['proceeds'])}",
        f"  Total cost basis: {money(vals['basis'])}",
    ] + extra)


def build():
    docs = {}
    docs["D01-atlas-w2-2025.pdf"] = w2("atlas", "AT-W2-2025-7731")
    docs["D02-brook-w2-2025.pdf"] = w2("brook", "BR-W2-2025-7731")
    docs["D03-northfield-1099-2025.pdf"] = nf_statement(NF_ORIG, "", "2026-02-14", ["Statement ID: NF-2025-2208-A"])
    docs["D04-northfield-1099-2025-export.pdf"] = nf_statement(NF_ORIG, "", "2026-02-14", ["Statement ID: NF-2025-2208-A", "Downloaded copy exported 2026-02-16 from online account."])
    docs["D05-northfield-1099-2025-corrected.pdf"] = nf_statement(NF_CORR, "CORRECTED", "2026-03-02", [
        "Statement ID: NF-2025-2208-B",
        "CORRECTED: this statement replaces statement NF-2025-2208-A (issued 2026-02-14) in full.",
        "Corrected items: 1099-DIV box 1a; 1099-B cost basis for two lots.",
    ])
    docs["D06-northfield-1099-2025-forwarded.pdf"] = docs["D03-northfield-1099-2025.pdf"]
    rw_lines = ["Account holder: Rowan Ellis", "Account: individual brokerage, last four 5160", "Issued: 2026-02-12",
                "Form 1099-DIV", f"  Box 1a  Total ordinary dividends: {money(RW['div1a'])}", f"  Box 1b  Qualified dividends: {money(RW['div1b'])}",
                "Form 1099-B (covered securities, basis reported to the IRS)"]
    rw_lines += [f"  {tid}  sold {d}  proceeds {money(p)}  cost basis {money(b)}" for tid, d, p, b in RW["trades"]]
    rw_lines += [f"  Total proceeds: {money(RW['proceeds'])}", f"  Total cost basis: {money(RW['basis'])}"]
    docs["D07-ridgeway-1099-2025.pdf"] = pdf_bytes("Ridgeway Invest 2025 Tax Statement", rw_lines)
    docs["D08-ridgeway-1099-2025-supplement.pdf"] = pdf_bytes("Ridgeway Invest 2025 Supplemental Information", [
        "Account holder: Rowan Ellis", "Account: individual brokerage, last four 5160",
        "Supplemental detail for sales already reported on the 2025 Tax Statement.", "Not a separate tax form; amounts are included in the Tax Statement totals."]
        + [f"  {tid}  sold {d}  proceeds {money(p)}  cost basis {money(b)}  holding period: long term  wash sale: none" for tid, d, p, b in RW["trades"]])
    docs["D09-cedar-1099-int-2025.pdf"] = pdf_bytes("Cedar Bank Form 1099-INT 2025", [
        "Recipient: Rowan Ellis", "Account: checking, last four 0937", "Issued: 2026-01-29", f"Box 1  Interest income: {money(CEDAR_INT)}"])
    docs["D10-bayview-1099-int-2025.pdf"] = pdf_bytes("Bayview Bank Form 1099-INT 2025", [
        "Recipient: Rowan Ellis", "Account: savings, last four 4410 (closed 2025-08-29)", "Issued: 2026-03-10", f"Box 1  Interest income: {money(BAYVIEW_INT)}"])
    docs["D11-northfield-1099-2024.pdf"] = pdf_bytes("Northfield Brokerage 2024 Consolidated Form 1099", [
        "Account holder: Rowan Ellis", "Account: individual brokerage, last four 2208", "Issued: 2025-02-14",
        "Form 1099-DIV", f"  Box 1a  Total ordinary dividends: {money(NF_2024['div1a'])}", f"  Box 1b  Qualified dividends: {money(NF_2024['div1b'])}",
        "Form 1099-B", f"  Total proceeds: {money(NF_2024['proceeds'])}", f"  Total cost basis: {money(NF_2024['basis'])}"])
    docs["D12-tax-organizer-2024.pdf"] = pdf_bytes("Morgan Lee Tax Advisory - 2024 Tax Organizer for Rowan Ellis", [
        "Prepared for the 2024 tax year. Sent 2025-03-03.", "Employer: Atlas Labs, Inc.", "Accounts: Northfield Brokerage, Cedar Bank, Bayview Bank savings.",
        "Please return the completed organizer with your 2024 forms."])

    # Gold table: reported fields per checkpoint, in cents. S1 has no field values.
    current = {
        "S2": ["D01", "D02", "D03", "D07", "D09"],
        "S3": ["D01", "D02", "D05", "D07", "D09"],
        "S4": ["D01", "D02", "D05", "D07", "D09"],
        "S5": ["D01", "D02", "D05", "D07", "D09", "D10"],
    }
    per_doc = {
        "D01": dict(wages=W2["atlas"]["wages"], withholding=W2["atlas"]["wh"]),
        "D02": dict(wages=W2["brook"]["wages"], withholding=W2["brook"]["wh"]),
        "D03": dict(dividends_1a=NF_ORIG["div1a"], dividends_1b=NF_ORIG["div1b"], proceeds=NF_ORIG["proceeds"], basis=NF_ORIG["basis"]),
        "D05": dict(dividends_1a=NF_CORR["div1a"], dividends_1b=NF_CORR["div1b"], proceeds=NF_CORR["proceeds"], basis=NF_CORR["basis"]),
        "D07": dict(dividends_1a=RW["div1a"], dividends_1b=RW["div1b"], proceeds=RW["proceeds"], basis=RW["basis"]),
        "D09": dict(interest=CEDAR_INT),
        "D10": dict(interest=BAYVIEW_INT),
        "D11": dict(dividends_1a=NF_2024["div1a"], dividends_1b=NF_2024["div1b"], proceeds=NF_2024["proceeds"], basis=NF_2024["basis"]),
    }
    fields = ["wages", "withholding", "interest", "dividends_1a", "dividends_1b", "proceeds", "basis"]
    checkpoints = {}
    for cp, ids in current.items():
        totals = {f: 0 for f in fields}
        for i in ids:
            for f, v in per_doc[i].items():
                totals[f] += v
        checkpoints[cp] = {"current_documents": ids, "totals_cents": totals}
    # Amounts a known identity mistake adds on top of the correct totals (E2). The grader checks
    # that no saved summary equals correct total + one of these, so it never hard-codes amounts.
    error_offsets = {
        "northfield_counted_twice": dict(proceeds=[NF_ORIG["proceeds"], NF_CORR["proceeds"]], dividends_1a=[NF_ORIG["div1a"], NF_CORR["div1a"]]),
        "ridgeway_supplement_counted": dict(proceeds=[sum(t[2] for t in RW["trades"])], basis=[sum(t[3] for t in RW["trades"])]),
        "prior_year_counted": dict(proceeds=[NF_2024["proceeds"]], dividends_1a=[NF_2024["div1a"]]),
    }
    expected_final = dict(wages=10_000_000, withholding=1_200_000, interest=37_500, dividends_1a=80_000, dividends_1b=60_000, proceeds=2_000_000, basis=1_930_000)
    assert checkpoints["S5"]["totals_cents"] == expected_final, checkpoints["S5"]
    assert checkpoints["S2"]["totals_cents"]["dividends_1a"] == 76_000 and checkpoints["S2"]["totals_cents"]["basis"] == 1_850_000
    assert checkpoints["S4"]["totals_cents"]["interest"] == 30_000

    os.makedirs(OUT, exist_ok=True)
    hashes = {}
    for name, data in sorted(docs.items()):
        with open(os.path.join(OUT, name), "wb") as fh:
            fh.write(data)
        hashes[name.split("-")[0]] = {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    roles = {
        "D01": "current", "D02": "current", "D03": "superseded_original", "D04": "duplicate_of_D03",
        "D05": "current_correction", "D06": "reforwarded_original", "D07": "current", "D08": "supplement_no_new_amounts",
        "D09": "current", "D10": "current_released_2026-03-10", "D11": "prior_year_reference", "D12": "prior_year_reference",
    }
    gold = {
        "task": "tax-packet", "currency": "USD", "fields": fields,
        "documents": {k: {**v, "role": roles[k], "reported_cents": per_doc.get(k, {})} for k, v in hashes.items()},
        "delivered_set": checkpoints["S5"]["current_documents"],
        "checkpoints": checkpoints,
        "error_offsets_cents": error_offsets,
    }
    os.makedirs(os.path.dirname(GOLD), exist_ok=True)
    with open(GOLD, "w") as fh:
        json.dump(gold, fh, indent=2)
        fh.write("\n")
    total = sum(v["bytes"] for v in hashes.values())
    print(f"wrote {len(docs)} PDFs ({total} bytes) and tests/gold.json")


if __name__ == "__main__":
    sys.exit(build())
