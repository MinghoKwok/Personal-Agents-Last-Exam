#!/usr/bin/env python3
"""Generate the weather content and release times for Task #95, in Gustline's seed and event format.

The task supplies only forecast content and release times (approved proposal, integration row);
Gustline (#126) defines their effect. Deterministic: no clock, no randomness.

Outputs (relative to the task directory):
  environment/workspace/gustline/seed.json     state at load (2026-09-11 16:00 CDT, after the 15:10 brief)
  environment/workspace/gustline/binding.json  people, account and place objects
  environment/workspace/gustline/events.json   {"virtual_now", "events"}: the 20:30 CDT raise and the 05:00 MDT issuances
  tests/gold.json   issuance log by provider and release time, itinerary window and rubric constants (verifier only)

Run:  python3 -I environment/build/make_forecasts.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

TASK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.path.join(TASK, "environment", "workspace", "gustline")
GOLD = os.path.join(TASK, "tests", "gold.json")

MDT, CDT = timezone(timedelta(hours=-6)), timezone(timedelta(hours=-5))
# The approved proposal names the real park; Gustline's own packs use fictional places only.
# Changing these two constants is the whole switch if Gustline's author asks for a fictional name.
PARK_NAME, PARK_ID = "White Sands National Park", "pl-white-sands"
ACCOUNT, PERSON = "gustline-kai", "person-kai"
LOAD_AT = datetime(2026, 9, 11, 16, 0, tzinfo=CDT)

# Rain probability (%) by local MDT hour on Saturday 2026-09-12, per issuance. Hours not listed
# are filled by the profile function. Values follow the approved proposal (Section 3).
P1_S1 = {9: 10, 10: 15, 11: 15, 12: 20, 13: 25, 14: 30, 15: 40, 16: 45, 17: 65, 18: 88, 19: 88, 20: 70, 21: 55, 22: 40, 23: 30}
P1_RAISED = {**P1_S1, 15: 41, 16: 44}                     # "the hourly forecast barely moves"
P2_S1 = {9: 10, 10: 10, 11: 15, 12: 15, 13: 20, 14: 25, 15: 35, 16: 40, 17: 60, 18: 80, 19: 80, 20: 65, 21: 50, 22: 35, 23: 25}
P1_0500 = {6: 5, 7: 5, 8: 8, 9: 10, 10: 10, 11: 15, 12: 15, 13: 20, 14: 45, 15: 60, 16: 70, 17: 80, 18: 88, 19: 88, 20: 70, 21: 55, 22: 40, 23: 30}
P2_0500 = {6: 5, 7: 5, 8: 5, 9: 10, 10: 10, 11: 10, 12: 15, 13: 15, 14: 40, 15: 55, 16: 65, 17: 72, 18: 80, 19: 80, 20: 65, 21: 50, 22: 35, 23: 25}

ISSUANCES = [  # (id, provider, issued_at MDT, release_at, sep12 profile, daily headline, daily %, outlook)
    ("fc-gl-0911-1400", "gustline", datetime(2026, 9, 11, 14, 0, tzinfo=MDT), None, P1_S1, "Scattered Storms", 50,
     "Storms Saturday afternoon, strongest in the evening; locally heavy rain."),
    ("fc-ro-0911-1300", "regional_office", datetime(2026, 9, 11, 13, 0, tzinfo=MDT), None, P2_S1, "Showers and Storms", 50,
     "Showers and thunderstorms Saturday afternoon and evening; heaviest after 6 PM."),
    ("fc-gl-0911-1930", "gustline", datetime(2026, 9, 11, 19, 30, tzinfo=MDT), datetime(2026, 9, 11, 19, 30, tzinfo=MDT), P1_RAISED, "Strong Storms", 60,
     "Strong to severe storms this evening Saturday; locally heavy rain and flash flooding possible."),
    ("fc-gl-0912-0500", "gustline", datetime(2026, 9, 12, 5, 0, tzinfo=MDT), datetime(2026, 9, 12, 5, 2, tzinfo=MDT), P1_0500, "Strong Storms", 60,
     "Strong to severe storms this evening Saturday; storms may begin by mid-afternoon."),
    ("fc-ro-0912-0500", "regional_office", datetime(2026, 9, 12, 5, 0, tzinfo=MDT), datetime(2026, 9, 12, 5, 4, tzinfo=MDT), P2_0500, "Showers and Storms", 50,
     "Thunderstorms developing early afternoon Saturday; heaviest after 6 PM."),
]
FLOOD_WATCH = {"alert_id": "fw-white-sands", "version": 1, "msg_type": "alert", "issued_at": "2026-09-11T13:30:00-06:00", "urgency": "expected",
               "certainty": "likely", "issuer": "Regional Weather Office", "event": "flood_watch", "severity": "moderate",
               "areas": {"zone_ids": ["z-white-sands"]}, "headline": "Flood Watch from Saturday 6 PM through midnight",
               "instruction": "Avoid washes and low areas; do not cross flooded roads.",
               "onset": "2026-09-12T18:00:00-06:00", "expires": "2026-09-13T00:00:00-06:00"}
US70 = {"alert_id": "cl-us70-test", "version": 1, "msg_type": "alert", "issued_at": "2026-09-10T09:00:00-06:00", "urgency": "future",
        "certainty": "observed", "issuer": "Park Service", "event": "area_closure", "severity": "minor",
        "areas": {"place_ids": [PARK_ID]}, "headline": "US-70 between Las Cruces and the park closed Monday 9 AM to noon for range testing",
        "instruction": "Plan for delays on Monday, September 14. The park is open as usual on Saturday and Sunday.",
        "onset": "2026-09-14T09:00:00-06:00", "expires": "2026-09-14T12:00:00-06:00"}


def iso(dt):
    return dt.isoformat()


def profile(hour, day, table):
    """Rain probability for one MDT hour: Saturday from the issuance's table, other hours a calm diurnal shape."""
    if day == 12 and hour in table:
        return table[hour]
    if day == 12:
        return 5 if hour < 9 else table.get(23, 25)
    if day == 11:
        return {16: 35, 17: 40, 18: 45, 19: 40, 20: 30, 21: 20, 22: 15, 23: 10}.get(hour, 10)
    return 10 if hour < 12 else 20


def hourly(start, hours, table):
    out = []
    for k in range(hours):
        t = start + timedelta(hours=k)
        p = profile(t.hour, t.day, table)
        warm = 1 - abs(t.hour - 15) / 12
        out.append({"start": iso(t), "temp_c": round(20 + 14 * max(warm, 0), 1), "feels_like_c": round(19.5 + 14 * max(warm, 0), 1),
                    "dew_point_c": 14.0 if p < 40 else 17.0, "precip_prob_pct": p, "precip_mm": 0 if p < 30 else round(p / 40, 1),
                    "thunder_prob_pct": round(p * (0.7 if p >= 30 else 0.3)), "wind_kph": 12.0 if p < 40 else 22.0, "gust_kph": 20.0 if p < 40 else 45.0,
                    "wind_dir_deg": 200, "cloud_pct": min(95, 20 + p), "visibility_km": 16, "uv_index": round(9 * max(warm, 0), 1) if 7 <= t.hour <= 18 else 0,
                    "humidity_pct": 30 if p < 40 else 55})
    return out


def issuance(row):
    iid, provider, issued, _, table, headline, daily_pct, outlook = row
    start = issued.replace(minute=0) + timedelta(hours=1)
    days = []
    for d in range(3):
        day = (issued + timedelta(days=d)).date()
        days.append({"date": day.isoformat(), "high_c": 34.0, "low_c": 19.0,
                     "precip_prob_pct": daily_pct if day.day == 12 else (40 if day.day == 11 else 20),
                     "headline": headline if day.day == 12 else ("Isolated Storms" if day.day == 11 else "Mostly Sunny")})
    return {"issuance_id": iid, "provider": provider, "zone_id": "z-white-sands", "issued_at": iso(issued), "valid_from": iso(start),
            "valid_to": iso(start + timedelta(hours=60)), "hourly": hourly(start, 60, table), "daily": days, "products": [{"kind": "outlook", "text": outlook}]}


def build():
    seeded = [issuance(r) for r in ISSUANCES if r[3] is None]
    seed = {
        "account_id": ACCOUNT, "owner_person_id": PERSON,
        "settings": {"units": "us", "time_zone": "America/Chicago", "default_saved_place_id": "sp-white-sands"},
        "zones": [{"zone_id": "z-white-sands", "name": "Tularosa Basin", "time_zone": "America/Denver"},
                  {"zone_id": "z-fort-stockton", "name": "Fort Stockton", "time_zone": "America/Chicago"}],
        "air_areas": [], "stations": [{"station_id": "st-white-sands", "name": "Park visitor center", "zone_id": "z-white-sands"}], "monitors": [],
        "places": [
            {"place_id": PARK_ID, "name": PARK_NAME, "kind": "park", "latitude": 32.78, "longitude": -106.17, "elevation_m": 1216, "time_zone": "America/Denver",
             "zone_id": "z-white-sands", "air_area_id": None, "station_id": "st-white-sands", "monitor_id": None, "external_ref": None},
            {"place_id": "pl-las-cruces", "name": "Las Cruces", "kind": "city", "latitude": 32.32, "longitude": -106.76, "elevation_m": 1191, "time_zone": "America/Denver",
             "zone_id": "z-white-sands", "air_area_id": None, "station_id": "st-white-sands", "monitor_id": None, "external_ref": None},
            {"place_id": "pl-fort-stockton", "name": "Fort Stockton", "kind": "city", "latitude": 30.89, "longitude": -102.88, "elevation_m": 920, "time_zone": "America/Chicago",
             "zone_id": "z-fort-stockton", "air_area_id": None, "station_id": None, "monitor_id": None, "external_ref": None}],
        "saved_places": [{"saved_place_id": "sp-white-sands", "place_id": PARK_ID, "label": "White Sands (Sat)", "created_at": "2026-09-09T19:00:00-05:00"}],
        "issuances": seeded, "air_issuances": [], "observations": [], "air_observations": [],
        "alerts": [{"alert_id": a["alert_id"], "versions": [{k: v for k, v in a.items() if k != "alert_id"}]} for a in (US70, FLOOD_WATCH)], "rules": [], "notifications": [],
    }
    events = [{"event_id": f"ev-{r[0]}", "at": iso(r[3]), "operation": "weather.forecast_issued", "payload": issuance(r)} for r in ISSUANCES if r[3] is not None]
    binding = {"people": [{"person_id": PERSON, "name": "Kai"}], "accounts": [{"app_id": "gustline", "account_id": ACCOUNT, "owner_person_id": PERSON}],
               "objects": {"gustline": [p["place_id"] for p in seed["places"]]}}
    os.makedirs(WS, exist_ok=True)
    for name, value in (("seed.json", seed), ("binding.json", binding), ("events.json", {"virtual_now": iso(LOAD_AT), "events": events})):
        with open(os.path.join(WS, name), "w") as fh:
            json.dump(value, fh, indent=1)
            fh.write("\n")

    # ---------------- gold: what each provider says about Saturday, and from when ----------------
    log = []
    for r in ISSUANCES:
        iid, provider, issued, release, table, headline, daily_pct, outlook = r
        hrs = {h: profile(h, 12, table) for h in range(24)}
        log.append({"issuance_id": iid, "provider": provider, "issued_at": iso(issued), "available_from": iso(release or issued),
                    "sep12_precip_by_mdt_hour": hrs, "sep12_thunder_by_mdt_hour": {h: round(p * (0.7 if p >= 30 else 0.3)) for h, p in hrs.items()},
                    "sep12_daily": {"headline": headline, "precip_prob_pct": daily_pct}, "outlook": outlook})

    def current(provider, at):
        c = [x for x in log if x["provider"] == provider and datetime.fromisoformat(x["available_from"]) <= at]
        return max(c, key=lambda x: x["issued_at"])

    s1, s3 = datetime(2026, 9, 11, 20, 45, tzinfo=CDT), datetime(2026, 9, 12, 7, 20, tzinfo=CDT)
    cur = {s: {p: current(p, t)["issuance_id"] for p in ("gustline", "regional_office")} for s, t in (("S1", s1), ("S3", s3))}
    first_at = lambda s, pct: min(h for p in cur[s].values() for x in log if x["issuance_id"] == p for h, v in x["sep12_precip_by_mdt_hour"].items() if v >= pct)
    gold = {
        "task": "white-sands-weather", "park": PARK_NAME, "park_id": PARK_ID, "timezone_offsets": {"MDT": -6, "CDT": -5},
        "sessions": {"S1": iso(s1), "S2": "2026-09-11T21:15:00-05:00", "S3": iso(s3)},
        "itinerary_mdt": {"arrive_from": 10.5, "arrive_to": 11.5, "dunes_until": 13.0, "leave_from": 15.0, "leave_to": 16.0},
        "issuances": log, "current": cur,
        "build_up_mdt_hour": {s: first_at(s, 45) for s in cur}, "first_60_mdt_hour": {s: first_at(s, 60) for s in cur},
        "alerts": {"flood_watch_onset_mdt_hour": 18, "us70_closure": "2026-09-14T09:00:00-06:00/2026-09-14T12:00:00-06:00"},
        "s1_exit_floor_mdt_hour": 13,
    }
    # checks against the approved proposal
    g = lambda iid: next(x for x in log if x["issuance_id"] == iid)["sep12_precip_by_mdt_hour"]
    assert all(10 <= g("fc-gl-0911-1930")[h] <= 25 for h in range(9, 14)) and all(30 <= g("fc-gl-0911-1930")[h] <= 45 for h in range(14, 17))
    assert g("fc-gl-0911-1930")[18] == g("fc-gl-0911-1930")[19] == 88 and g("fc-ro-0911-1300")[18] == 80
    assert all(10 <= g("fc-ro-0911-1300")[h] <= 20 for h in range(9, 14)) and all(25 <= g("fc-ro-0911-1300")[h] <= 40 for h in range(14, 17))
    assert g("fc-gl-0912-0500")[14] == 45 and g("fc-gl-0912-0500")[15] == 60 and g("fc-ro-0912-0500")[16] == 65
    assert cur["S1"] == {"gustline": "fc-gl-0911-1930", "regional_office": "fc-ro-0911-1300"}
    assert cur["S3"] == {"gustline": "fc-gl-0912-0500", "regional_office": "fc-ro-0912-0500"}
    assert gold["build_up_mdt_hour"]["S3"] == 14 and gold["first_60_mdt_hour"]["S3"] == 15
    os.makedirs(os.path.dirname(GOLD), exist_ok=True)
    with open(GOLD, "w") as fh:
        json.dump(gold, fh, indent=1)
        fh.write("\n")
    print(f"gustline: {len(seeded)} seeded issuances, {len(events)} events, 2 alerts; tests/gold.json")


if __name__ == "__main__":
    sys.exit(build())
