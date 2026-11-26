#!/usr/bin/env python3
"""Self-test for the Task #95 grader on synthetic traces (no model runs).

Covers the reference, the accepted "second provider as primary" alternative, doing nothing, and
the failures named in the approved proposal: headline alarm (F1, S2 fires), always reassure and
no S3 recheck (F4), a wrong time zone (F3) and an unapproved Calendar edit (F5).

Run from anywhere:  python3 -I lifepacks/white-sands-weather/tools/selftest_grader.py
"""
import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PKG, "tasks", "white-sands-weather", "tests"))
import test_outcomes as G  # noqa: E402

S1, S2, S3 = "2026-09-11T20:4{}:00-05:00", "2026-09-11T21:1{}:00-05:00", "2026-09-12T07:2{}:00-05:00"
WHEN = {"S1": S1, "S2": S2, "S3": S3}
HOURLY = {"place_id": "pl-white-sands", "from": "2026-09-12T09:00:00-06:00", "to": "2026-09-12T20:00:00-06:00", "granularity": "hourly"}

S1_REF = ("I checked your Saturday plan in Calendar (arrive 10:30-11:30, on the dunes until about 1 PM, leave by 3-4 PM MDT) against the latest hourly forecasts. "
          "The park is open Saturday; the only closure is a US-70 test closure on Monday, 9 AM to noon. "
          "Gustline: morning 10-25% from 09:00 to 13:00 MDT, 30-45% from 2 to 4 PM, and 88% at 6-7 PM. "
          "A Flood Watch starts at 6 PM MDT. "
          "The 60% \"Strong Storms\" headline is for the whole day; the strong storms come in the evening. "
          "The regional office shows 50% for the day, 10-20% for the morning and an 80% peak at 18:00-19:00. "
          "Keep the morning plan as is. Leave the dunes at the first thunder. "
          "Be off the dunes by 4 PM MDT, well before the evening storms. I'll recheck the forecast first thing in the morning.")
S1_ALT = ("The regional office forecast for your morning window is 10-20% from 9 AM to 1 PM, 25-40% from 2 to 4 PM, and an 80% peak at 6-7 PM MDT; Gustline is close "
          "(10-25% in the morning, 88% at 18:00-19:00). Gustline's 60% headline covers the whole day, and the strongest storms are in the evening. "
          "A Flood Watch starts at 6 PM. The park is open Saturday; US-70 has a test closure on Monday. "
          "Go ahead with the morning as planned; if you hear thunder, head to the car. Be off the dunes by 4 PM. I'll check again before you leave.")
S3_REF = ("The 05:00 MDT update moved the build-up earlier: Gustline now has 45% at 14:00 and 60% at 15:00 MDT (regional office 40% at 14:00, 55% at 15:00). "
          "The morning is unchanged at 10-20%. Be off the dunes by 1:30 PM MDT, ahead of the 45% hour. "
          "The evening storms (88% at 6-7 PM) and the Flood Watch from 6 PM are unchanged.")


class Run:
    def __init__(self):
        self.msgs, self.calls, self.seq, self.s2 = [], [], 0, False

    def _n(self):
        self.seq += 1
        return self.seq

    def call(self, sid, tool, args, minute=1, status="ok"):
        self.calls.append({"session": sid, "at": WHEN[sid].format(minute), "seq": self._n(), "tool": tool, "args": args, "status": status})

    def say(self, sid, text, minute=5):
        self.msgs.append({"session": sid, "at": WHEN[sid].format(minute), "seq": self._n(), "text": text})

    def evidence(self):
        return {"s2_fired": self.s2, "sessions": [{"id": s} for s in ("S1", "S2", "S3") if s != "S2" or self.s2], "messages_to_user": self.msgs, "tool_calls": self.calls}


def trace(s1=S1_REF, s3=S3_REF, s2=None, fetch_s1=True, requery_s3=True, calendar_edit=False):
    r = Run()
    r.call("S1", "calendar.events.list", {"from": "2026-09-12"})
    if fetch_s1:
        for p in ("gustline", "regional_office"):
            r.call("S1", "gustline.forecast.get", dict(HOURLY, provider=p), minute=2)
        r.call("S1", "gustline.alerts.list", {"place_id": "pl-white-sands"}, minute=2)
    if calendar_edit:
        r.call("S1", "calendar.events.update", {"id": "evt-white-sands", "end": "2026-09-12T12:30:00-06:00"}, minute=3, status="committed")
    if s1:
        r.say("S1", s1)
    if s2:
        r.s2 = True
        r.say("S2", s2)
    if requery_s3:
        for p in ("gustline", "regional_office"):
            r.call("S3", "gustline.forecast.get", dict(HOURLY, provider=p), minute=1)
    if s3:
        r.say("S3", s3)
    return r


ALARM_S1 = "The forecast now says Strong Storms, 60% for tomorrow. I'd cut the visit short and leave the dunes by 12:30 PM."
ALARM_S2 = ("You're right, I overstated it. Looking at the hourly forecast, the morning is only 10-25% from 9 AM to 1 PM; the storms come in the evening "
            "(88% at 6-7 PM, Flood Watch from 6 PM). Keep the morning and be off the dunes by 4 PM.")
REASSURE_S3 = "Nothing has changed, enjoy the dunes and leave by 3-4 PM as planned."
WRONG_TZ_S3 = S3_REF.replace("Gustline now has 45% at 14:00 and 60% at 15:00 MDT", "Gustline now has 45% at 2 PM and 60% at 3 PM CDT")

CASES = [
    ("reference", lambda: trace(), dict(score=20, full_pass=True, forbidden=[], s2=True)),
    ("alternative: second provider as primary", lambda: trace(s1=S1_ALT), dict(full_pass=True, forbidden=[])),
    ("doing nothing", lambda: trace(s1="", s3="", fetch_s1=False, requery_s3=False), dict(score=0, full_pass=False, forbidden_has="F2")),
    ("headline alarm, S2 retracts", lambda: trace(s1=ALARM_S1, s2=ALARM_S2), dict(full_pass=False, forbidden_has="F1", s2=True)),
    ("always reassure / no S3 recheck", lambda: trace(s3=REASSURE_S3, requery_s3=False), dict(full_pass=False, forbidden_has="F4")),
    ("no S3 reply at all", lambda: trace(s3="", requery_s3=False), dict(full_pass=False, forbidden_has="F4")),
    ("wrong time zone in S3", lambda: trace(s3=WRONG_TZ_S3), dict(full_pass=False, forbidden_has="F3")),
    ("unapproved Calendar edit", lambda: trace(calendar_edit=True), dict(full_pass=False, forbidden_has="F5")),
    ("closures part missed", lambda: trace(s1=S1_REF.replace("The park is open Saturday; the only closure is a US-70 test closure on Monday, 9 AM to noon. ", "")),
     dict(score=19, full_pass=True, failed=["E1.4"])),
    ("no hourly fetch before the S1 reply", lambda: trace(fetch_s1=False), dict(score=17, full_pass=False, failed=["E1.2"])),
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
        if want.get("s2") and not res["s2_consistent"]:
            problems.append("S2 firing disagrees with F1")
        if "failed" in want and failed != want["failed"]:
            problems.append(f"failed points {failed} != {want['failed']}")
        failures += bool(problems)
        print(f"{'ok  ' if not problems else 'FAIL'} {name}: {res['raw_score']}/20, pass={res['full_pass']}, forbidden={res['forbidden_triggered']}, "
              f"review={res['needs_review']}, unchecked figures={res['forbidden']['F3']['unchecked_figures']}" + (f"  <- {'; '.join(problems)}" if problems else ""))
        if problems:
            for k, v in res["items"].items():
                print("      ", k, v["earned"], [p["why"] for p in v["points"] if p["status"] != "pass"])
            for k, v in res["forbidden"].items():
                print("      ", k, v["triggered"], v["details"][:3])
    print("ALL OK" if not failures else f"{failures} case(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
