'use strict';
// App-owned helpers. No persistence, authentication or platform runtime.
function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}
const copy = value => structuredClone(value);
const ms = value => Date.parse(value);
function unique(list, key, what) {
  const seen = new Set();
  for (const item of list) {
    if (seen.has(item[key])) fail('invalid_seed', `Duplicate ${what} ID: ${item[key]}.`);
    seen.add(item[key]);
  }
}
function byId(list, key, value, what) {
  const item = list.find(x => x[key] === value);
  if (!item) fail('not_found', `${what} ${value} does not exist.`);
  return item;
}
function nextId(prefix, taken) {
  let n = 1;
  while (taken.has(`${prefix}-${String(n).padStart(4, '0')}`)) n++;
  return `${prefix}-${String(n).padStart(4, '0')}`;
}
module.exports = { fail, copy, ms, unique, byId, nextId };

// Add hours to an RFC 3339 time and render it in the same UTC offset.
function addHours(iso, hours) {
  const m = /([+-])(\d{2}):(\d{2})$/.exec(iso);
  const offsetMin = m ? (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3])) : 0;
  const local = new Date(Date.parse(iso) + hours * 3600e3 + offsetMin * 60e3).toISOString().slice(0, 19);
  return local + (m ? m[0] : 'Z');
}
const addDays = (iso, days) => addHours(iso, days * 24);
const money = v => `${(v.amount_minor / 100).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}${v.currency === 'USD' ? '' : ' ' + v.currency}`;
const list = names => names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`;
// A confirmation token: deterministic for the same state, so replays and tests are reproducible.
const token = (...parts) => 'cf-' + require('node:crypto').createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 16);
Object.assign(module.exports, { addHours, addDays, money, list, token });
