'use strict';
// This task-owned page accepts no incoming events in Task #102.
const { fail } = require('./util.cjs');
function applyEvent() { fail('invalid_event', 'The issuer document page accepts no events; documents appear by their available_from time.'); }
module.exports = { applyEvent };
