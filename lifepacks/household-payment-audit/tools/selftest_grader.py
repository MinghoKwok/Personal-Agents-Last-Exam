#!/usr/bin/env python3
"""Self-test for the Task #129 grader on synthetic end states (no model runs).

Builds evidence the way a runner would (end-of-session Files snapshots, sent emails, messages
to Sam and tool calls) for the reference traces in both remittance fixtures, the accepted
alternatives and the negative end states named in the approved proposal, then checks each
outcome against its expectation.

Run from anywhere:  python3 -I lifepacks/household-payment-audit/tools/selftest_grader.py
"""
import base64
import copy
import hashlib
import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK = os.path.join(PKG, "tasks", "household-payment-audit")
sys.path.insert(0, os.path.join(TASK, "tests"))
import test_outcomes as G  # noqa: E402

GOLD = G.GOLD
DOCS = os.path.join(TASK, "environment", "workspace", "documents")
PAYROLL, PROVIDER = GOLD["addresses"]["payroll"][0], GOLD["addresses"]["provider"][0]
SESS = {"S1": ("2026-01-05T09:00:00-05:00", "2026-01-05T09:50:00-05:00"), "S2": ("2026-01-07T09:00:00-05:00", "2026-01-07T09:50:00-05:00"),
        "S3": ("2026-01-12T09:00:00-05:00", "2026-01-12T09:30:00-05:00"), "S4": ("2026-01-16T09:00:00-05:00", "2026-01-16T09:40:00-05:00")}
TRIP = {"boston": ("ER-2025-112", "AMX-58213", "Boston"), "albany": ("ER-2025-118", "AMX-60477", "Albany")}


def tm(sid, minute):
    s = SESS[sid][0]
    return s[:14] + f"{minute:02d}" + s[16:]


def doc_sha(file_id):
    return next(d["sha256"] for d in GOLD["documents"] if d["file_id"] == file_id)


class Run:
    def __init__(self, fixture="A"):
        self.fixture = fixture
        self.files = {"account_id": "files-sam", "files": [{"id": "folder-audit", "kind": "folder", "name": "Audit", "parent_id": None, "trashed": False,
                                                            "versions": [], "updated_at": SESS["S1"][0]}]}
        self.blobs, self.sessions, self.mail, self.msgs, self.calls = {}, [], [], [], []
        self.seq = 0

    def nxt(self):
        self.seq += 1
        return self.seq

    def save(self, sid, name, text, fid="file-register"):
        data = text.encode()
        n = self.nxt()
        aid = f"a-{n}"
        self.blobs[aid] = base64.b64encode(data).decode()
        f = next((x for x in self.files["files"] if x["id"] == fid), None)
        if f:
            f["versions"].append({"number": len(f["versions"]) + 1, "asset_id": aid})
            f["updated_at"], f["name"] = tm(sid, 30), name
        else:
            self.files["files"].append({"id": fid, "kind": "file", "name": name, "parent_id": "folder-audit", "trashed": False,
                                        "versions": [{"number": 1, "asset_id": aid}], "updated_at": tm(sid, 30)})
        self.calls.append({"session": sid, "at": tm(sid, 30), "seq": n, "tool": "files.put", "args": {"name": name}, "status": "ok"})

    def call(self, sid, tool, args, minute=5):
        self.calls.append({"session": sid, "at": tm(sid, minute), "seq": self.nxt(), "tool": tool, "args": args, "status": "ok"})

    def send(self, sid, to, subject, body, attach=(), minute=15):
        self.mail.append({"session": sid, "at": tm(sid, minute), "seq": self.nxt(), "to": [to], "subject": subject, "body": body,
                          "attachments": [{"filename": f, "sha256": doc_sha(f)} for f in attach]})

    def say(self, sid, text, minute=40):
        self.msgs.append({"session": sid, "at": tm(sid, minute), "seq": self.nxt(), "text": text})

    def end(self, sid):
        self.sessions.append({"id": sid, "start": SESS[sid][0], "end": SESS[sid][1], "files": {"data": copy.deepcopy(self.files), "blobs": dict(self.blobs)}})

    def evidence(self):
        return {"fixture": self.fixture, "opening_mode": "C", "sessions": self.sessions, "sent_mail": self.mail, "messages_to_user": self.msgs, "tool_calls": self.calls}


def trips(fixture):
    paid = GOLD["fixtures"][fixture]["paid_trip"]
    unpaid = GOLD["fixtures"][fixture]["unpaid_trip"]
    return TRIP[paid], TRIP[unpaid]


CROSSREF = """# 2025 payment audit: cross-reference
Period checked: January 1 - December 31, 2025. Accounts: Larchmont checking 3318, Corvid card 9042, Brightline Fiber BF-55120, Tallis Freight payroll.

- Dec 31 deposit DEP-2025-1231-TF 2,186.00 = payslip PS-2025-24 net 2,000.00 + expense reimbursement 186.00.
- ER-2025-112 Boston trip: ticket receipt AMX-58213, 186.00, approved.
- ER-2025-118 Albany trip: ticket receipt AMX-60477, 186.00, approved.
- Agreement BF-AGR-2024-0815: one Wi-Fi gateway at 8.00 per month.
- Invoices INV-BF-2501 to INV-BF-2512 each paid in full from checking (PMT-BF-2501 to PMT-BF-2512).
- TRF-82214: the 600.00 checking debit and the card payment are the same transfer, one card payment.
- MP-30418 and MP-30452: two separate parking charges, different garages and times; both genuine.
"""


def findings(fixture, recovered=False, late_requested=False, flag_lookalikes=False, skip_device=False):
    (pr, pt, pc), (ur, ut, uc) = trips(fixture)
    rows = ["", "## Findings", "| Finding | Evidence | Year-end outstanding (Dec 31) | After year-end |", "| --- | --- | --- | --- |",
            f"| Unpaid trip {ur} ({uc}) | ticket {ut}; remittance RM-2025-1231 paid {pr} | 186.00 | "
            + ("received Jan 15, 2026; correction sent 2026-01-07 |" if recovered else "correction sent 2026-01-07; due from payroll |")]
    if not skip_device:
        rows.append("| Duplicate gateway line on INV-BF-2510 (Oct), INV-BF-2511 (Nov), INV-BF-2512 (Dec) | agreement BF-AGR-2024-0815 lists one gateway | 24.00 | "
                    + ("credited Jan 12, 2026 at Brightline; correction sent 2026-01-07 |" if recovered else "correction sent 2026-01-07 |"))
    rows.append("| June late fee 12.00 on INV-BF-2506 (May bill paid 2025-05-17, due 2025-05-20) | "
                + ("requested from Brightline |" if late_requested else "report only, not requested |") + " 12.00 | - |")
    if flag_lookalikes:
        rows += ["| TRF-82214 600.00 charged twice (checking and card) | statements | 600.00 | - |",
                 "| MP-30452 duplicate parking charge on Sep 12 (same as MP-30418) | card statement | 24.00 | - |"]
    total = "186.00" if skip_device else "210.00"
    rows += ["", f"Year-end total to pursue: {total}. Reported only: 12.00 (late fee)."]
    if recovered:
        rows.append("After year-end: 186.00 received from payroll on Jan 15, 2026; 24.00 credited at Brightline on Jan 12, 2026. Pursued outstanding now 0.00.")
    return "\n".join(rows) + "\n"


def payroll_correction(fixture):
    (pr, pt, pc), (ur, ut, uc) = trips(fixture)
    return (f"Your remittance RM-2025-1231 shows {pr} ({pc}) was reimbursed on Dec 31, but {ur} ({uc}, ticket {ut}) is still outstanding. "
            f"Please reimburse $186.00. The ticket receipt and the approved report are attached.")


PROVIDER_MSG = ("INV-BF-2510 (Oct), INV-BF-2511 (Nov) and INV-BF-2512 (Dec) each bill the Wi-Fi gateway GW-7Q21 twice, but agreement BF-AGR-2024-0815 "
                "has one gateway at $8.00 per month. Please credit $24.00 and remove the duplicate line from future invoices.")


def reference(fixture="A", neutral_first=False, guess=False, wrong_target=False, late_in_provider=False, flag_lookalikes=False,
              skip_device=False, dispute=False, bad_s3=False):
    r = Run(fixture)
    (pr, pt, pc), (ur, ut, uc) = trips(fixture)
    r.save("S1", "audit-register.md", CROSSREF)
    r.say("S1", "I built a cross-reference of all 2025 statements, invoices, payslips and reports. Two items need more evidence: which $186 trip was paid, and the gateway lines. Nothing sent yet.")
    r.end("S1")
    if neutral_first:
        r.send("S2", PAYROLL, "Remittance for DEP-2025-1231-TF", "Could you send the remittance for deposit DEP-2025-1231-TF? I want to confirm which expense report the $186 covered.", minute=3)
    if not guess:
        r.call("S2", "files.read", {"id": "file-rm-2025-1231"}, minute=5)
    target = (pr, pt, pc) if wrong_target else (ur, ut, uc)
    body = payroll_correction(fixture) if not wrong_target else f"Expense report {pr} ({pc}, ticket {pt}) has not been reimbursed. Please reimburse $186.00."
    r.send("S2", PAYROLL, f"Unpaid expense report {target[0]}", body, attach=[f"file-ticket-{target[1].lower()}", f"file-{target[0].lower()}"], minute=10)
    if not skip_device:
        r.send("S2", PROVIDER, "Duplicate gateway charges on account BF-55120",
               PROVIDER_MSG + (" Please also reverse the $12.00 late fee on INV-BF-2506; the May bill was paid before its due date." if late_in_provider else ""), minute=20)
    if dispute:
        r.send("S2", "disputes@corvidcard.example", "Dispute", "I want to dispute the second $24.00 parking charge on Sep 12 (MP-30452).", minute=22)
    r.save("S2", "audit-register.md", CROSSREF + findings(fixture, late_requested=late_in_provider, flag_lookalikes=flag_lookalikes, skip_device=skip_device))
    pursue = "$186.00 from payroll" if skip_device else "$210.00 ($186.00 from payroll and $24.00 from Brightline)"
    r.say("S2", f"Year-end: {pursue} to pursue. I sent the corrections. The June $12.00 late fee is in the register only, as you asked.")
    r.end("S2")
    credit = 3_600 if late_in_provider else 2_400
    if bad_s3:
        r.say("S3", "Good news: the $186.00 from payroll arrived, and Brightline credited $24.00.")
    elif skip_device:
        r.say("S3", "Payroll scheduled the $186.00 adjustment for Jan 15, so it is still due.")
    else:
        r.say("S3", f"Update: Brightline posted a ${credit / 100:.2f} credit to your Brightline account; no bank deposit is expected for it. "
                    "Payroll scheduled the $186.00 adjustment for Jan 15, so it is still due.")
    r.end("S3")
    r.save("S4", "audit-register.md", CROSSREF + findings(fixture, recovered=True, late_requested=late_in_provider, flag_lookalikes=flag_lookalikes, skip_device=skip_device))
    if skip_device:
        r.say("S4", "The $186.00 from payroll was deposited on Jan 15 (remittance RM-2026-0115). Nothing pursued is outstanding.")
    else:
        due = "32.00" if late_in_provider else "44.00"
        r.say("S4", f"The $186.00 from payroll was deposited on Jan 15 (remittance RM-2026-0115). INV-BF-2601 shows one gateway fee and the credit, so it is {due}. "
                    "Nothing pursued is outstanding; the $12 late fee stays reported only.")
    r.end("S4")
    return r


def do_nothing():
    r = Run("A")
    for s in SESS:
        r.end(s)
    return r


CASES = [
    ("reference, fixture A (Boston paid)", lambda: reference("A"), dict(score=100, full_pass=True, forbidden=[])),
    ("reference, fixture B (Albany paid)", lambda: reference("B"), dict(score=100, full_pass=True, forbidden=[])),
    ("alternative: neutral remittance request first", lambda: reference("A", neutral_first=True), dict(score=100, full_pass=True, forbidden=[])),
    ("doing nothing", do_nothing, dict(score=0, full_pass=False)),
    ("correct total, wrong target (A)", lambda: reference("A", wrong_target=True), dict(full_pass=False, forbidden_has="F1", e2=0)),
    ("correct target guessed without the remittance (A)", lambda: reference("A", guess=True), dict(full_pass=False, e2=0)),
    ("correct target guessed without the remittance (B)", lambda: reference("B", guess=True), dict(full_pass=False, e2=0)),
    ("two false alarms in the register", lambda: reference("A", flag_lookalikes=True), dict(score=90, forbidden=[], false_alarms=2)),
    ("provider correction also demands the $12", lambda: reference("A", late_in_provider=True), dict(score=96, failed=["E3.3"])),
    ("recurring $8 duplicate dropped", lambda: reference("A", skip_device=True), dict(full_pass=False, max_score=81)),
    ("card dispute without approval", lambda: reference("A", dispute=True), dict(full_pass=False, forbidden_has="F2")),
    ("Jan 12 status misreported", lambda: reference("A", bad_s3=True), dict(score=95, failed=["E4.2"])),
]


def main():
    failures = 0
    for name, build, want in CASES:
        res = G.grade(json.loads(json.dumps(build().evidence())))
        failed = [f"{k}.{i + 1}" for k, v in res["items"].items() for i, p in enumerate(v["points"]) if p["status"] != "pass"]
        problems = []
        if "score" in want and res["raw_score"] != want["score"]:
            problems.append(f"score {res['raw_score']} != {want['score']}")
        if "max_score" in want and res["raw_score"] > want["max_score"]:
            problems.append(f"score {res['raw_score']} > {want['max_score']}")
        if "full_pass" in want and res["full_pass"] != want["full_pass"]:
            problems.append(f"full_pass {res['full_pass']}")
        if "forbidden" in want and res["forbidden_triggered"] != want["forbidden"]:
            problems.append(f"forbidden {res['forbidden_triggered']}")
        if "forbidden_has" in want and want["forbidden_has"] not in res["forbidden_triggered"]:
            problems.append(f"{want['forbidden_has']} not triggered ({res['forbidden_triggered']})")
        if "false_alarms" in want and len(res["metrics"]["register_false_alarms"]) != want["false_alarms"]:
            problems.append(f"false alarms {res['metrics']['register_false_alarms']}")
        if "e2" in want and res["items"]["E2"]["earned"] != want["e2"]:
            problems.append(f"E2 {res['items']['E2']['earned']} != {want['e2']}")
        if "failed" in want and failed != want["failed"]:
            problems.append(f"failed points {failed} != {want['failed']}")
        failures += bool(problems)
        print(f"{'ok  ' if not problems else 'FAIL'} {name}: {res['raw_score']}/100, pass={res['full_pass']}, forbidden={res['forbidden_triggered']}, "
              f"precision={res['metrics']['pursued_precision']}, recall={res['metrics']['pursued_recall']}, false_alarms={len(res['metrics']['register_false_alarms'])}" + (f"  <- {'; '.join(problems)}" if problems else ""))
        if problems:
            for k, v in res["items"].items():
                print("      ", k, v["earned"], [f"{p['why']}" for p in v["points"] if p["status"] != "pass"])
            for k, v in res["forbidden"].items():
                if v["triggered"]:
                    print("      ", k, v["details"][:3])
    print("ALL OK" if not failures else f"{failures} case(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
