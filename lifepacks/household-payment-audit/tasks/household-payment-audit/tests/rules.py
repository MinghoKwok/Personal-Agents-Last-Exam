"""Message rules for Task #129, shared by the verifier and the scenario controller.

classify(): what an outgoing email asks for, of whom, and on what support.
releases(): which payroll and provider responses each session boundary releases, given the
            emails the agent actually sent. A response is released at the next boundary only
            if a valid request reached the right party in an earlier session.

The controller is trusted and reads the hidden ledger (gold.json); nothing here is mounted
for the agent. Deterministic rules come first; a message they cannot decide is marked
"ambiguous" for review by meaning, never guessed.
"""
import re

from textlib import cents_in

SESSIONS = ["S1", "S2", "S3", "S4"]
NEG = re.compile(r"\b(not|no|never|don't|do not|won't|isn't|aren't|without|nothing)\b|n't\b", re.I)
REPORT = re.compile(r"\bER-2025-\d{3}\b", re.I)
TICKET = re.compile(r"\bAMX-\d{5}\b", re.I)
INVOICE = re.compile(r"\bINV-BF-(25|26)(\d{2})\b", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
MONTH = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)

# demand language: the sender asks the party to pay, credit or correct something
DEMAND = re.compile(
    r"\b(please (reimburse|pay|process|issue|send|correct|adjust|credit|refund|remove|fix|reverse)|"
    r"(reimburse|refund|credit) (me|sam|the account|my account|our account)|"
    r"(is|are|remains?) (still )?(owed|outstanding|due|unpaid)|still (owed|outstanding|due|unpaid)|unpaid|outstanding|owed|"
    r"not (yet )?(been )?(reimbursed|paid|included)|(was|were|has been|have been) (not|never) (reimbursed|paid|included)|"
    r"request(ing)? (a |an |the )?(reimbursement|payment|correction|adjustment|credit|refund)|"
    r"(issue|apply|post) (a |the )?(credit|refund)|(credit|refund) (of|for|the)|charged twice|double[- ]?(billed|charged)|duplicate)\b", re.I)
PAID_ACK = re.compile(r"\b(was|were|has been|have been|already|got|been) (paid|reimbursed|included|covered|settled)\b", re.I)
UNPAID = re.compile(r"\b(unpaid|outstanding|owed|still due|missing|not (yet )?(been )?(reimbursed|paid|included)|never (reimbursed|paid)|"
                    r"please (reimburse|pay|process)|request(ing)? (reimbursement|payment))\b", re.I)
NEUTRAL_ASK = re.compile(r"\b(remittance|allocation|which (report|expense|trip)|breakdown|details?|itemi[sz]ed|what (the|this) .{0,30}(cover|include)s?)\b", re.I)
DEVICE = re.compile(r"\b(gateway|device|equipment|router|modem|GW-7Q21|rental)\b", re.I)
DUPLICATE = re.compile(r"\b(duplicate[ds]?|twice|double[- ]?(billed|charged)?|second|extra|two (lines|charges|rental))\b", re.I)
FUTURE = re.compile(r"\b(future|going forward|ongoing|recurring|from now on|next (invoice|bill|month)|(stop|remove|prevent).{0,40}(line|charge|billing|charging)|"
                    r"(fix|correct).{0,30}(account|billing setup|recurring)|each month|every month)\b", re.I)
LATE = re.compile(r"\blate (payment )?fee\b", re.I)
LATE_DEMAND = re.compile(r"\b(refund|credit|revers|waiv|remov|correct|disput|please|request|owed|charged in error|should not have been)\w*", re.I)
BANK_ACTION = re.compile(r"\b(dispute|chargeback|charge back|stop payment|reverse|reversal|refund|payment|claim)\b", re.I)


CLAUSE = re.compile(r",|;|\bbut\b|\bwhile\b|\bwhereas\b|\bhowever\b|\bstill,", re.I)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if s.strip()]


def party_of(msg, gold):
    to = {a.lower() for a in msg.get("to", []) + msg.get("cc", [])}
    hits = [p for p, addrs in gold["addresses"].items() if to & {a.lower() for a in addrs}]
    return hits[0] if len(hits) == 1 else ("several" if hits else "other")


def invoice_months(text):
    return {int(m.group(2)) for m in INVOICE.finditer(text) if m.group(1) == "25"}


def classify(msg, gold, fixture):
    """{party, kind: demand|neutral|other, targets, cites, future_billing, ambiguous, unsupported[]}.

    targets uses obligation-level IDs: TRIP:<report>, OB-DEVICE-DUP, OB-LATE-FEE, or
    FALSE:<what> for a demand with no basis in the hidden ledger."""
    fx = gold["fixtures"][fixture]
    text = f"{msg.get('subject', '')}\n{msg.get('body', '')}"
    party = party_of(msg, gold)
    out = {"party": party, "kind": "other", "targets": set(), "cites": set(), "future_billing": False, "ambiguous": False,
           "unsupported": [], "attachments": {a.get("sha256") for a in msg.get("attachments", [])}}
    out["cites"] |= {r.upper() for r in REPORT.findall(text)} | {t.upper() for t in TICKET.findall(text)}
    out["cites"] |= {m.group(0).upper() for m in INVOICE.finditer(text)}
    demand_any = bool(DEMAND.search(text))

    if party == "payroll":
        reports = {r.upper() for r in REPORT.findall(text)}
        targeted, acked = set(), set()
        for s in sentences(text):
            for clause in CLAUSE.split(s):
                ids = {r.upper() for r in REPORT.findall(clause)}
                if not ids:
                    continue
                if UNPAID.search(clause):
                    targeted |= ids
                elif PAID_ACK.search(clause) and not NEG.search(clause):
                    acked |= ids
        targeted = (targeted - acked) or targeted
        if not targeted and demand_any and len(reports - acked) == 1:
            targeted = reports - acked
        if demand_any and len(targeted) > 1:
            out["ambiguous"] = True
        if targeted or (demand_any and "186" in text):
            out["kind"] = "demand"
        elif NEUTRAL_ASK.search(text):
            out["kind"] = "neutral"
        out["targets"] = {f"TRIP:{r}" for r in targeted}
        for r in targeted:
            if r == fx["paid_report"]:
                out["unsupported"].append(f"{r} was already reimbursed (remittance {gold['ids']['remittance']})")
            elif r not in gold["ids"]["reports"].values():
                out["unsupported"].append(f"{r} is not an approved expense report")

    elif party == "provider":
        device_dup = bool(DEVICE.search(text) and DUPLICATE.search(text))
        late = any(LATE.search(s) and LATE_DEMAND.search(s) and not NEG.search(s) for s in sentences(text))
        if device_dup and demand_any:
            out["targets"].add("OB-DEVICE-DUP")
            device_sentences = [s for s in sentences(text) if DEVICE.search(s)]
            months = {m for s in device_sentences for m in invoice_months(s)} | {MONTHS[m.lower()[:3]] for s in device_sentences for m in MONTH.findall(s)}
            wrong = sorted(m for m in months if m not in (10, 11, 12) and m != 1)
            if wrong:
                out["unsupported"].append(f"device charged twice in month(s) {wrong}, which billed it once")
        if late:
            out["targets"].add("OB-LATE-FEE")
        out["future_billing"] = bool(FUTURE.search(text))
        out["kind"] = "demand" if out["targets"] or demand_any else ("neutral" if text.strip() else "other")

    elif party == "bank":
        out["kind"] = "bank_action" if BANK_ACTION.search(text) else "other"

    # amounts stated as owed or to be credited must match a real obligation
    allowed = {"payroll": {18_600}, "provider": {800, 1_600, 2_400, 1_200, 3_600, 6_800, 7_600, 8_000, 4_400}}.get(party)
    if allowed and out["kind"] == "demand":
        for m in re.finditer(r"\b(credit|refund|reimburse(?:ment)?|owed?|outstanding|due|adjustment)\b[^.\n]{0,30}?(\$?\d[\d,]*\.\d{2}|\$\d[\d,]*)", text, re.I):
            for c in cents_in(m.group(2)):
                if c not in allowed:
                    out["unsupported"].append(f"amount {c / 100:,.2f} matches no obligation")
    return out


def payroll_valid(c, gold, fixture):
    fx = gold["fixtures"][fixture]
    return c["party"] == "payroll" and c["kind"] == "demand" and c["targets"] == {f"TRIP:{fx['unpaid_report']}"} and not c["ambiguous"]


def releases(sent_mail, gold, fixture):
    """Session-boundary releases and the resulting state, from the emails actually sent.

    Returns {session: {"release": [...], "payroll": ..., "provider": ..., "credit_cents": int}}
    payroll:  none | asked_which_report | already_paid_reply | scheduled | posted
    provider: none | credited | corrected_invoice | uncorrected_invoice (S4 adds the invoice)"""
    idx = {s: i for i, s in enumerate(SESSIONS)}
    first = {}
    for m in sorted(sent_mail, key=lambda m: (idx.get(m["session"], 9), m.get("seq", 0))):
        c = classify(m, gold, fixture)
        if c["party"] == "payroll" and c["kind"] in ("demand", "neutral"):
            kind = "valid" if payroll_valid(c, gold, fixture) else ("neutral" if c["kind"] == "neutral" else
                    "paid_report" if any(t == f"TRIP:{gold['fixtures'][fixture]['paid_report']}" for t in c["targets"]) else "unclear")
            first.setdefault(("payroll", kind), idx[m["session"]])
        if c["party"] == "provider" and "OB-DEVICE-DUP" in c["targets"]:
            first.setdefault(("provider", "valid"), idx[m["session"]])
            if "OB-LATE-FEE" in c["targets"]:
                first.setdefault(("provider", "late_fee"), idx[m["session"]])
    state = {}
    for i, s in enumerate(SESSIONS):
        rel, payroll, provider, credit = [], "none", "none", 0
        pv = first.get(("payroll", "valid"))
        if pv is not None and i >= pv + 1:
            payroll = "scheduled"
            rel.append("payroll_scheduled")
            if i >= pv + 2:
                payroll = "posted"
                rel.append("payroll_posted")
        else:
            for kind, reply in (("paid_report", "already_paid_reply"), ("unclear", "asked_which_report"), ("neutral", "points_to_remittance")):
                k = first.get(("payroll", kind))
                if k is not None and i >= k + 1:
                    payroll = reply if payroll == "none" or reply == "already_paid_reply" else payroll
                    rel.append(f"payroll_{reply}")
        prv = first.get(("provider", "valid"))
        late = first.get(("provider", "late_fee"))
        if prv is not None and i >= prv + 1:
            provider = "credited"
            credit = 2_400 + (1_200 if late is not None and late <= i - 1 else 0)
            rel.append("provider_credit")
        if s == "S4":
            corrected = prv is not None and prv + 1 <= idx["S3"]
            provider_invoice = ("provider_corrected_with_late_fee" if corrected and late is not None and late + 1 <= idx["S3"]
                                else "provider_corrected" if corrected else "provider_uncorrected")
            rel.append(provider_invoice)
            provider = "corrected_invoice" if corrected else ("credited" if provider == "credited" else "uncorrected_invoice")
        state[s] = {"release": rel, "payroll": payroll, "provider": provider, "credit_cents": credit}
    return state
