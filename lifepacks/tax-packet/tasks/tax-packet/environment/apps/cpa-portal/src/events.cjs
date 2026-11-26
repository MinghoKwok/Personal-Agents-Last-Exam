'use strict';
// This task-owned portal accepts no incoming events in Task #102.
const { fail } = require('./util.cjs');
function applyEvent() { fail('invalid_event', 'The CPA portal accepts no events in this task.'); }
module.exports = { applyEvent };
