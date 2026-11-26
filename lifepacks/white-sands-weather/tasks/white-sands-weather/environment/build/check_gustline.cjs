#!/usr/bin/env node
// Load the Task #95 weather pack into Gustline (#126) with Gustline's own App harness, replay the
// events at their release times, and read back what the agent would see at S1 and S3 through the
// Agent tools (gustline.forecast.get, gustline.alerts.list). Every figure the rubric depends on is
// compared with tests/gold.json.
//
// Usage: node environment/build/check_gustline.cjs [path/to/apps/gustline]
//        (default: apps/gustline in this checkout, once Gustline is merged)
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const task = path.resolve(__dirname, '../..');
const repo = path.resolve(task, '../../../..');
const gustline = path.resolve(process.argv[2] || path.join(repo, 'apps/gustline'));
const {fixture} = require(path.join(gustline, 'tests/harness.cjs'));
const ws = path.join(task, 'environment/workspace/gustline');
const seed = require(path.join(ws, 'seed.json')), binding = require(path.join(ws, 'binding.json'));
const {virtual_now, events} = structuredClone(require(path.join(ws, 'events.json')));
const gold = require(path.join(task, 'tests/gold.json'));
const f = fixture({seed, now: virtual_now, binding});
const park = gold.park_id;

function moveTo(at) {
  for (const e of events.filter(e => !e.done && Date.parse(e.at) <= Date.parse(at))) {
    if (Date.parse(e.at) > Date.parse(f.now)) f.event(e); else throw new Error('event before clock');
    e.done = true;
  }
  if (Date.parse(at) > Date.parse(f.now)) f.advance(at);
}

let checks = 0;
// The 05:00 MDT issuances start at 06:00; an earlier window is outside their horizon (as for the agent).
for (const [session, at, from] of [['S1', gold.sessions.S1, '2026-09-12T00:00:00-06:00'], ['S3', gold.sessions.S3, '2026-09-12T06:00:00-06:00']]) {
  moveTo(at);
  const range = {from, to: '2026-09-13T00:00:00-06:00'};
  for (const provider of ['gustline', 'regional_office']) {
    const out = f.call('gustline.forecast.get', {place_id: park, ...range, granularity: 'hourly', provider});
    const daily = f.call('gustline.forecast.get', {place_id: park, ...range, granularity: 'daily', provider});
    if (!checks) console.log('forecast.get keys:', Object.keys(out).join(', '));
    const want = gold.issuances.find(i => i.issuance_id === gold.current[session][provider]);
    assert.equal(out.issuance_id, want.issuance_id, `${session} ${provider}: current issuance`);
    const periods = out.periods.filter(p => String(p.start).startsWith('2026-09-12'));   // `to` is inclusive
    assert.ok(Array.isArray(periods) && periods.length >= 17, `${session} ${provider}: hourly periods returned`);
    for (const p of periods) {
      assert.ok(String(p.start).endsWith('-06:00'), `rendered in park time (MDT): ${p.start}`);
      const hour = Number(String(p.start).slice(11, 13));
      assert.equal(p.precip_prob_pct, want.sep12_precip_by_mdt_hour[hour], `${session} ${provider} ${hour}:00 precip`);
      assert.equal(p.thunder_prob_pct, want.sep12_thunder_by_mdt_hour[hour], `${session} ${provider} ${hour}:00 thunder`);
      checks += 2;
    }
    const d = daily.periods[0];
    assert.equal(d.headline, want.sep12_daily.headline);
    assert.equal(d.precip_prob_pct, want.sep12_daily.precip_prob_pct);
    checks += 2;
    const h = want.sep12_precip_by_mdt_hour;
    console.log(`${session} ${provider.padEnd(15)} ${out.issuance_id}  09-13 ${[9, 10, 11, 12, 13].map(x => h[x]).join('/')}  14-16 ${[14, 15, 16].map(x => h[x]).join('/')}`
      + `  18-19 ${h[18]}/${h[19]}  daily "${d.headline}" ${d.precip_prob_pct}%`);
  }
  const alerts = f.call('gustline.alerts.list', {place_id: park}).alerts.map(a => `${a.version.event}:${a.status}`);
  assert.ok(alerts.some(a => a.startsWith('flood_watch')) && alerts.some(a => a.startsWith('area_closure')), `${session}: alerts ${alerts}`);
  console.log(`${session} alerts: ${alerts.join(', ')}`);
  checks++;
}
console.log(`OK: ${checks} checks against tests/gold.json through Gustline's Agent tools`);
