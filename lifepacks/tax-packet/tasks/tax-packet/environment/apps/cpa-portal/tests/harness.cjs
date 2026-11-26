'use strict';
// App-only transaction simulator. Real permissions, persistence and MCP are checked by the public verifier.
const assert = require('node:assert/strict');
const path = require('node:path');
const { compile } = require('./schema-validator.cjs');
const plugin = require('../plugin.cjs');
const app = require('../app.json').app_id;
const tools = require('../tools.json');
const root = path.resolve(__dirname, '..');
const seedValid = compile(require('../schemas/seed.schema.json'), path.join(root, 'schemas'));
const eventValid = compile(require('../schemas/events.schema.json'), path.join(root, 'schemas'));
const input = new Map(tools.map(t => [t.name, compile(t.inputSchema, root)]));
const output = new Map(tools.map(t => [t.name, compile(t.outputSchema, root)]));

function fixture({ seed = require('../fixtures/minimal.json'), now = require('../fixtures/clock.json').initial_time, logging = true } = {}) {
  let data = structuredClone(seed);
  const logs = [];
  const ctx = { app_id: app, role: 'agent', virtual_now: now, binding: structuredClone(require('../fixtures/binding.json')) };
  if (logging) ctx.log = (step, details = {}) => logs.push({ step, details: structuredClone(details) });
  const validate = value => { assert.ok(seedValid(value), 'Seed schema'); plugin.validateSeed(ctx, value); };
  validate(data);
  let seq = 0;
  return {
    ctx,
    get data() { return structuredClone(data); },
    get logs() { return structuredClone(logs); },
    at(time) { ctx.virtual_now = time; },
    call(name, args = {}) {
      const tool = tools.find(t => t.name === name);
      assert.ok(tool, 'Known tool: ' + name);
      const full = tool.read_only ? args : { expected_version: { epoch: 1, revision: seq }, request_id: 'local-' + (seq + 1), ...args };
      assert.ok(input.get(name)(full), 'Input schema: ' + name);
      const before = JSON.stringify(data);
      const out = plugin.handleTool(ctx, structuredClone(data), name, structuredClone(full));
      validate(out.data);
      if (tool.read_only) assert.equal(JSON.stringify(out.data), before, 'Read changed data: ' + name);
      else seq++;
      assert.ok(output.get(name)({ ...out.result, status: tool.read_only ? 'ok' : 'committed', app_id: app, version: { epoch: 1, revision: seq } }), 'Output schema: ' + name);
      data = out.data;
      return structuredClone(out.result);
    },
    event(event) {
      assert.ok(eventValid(event), 'Event schema');
      const out = plugin.applyEvent({ ...ctx, role: 'infra' }, structuredClone(data), structuredClone(event));
      validate(out);
      data = out;
      ctx.virtual_now = event.at;
      return structuredClone(data);
    }
  };
}
module.exports = { fixture };
