#!/usr/bin/env python3
"""Generate Sam's 2025 household records and the hidden obligation ledger for Task #129.

Deterministic: the same script always writes byte-identical PDFs (fixed seed, no timestamps
or random IDs). Every page carries "SYNTHETIC BENCHMARK DATA". The household, employer,
bank, card issuer, provider, transactions and correspondence are fictional.

Outputs (relative to the task directory):
  environment/workspace/documents/common/     records visible before S1 (both fixtures)
  environment/workspace/documents/fixture-A/  the Dec 31 remittance allocating the $186 to Boston
  environment/workspace/documents/fixture-B/  the same remittance allocating it to Albany
  environment/workspace/documents/followups/  records a session boundary may release (S3, S4)
  environment/workspace/documents/catalog.json  file IDs, folders, availability and hashes
  tests/gold.json   hidden obligation ledger and expected state (verifier only; never mounted)

Run:  python3 -I environment/build/make_records.py
"""
import hashlib
import json
import os
import random
import shutil
import sys
from datetime import date, timedelta

TASK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(TASK, "environment", "workspace", "documents")
GOLD = os.path.join(TASK, "tests", "gold.json")
WATERMARK = "SYNTHETIC BENCHMARK DATA - FICTIONAL HOUSEHOLD"

# ---------------- parties ----------------
SAM = "Sam Calder"
BANK = dict(name="Larchmont Savings Bank", account="checking ending 3318", last4="3318", disputes="disputes@larchmontsavings.example")
CARD = dict(name="Corvid Rewards Visa", account="card ending 9042", last4="9042", disputes="disputes@corvidcard.example")
EMPLOYER = dict(name="Tallis Freight Analytics", payroll="payroll@tallisfreight.example", employee_id="TF-20417")
PROVIDER = dict(name="Brightline Fiber", billing="billing@brightlinefiber.example", account="BF-55120")
ADDRESSES = {"payroll": [EMPLOYER["payroll"]], "provider": [PROVIDER["billing"]], "bank": [BANK["disputes"], CARD["disputes"]]}

AGREEMENT_ID = "BF-AGR-2024-0815"
PLAN_FEE, DEVICE_FEE, LATE_FEE = 6_000, 800, 1_200      # cents
DEVICE = "Wi-Fi gateway GW-7Q21"
DUP_MONTHS = (10, 11, 12)
LATE_FEE_MONTH = 6                                      # charged on the June invoice for the May bill
TAKE_HOME = 200_000
TRIPS = {
    "boston": dict(report="ER-2025-112", city="Boston", ticket="AMX-58213", bought=date(2025, 11, 3), travel=date(2025, 11, 6), approved=date(2025, 12, 5), amount=18_600),
    "albany": dict(report="ER-2025-118", city="Albany", ticket="AMX-60477", bought=date(2025, 11, 17), travel=date(2025, 11, 20), approved=date(2025, 12, 12), amount=18_600),
}
HARTFORD = dict(report="ER-2025-031", city="Hartford", ticket="AMX-41960", bought=date(2025, 3, 18), travel=date(2025, 3, 21), approved=date(2025, 3, 28), amount=14_250)
TRANSFER = dict(ref="TRF-82214", day=date(2025, 8, 22), amount=60_000)
PARKING = [dict(ticket="MP-30418", place="Pearl St Garage", time="08:12", amount=2_400),
           dict(ticket="MP-30452", place="Union Station Lot", time="17:46", amount=2_400)]
PARKING_DAY = date(2025, 9, 12)
DEC_DEPOSIT = "DEP-2025-1231-TF"
REMITTANCE = "RM-2025-1231"
FIXTURES = {"A": "boston", "B": "albany"}               # which trip the Dec 31 remittance paid


def money(c):
    sign = "-" if c < 0 else ""
    return f"{sign}{abs(c) / 100:,.2f}"


def pdf_bytes(title, lines):
    """One or more pages, PDF 1.4, Helvetica text layer, correct xref table."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    body = [title, ""] + lines
    per_page = 50
    pages = [body[i:i + per_page] for i in range(0, len(body), per_page)] or [[title]]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for n, page in enumerate(pages):
        ops = ["BT", "/F1 9 Tf", "12 TL", "48 770 Td", f"({esc(WATERMARK)}) Tj"]
        ops += [f"T* ({esc(line)}) Tj" for line in page]
        ops += ["T* ()Tj", f"T* ({esc(WATERMARK)} - page {n + 1} of {len(pages)}) Tj", "ET"]
        stream = "\n".join(ops).encode("latin-1")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        content_id = len(objects)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>".encode())
        kids.append(len(objects))
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    objects.append(b"<< /Title (" + esc(title).encode("latin-1") + b") /Producer (PALE synthetic fixture) >>")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def friday_on_or_before(d):
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def month_end(y, m):
    return (date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)) - timedelta(days=1)


# ---------------- the 2025 ledger ----------------
def build_ledger():
    rng = random.Random(129)
    checking, card = [], []           # (date, description, reference, amount_cents)
    payslips, invoices = [], []

    # payroll: semi-monthly, 15th and last day, moved to the Friday before a weekend
    n = 0
    for m in range(1, 13):
        for d in (date(2025, m, 15), month_end(2025, m)):
            n += 1
            pay = friday_on_or_before(d)
            reimb, rid = 0, None
            if pay == friday_on_or_before(date(2025, 4, 30)):
                reimb, rid = HARTFORD["amount"], "RM-2025-0430"
            if (m, d.day) == (12, 31):
                reimb, rid = TRIPS["boston"]["amount"], REMITTANCE
            ref = DEC_DEPOSIT if (m, d.day) == (12, 31) else f"DEP-2025-{pay:%m%d}-TF"
            payslips.append(dict(id=f"PS-2025-{n:02d}", pay_date=pay, period_end=d, net=TAKE_HOME, reimb=reimb, deposit=TAKE_HOME + reimb, ref=ref, remittance=rid))
            checking.append((pay, f"PAYROLL {EMPLOYER['name'].upper()}", ref, TAKE_HOME + reimb))

    # internet: invoice on the 5th for that month's service, due the 20th; paid from checking
    for m in range(1, 13):
        lines = [(f"Fiber 500 plan, service {date(2025, m, 1):%b} 1-{month_end(2025, m).day}", PLAN_FEE),
                 (f"{DEVICE} rental, service {date(2025, m, 1):%b} 1-{month_end(2025, m).day}", DEVICE_FEE)]
        if m in DUP_MONTHS:
            lines.append((f"{DEVICE} rental, service {date(2025, m, 1):%b} 1-{month_end(2025, m).day}", DEVICE_FEE))
        if m == LATE_FEE_MONTH:
            lines.append(("Late payment fee (invoice INV-BF-2505)", LATE_FEE))
        total = sum(a for _, a in lines)
        paid = date(2025, m, 17)
        inv = dict(id=f"INV-BF-25{m:02d}", month=m, issued=date(2025, m, 5), due=date(2025, m, 20), lines=lines, total=total, paid=paid, payment_ref=f"PMT-BF-25{m:02d}")
        invoices.append(inv)
        checking.append((paid, f"BRIGHTLINE FIBER {PROVIDER['account']}", inv["payment_ref"], -total))

    electric = [11_842, 10_967, 9_418, 7_605, 6_932, 9_877, 12_416, 12_983, 9_104, 7_220, 8_391, 10_655]
    for m in range(1, 13):
        checking.append((date(2025, m, 1), "ACH WEXLEY PROPERTY MGMT RENT", f"RENT-25{m:02d}", -165_000))
        checking.append((date(2025, m, 9), "ACH NORTHGATE ELECTRIC", f"NGE-25{m:02d}", -electric[m - 1]))
        checking.append((date(2025, m, 12), "ACH KESTREL MOBILE", f"KM-25{m:02d}", -4_500))

    # card purchases
    shops = [("GREENLEAF MARKET", 4_800, 13_900), ("CITYLINE TRANSIT", 1_200, 3_600), ("ORCHARD STREET CAFE", 900, 3_400),
             ("HALVERSON PHARMACY", 1_100, 4_200), ("PAGEMARK BOOKS", 1_500, 4_500)]
    for m in range(1, 13):
        for k, (shop, lo, hi) in enumerate(shops[:3] if m % 2 else shops[:4]):
            card.append((date(2025, m, 3 + 6 * k), shop, f"CV{m:02d}{k}{rng.randint(100, 999)}", rng.randint(lo, hi)))
    for trip in (HARTFORD, TRIPS["boston"], TRIPS["albany"]):
        card.append((trip["bought"], f"NORTHEAST RAIL TICKETS {trip['ticket']}", trip["ticket"], trip["amount"]))
    card.append((date(2025, 8, 9), "COASTLINE FURNITURE", "CV08F512", 68_900))
    for p in PARKING:
        card.append((PARKING_DAY, f"METROPARK {p['place'].upper()}", p["ticket"], p["amount"]))
    card.append((TRANSFER["day"], "PAYMENT RECEIVED - THANK YOU", TRANSFER["ref"], -TRANSFER["amount"]))
    checking.append((TRANSFER["day"], f"ONLINE TRANSFER TO {CARD['name'].upper()} ...{CARD['last4']}", TRANSFER["ref"], -TRANSFER["amount"]))

    # card autopay on the 25th pays the previous statement's new balance in full
    card_open = 81_244
    card_statements, prev_balance = [], card_open
    for m in range(1, 13):
        pay = prev_balance
        if pay > 0:
            card.append((date(2025, m, 25), "AUTOPAY PAYMENT - THANK YOU", f"AP-25{m:02d}", -pay))
            checking.append((date(2025, m, 25), f"CORVID CARD AUTOPAY ...{CARD['last4']}", f"AP-25{m:02d}", -pay))
        rows = sorted([t for t in card if t[0].month == m], key=lambda t: (t[0], t[2]))
        new_balance = prev_balance + sum(t[3] for t in rows)
        card_statements.append(dict(month=m, opening=prev_balance, rows=rows, closing=new_balance))
        prev_balance = new_balance

    check_open = 481_237
    check_statements, bal = [], check_open
    for m in range(1, 13):
        rows = sorted([t for t in checking if t[0].month == m], key=lambda t: (t[0], t[2]))
        closing = bal + sum(t[3] for t in rows)
        check_statements.append(dict(month=m, opening=bal, rows=rows, closing=closing))
        bal = closing

    # balance checks
    assert all(s["closing"] == s["opening"] + sum(r[3] for r in s["rows"]) for s in check_statements + card_statements)
    assert min(s["closing"] for s in check_statements) > 0
    assert all(i["total"] == sum(a for _, a in i["lines"]) for i in invoices)
    dec = next(p for p in payslips if p["ref"] == DEC_DEPOSIT)
    assert dec["deposit"] == 218_600 and dec["net"] + TRIPS["boston"]["amount"] == dec["deposit"]
    lines = len(checking) + len(card)
    assert 100 <= lines <= 150, lines
    return dict(checking=check_statements, card=card_statements, payslips=payslips, invoices=invoices, posted_lines=lines)


# ---------------- documents ----------------
def statement_pdf(kind, s):
    name = BANK["name"] if kind == "checking" else CARD["name"]
    acct = BANK["account"] if kind == "checking" else CARD["account"]
    m = s["month"]
    lines = [f"Account holder: {SAM}", f"Account: {acct}", f"Statement period: 2025-{m:02d}-01 to {month_end(2025, m)}",
             f"{'Opening balance' if kind == 'checking' else 'Previous balance'}: {money(s['opening'])}", "",
             "Date        Description                                   Reference        Amount"]
    for d, desc, ref, amt in s["rows"]:
        lines.append(f"{d}  {desc:<44}  {ref:<15}  {money(amt)}")
    lines += ["", f"{'Closing balance' if kind == 'checking' else 'New balance'}: {money(s['closing'])}"]
    if kind == "card":
        lines.append(f"Payment due {date(2025, m + 1, 25) if m < 12 else date(2026, 1, 25)}: pay the new balance in full by autopay from {BANK['account']}.")
    return pdf_bytes(f"{name} statement {date(2025, m, 1):%B %Y}", lines)


def payslip_pdf(p):
    gross = 295_000
    deductions = gross - p["net"]
    lines = [f"Employer: {EMPLOYER['name']}", f"Employee: {SAM} ({EMPLOYER['employee_id']})", f"Pay statement: {p['id']}",
             f"Pay period ending: {p['period_end']}", f"Pay date: {p['pay_date']}", "",
             f"Gross pay: {money(gross)}", f"Taxes and deductions: {money(-deductions)}", f"Net pay: {money(p['net'])}"]
    if p["reimb"]:
        lines.append(f"Expense reimbursement (non-taxable): {money(p['reimb'])}")
        lines.append("Reimbursement detail: see the remittance advice for this deposit in your payroll records.")
    lines += [f"Direct deposit to {BANK['account']}: {money(p['deposit'])}", f"Deposit reference: {p['ref']}"]
    return pdf_bytes(f"{EMPLOYER['name']} pay statement {p['pay_date']}", lines)


def remittance_pdf(rid, deposit_ref, pay_date, trip, published):
    return pdf_bytes(f"{EMPLOYER['name']} remittance advice {rid}", [
        f"Employee: {SAM} ({EMPLOYER['employee_id']})", f"Remittance: {rid}", f"Deposit reference: {deposit_ref}", f"Deposit date: {pay_date}",
        f"Published to payroll records: {published}", "", "Expense reports reimbursed with this deposit:",
        f"  {trip['report']}  {trip['city']} trip {trip['travel']}  ticket {trip['ticket']}  {money(trip['amount'])}",
        f"Total reimbursed: {money(trip['amount'])}", "", "Reports not listed here have not been reimbursed with this deposit."])


def report_pdf(t):
    return pdf_bytes(f"{EMPLOYER['name']} expense report {t['report']}", [
        f"Employee: {SAM} ({EMPLOYER['employee_id']})", f"Report: {t['report']}", f"Purpose: client visit, {t['city']}", f"Travel date: {t['travel']}",
        f"Item: rail ticket {t['ticket']}, paid on personal {CARD['account']} on {t['bought']}: {money(t['amount'])}",
        f"Status: APPROVED on {t['approved']}", "Reimbursement: through payroll; approved reports are payable by December 31, 2025.",
        "Attached receipt: rail ticket receipt " + t["ticket"]])


def ticket_pdf(t):
    return pdf_bytes(f"Northeast Rail ticket receipt {t['ticket']}", [
        f"Passenger: {SAM}", f"Ticket: {t['ticket']}", f"Journey: New York to {t['city']} and return, {t['travel']}",
        f"Purchased: {t['bought']}", f"Paid: {money(t['amount'])} with Visa ending {CARD['last4']}"])


def parking_pdf(p):
    return pdf_bytes(f"MetroPark receipt {p['ticket']}", [
        f"Ticket: {p['ticket']}", f"Location: {p['place']}", f"Date: {PARKING_DAY}", f"Exit time: {p['time']}",
        f"Paid: {money(p['amount'])} with Visa ending {CARD['last4']}"])


def invoice_pdf(inv, credit=0, note=None):
    lines = [f"Customer: {SAM}", f"Account: {PROVIDER['account']}", f"Invoice: {inv['id']}", f"Issued: {inv['issued']}", f"Due: {inv['due']}", ""]
    lines += [f"  {desc:<52} {money(a)}" for desc, a in inv["lines"]]
    if credit:
        lines.append(f"  {'Account credit applied':<52} {money(-credit)}")
    lines += ["", f"Amount due: {money(inv['total'] - credit)}"]
    lines.append(f"Pay by the due date to avoid a late payment fee. Payments are made from {BANK['account']}.")
    if note:
        lines.append(note)
    return pdf_bytes(f"{PROVIDER['name']} invoice {inv['id']}", lines)


def agreement_pdf():
    return pdf_bytes(f"{PROVIDER['name']} service agreement {AGREEMENT_ID}", [
        f"Customer: {SAM}", f"Account: {PROVIDER['account']}", f"Agreement: {AGREEMENT_ID}, signed 2024-08-15", "",
        f"Service: Fiber 500 plan, {money(PLAN_FEE)} per month", f"Equipment: one {DEVICE}, {money(DEVICE_FEE)} per month",
        "Billing: one invoice per month on the 5th for that month's service; payment due on the 20th.",
        f"Late payment fee: {money(LATE_FEE)}, charged only if a bill is unpaid after its due date.",
        "Equipment changes require a signed order; no other equipment is on this account."])


def build_documents(ledger):
    shutil.rmtree(DOCS, ignore_errors=True)
    catalog = []

    def put(folder, fid, name, data, parent, available="pre_S1", fixture=None, role=None):
        disk = name if folder != "followups" else name.replace(".pdf", f"-{fixture or available}.pdf")
        path = os.path.join(DOCS, folder, disk)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        catalog.append(dict(file_id=fid, name=name, parent_id=parent, available=available, fixture=fixture,
                            role=role, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), disk_path=f"{folder}/{disk}"))

    for s in ledger["checking"]:
        put("common", f"file-chk-25{s['month']:02d}", f"checking-3318-2025-{s['month']:02d}.pdf", statement_pdf("checking", s), "folder-bank")
    for s in ledger["card"]:
        put("common", f"file-card-25{s['month']:02d}", f"card-9042-2025-{s['month']:02d}.pdf", statement_pdf("card", s), "folder-bank")
    for p in ledger["payslips"]:
        put("common", f"file-{p['id'].lower()}", f"payslip-{p['pay_date']}.pdf", payslip_pdf(p), "folder-payroll")
    put("common", "file-rm-2025-0430", "remittance-DEP-2025-0430-TF.pdf",
        remittance_pdf("RM-2025-0430", "DEP-2025-0430-TF", date(2025, 4, 30), HARTFORD, "2025-05-07"), "folder-payroll")
    for t in (HARTFORD, TRIPS["boston"], TRIPS["albany"]):
        put("common", f"file-{t['report'].lower()}", f"expense-report-{t['report']}.pdf", report_pdf(t), "folder-expenses")
        put("common", f"file-ticket-{t['ticket'].lower()}", f"receipt-rail-{t['ticket']}.pdf", ticket_pdf(t), "folder-receipts")
    for p in PARKING:
        put("common", f"file-parking-{p['ticket'].lower()}", f"receipt-parking-{p['ticket']}.pdf", parking_pdf(p), "folder-receipts")
    put("common", "file-agreement", f"service-agreement-{AGREEMENT_ID}.pdf", agreement_pdf(), "folder-internet")
    for inv in ledger["invoices"]:
        put("common", f"file-{inv['id'].lower()}", f"invoice-{inv['id']}.pdf", invoice_pdf(inv), "folder-internet")

    # the Dec 31 remittance, published on Jan 7 (S2); one per fixture
    for fx, trip in FIXTURES.items():
        put(f"fixture-{fx}", "file-rm-2025-1231", f"remittance-{DEC_DEPOSIT}.pdf",
            remittance_pdf(REMITTANCE, DEC_DEPOSIT, date(2025, 12, 31), TRIPS[trip], "2026-01-07"), "folder-payroll", available="S2", fixture=fx, role="remittance")

    # follow-ups a session boundary may release (chosen by rules.releases)
    for fx, paid in FIXTURES.items():
        unpaid = TRIPS["albany" if paid == "boston" else "boston"]
        put("followups", f"file-rm-2026-0115-{fx}", "remittance-DEP-2026-0115-TF.pdf",
            remittance_pdf("RM-2026-0115", "DEP-2026-0115-TF", date(2026, 1, 15), unpaid, "2026-01-15"), "folder-payroll",
            available="payroll_posted", fixture=fx, role="correction_remittance")
    jan = dict(id="INV-BF-2601", month=1, issued=date(2026, 1, 15), due=date(2026, 1, 20), paid=None,
               lines=[("Fiber 500 plan, service Jan 1-31", PLAN_FEE), (f"{DEVICE} rental, service Jan 1-31", DEVICE_FEE)])
    jan["total"] = PLAN_FEE + DEVICE_FEE
    put("followups", "file-inv-bf-2601", "invoice-INV-BF-2601.pdf", invoice_pdf(jan, credit=3 * DEVICE_FEE,
        note="Billing correction: duplicate equipment line removed from future invoices."), "folder-internet",
        available="provider_corrected", role="corrected_invoice")
    put("followups", "file-inv-bf-2601", "invoice-INV-BF-2601.pdf", invoice_pdf(jan, credit=3 * DEVICE_FEE + LATE_FEE,
        note="Billing correction: duplicate equipment line removed from future invoices; late fee reversed."), "folder-internet",
        available="provider_corrected_with_late_fee", role="corrected_invoice")
    dup = dict(jan, lines=jan["lines"] + [(f"{DEVICE} rental, service Jan 1-31", DEVICE_FEE)], total=PLAN_FEE + 2 * DEVICE_FEE)
    put("followups", "file-inv-bf-2601", "invoice-INV-BF-2601.pdf", invoice_pdf(dup), "folder-internet",
        available="provider_uncorrected", role="uncorrected_invoice")
    with open(os.path.join(DOCS, "catalog.json"), "w") as fh:
        json.dump(catalog, fh, indent=2)
        fh.write("\n")
    return catalog


# ---------------- hidden ledger ----------------
def build_gold(ledger, catalog):
    sha = {}
    for c in catalog:
        sha.setdefault(c["file_id"], {})[c["fixture"] or c["available"]] = c["sha256"]
    fixtures = {}
    for fx, paid in FIXTURES.items():
        unpaid = "albany" if paid == "boston" else "boston"
        fixtures[fx] = dict(paid_trip=paid, unpaid_trip=unpaid, paid_report=TRIPS[paid]["report"], unpaid_report=TRIPS[unpaid]["report"],
                            paid_ticket=TRIPS[paid]["ticket"], unpaid_ticket=TRIPS[unpaid]["ticket"],
                            unpaid_receipt_sha=next(c["sha256"] for c in catalog if c["file_id"] == f"file-ticket-{TRIPS[unpaid]['ticket'].lower()}"),
                            unpaid_report_sha=next(c["sha256"] for c in catalog if c["file_id"] == f"file-{TRIPS[unpaid]['report'].lower()}"),
                            remittance_sha=sha["file-rm-2025-1231"][fx])
    dup_invoices = [i["id"] for i in ledger["invoices"] if i["month"] in DUP_MONTHS]
    gold = {
        "task": "household-payment-audit", "currency": "USD", "audit_period": ["2025-01-01", "2025-12-31"], "posted_lines": ledger["posted_lines"],
        "addresses": ADDRESSES,
        "accounts": {"checking": BANK["last4"], "card": CARD["last4"], "provider": PROVIDER["account"], "employer": EMPLOYER["name"]},
        "ids": {"agreement": AGREEMENT_ID, "dec_deposit": DEC_DEPOSIT, "dec_payslip": ledger["payslips"][-1]["id"], "remittance": REMITTANCE,
                "transfer": TRANSFER["ref"], "parking": [p["ticket"] for p in PARKING], "reports": {k: v["report"] for k, v in TRIPS.items()},
                "tickets": {k: v["ticket"] for k, v in TRIPS.items()}, "late_fee_invoice": f"INV-BF-25{LATE_FEE_MONTH:02d}",
                "dup_invoices": dup_invoices, "all_invoices": [i["id"] for i in ledger["invoices"]], "next_invoice": "INV-BF-2601"},
        "fixtures": fixtures,
        # Obligation-level hidden ledger. Look-alikes have an explanation and no amount owed.
        "obligations": [
            {"id": "OB-TRIP-UNPAID", "kind": "pursue", "party": "payroll", "amount_cents": 18_600, "evidence": ["remittance", "expense report", "ticket receipt", "payslip", "deposit"]},
            {"id": "OB-DEVICE-DUP", "kind": "pursue", "party": "provider", "amount_cents": 3 * DEVICE_FEE, "charges": dup_invoices, "recurring": True,
             "evidence": ["agreement", "invoices", "bill payments"]},
            {"id": "OB-LATE-FEE", "kind": "report_only", "party": "provider", "amount_cents": LATE_FEE, "invoice": f"INV-BF-25{LATE_FEE_MONTH:02d}",
             "evidence": ["June invoice", "May bill paid 2025-05-17, due 2025-05-20"]},
            {"id": "LA-TRANSFER", "kind": "look_alike", "explanation": "one $600 card payment seen from both sides (same transfer reference)", "ref": TRANSFER["ref"]},
            {"id": "LA-PARKING", "kind": "look_alike", "explanation": "two genuine parking purchases (different tickets, places and times)", "tickets": [p["ticket"] for p in PARKING]},
        ],
        "year_end_cents": {"pursue": 18_600 + 3 * DEVICE_FEE, "report_only": LATE_FEE, "confirmed_errors": 18_600 + 3 * DEVICE_FEE + LATE_FEE},
        "amounts_cents": {"trip": 18_600, "device_fee": DEVICE_FEE, "device_total": 3 * DEVICE_FEE, "late_fee": LATE_FEE, "dec_deposit": 218_600,
                          "take_home": TAKE_HOME, "jan_invoice_corrected": PLAN_FEE + DEVICE_FEE - 3 * DEVICE_FEE},
        "documents": catalog,
    }
    assert gold["year_end_cents"] == {"pursue": 21_000, "report_only": 1_200, "confirmed_errors": 22_200}
    os.makedirs(os.path.dirname(GOLD), exist_ok=True)
    with open(GOLD, "w") as fh:
        json.dump(gold, fh, indent=2)
        fh.write("\n")


def main():
    ledger = build_ledger()
    catalog = build_documents(ledger)
    build_gold(ledger, catalog)
    print(f"{ledger['posted_lines']} posted lines; {len(catalog)} documents ({sum(c['bytes'] for c in catalog)} bytes); tests/gold.json")


if __name__ == "__main__":
    sys.exit(main())
