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
