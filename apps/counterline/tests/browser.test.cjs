'use strict';
// Browser acceptance for Counterline's web pages through the shared Web Host (needs the full checkout,
// `npm ci` and Chromium: `npx playwright install chromium`). From the repository root:
//   node apps/counterline/tests/browser.test.cjs
// Real clicks and form entry; every write is checked in the App state through a separate Infra MCP
// connection. Screenshots and a JSON report go to .artifacts/web/counterline/ (PALE_WEB_REPORT_DIR overrides).
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const pkg = path.resolve(__dirname, '..');
let root = pkg; while (!fs.existsSync(path.join(root, 'runtime/web/server.cjs'))) { const up = path.dirname(root); if (up === root) { console.log('SKIP: no PALE checkout'); process.exit(0); } root = up; }
let chromium;
try { ({chromium} = require(require.resolve('playwright', {paths: [root]}))); } catch { try { ({chromium} = require('playwright')); } catch { console.log('SKIP: run `npm ci` and `npx playwright install chromium` first'); process.exit(0); } }
const {start} = require(path.join(root, 'runtime/web/server.cjs')), {Client} = require(path.join(root, 'runtime/client.cjs'));
const out = path.resolve(process.env.PALE_WEB_REPORT_DIR || path.join(root, '.artifacts/web/counterline'));

async function main() {
  fs.mkdirSync(out, {recursive: true});
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'counterline-browser-')), checks = [];
  const record = (name, condition = true) => { assert.ok(condition, name); checks.push(name); };
  const browser = await chromium.launch({headless: true});
  let host, infra, step = 0;
  try {
    host = await start({app: 'counterline', registry: path.join(pkg, 'registry.json'), stateDir, run: 'browser-counterline'});
    infra = new Client('counterline', 'infra', host.run, stateDir, 'counterline-web-inspector', {registry: host.registry}); await infra.initialize();
    const snap = async () => (await infra.call('env.snapshot')).snapshot;
    const data = async () => (await snap()).data;
    const context = await browser.newContext({viewport: {width: 1280, height: 900}}), page = await context.newPage();
    page.setDefaultTimeout(8000);
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const idle = () => page.locator('#app[aria-busy=false]').waitFor();
    const shot = name => page.screenshot({path: path.join(out, `${String(++step).padStart(2, '0')}-${name}.png`), fullPage: true});
    const status = () => page.locator('#status').textContent();

    // Page, discovery and coverage.
    await page.goto(host.accessUrl); await page.waitForSelector('#status:has-text("Ready")');
    record('Public Host loads the App-owned page with the provider name', await page.locator('.sidebar-foot').getByText('Larchmont Card Services').count() === 1);
    record('Business discovery has no management tools', (await host.client.request('tools/list')).result.tools.every(t => !t.name.startsWith('env.')));
    const controller = fs.readFileSync(path.join(pkg, 'gui/src/app.js'), 'utf8');
    const tools = require('../tools.json'), short = t => t.name.replace(/^counterline\./, '');
    record('Controller uses every write tool', tools.filter(t => !t.read_only).every(t => controller.includes(`'${short(t)}'`)));
    const unusedReads = tools.filter(t => t.read_only && !controller.includes(`'${t.name}'`) && !controller.includes(`'${short(t)}'`)).map(t => t.name);
    await shot('cases');

    // Open a case.
    await page.selectOption('select[aria-label=Topic]', 'annual_fee');
    await page.fill('textarea[aria-label="First message"]', 'My annual fee posted. Can you help?');
    await page.click('button:has-text("Open case")'); await idle();
    let d = await data();
    const c = d.cases.at(-1);
    record('New case is in the App with the message and the greeting', c.topic_id === 'annual_fee' && c.transcript[0].text === 'My annual fee posted. Can you help?' && c.transcript.length === 2);
    record('No offer before identity on an identity topic', !d.offers.some(o => o.case_id === c.case_id));

    // Identity: only the ticked fields are sent; values never reach the transcript.
    await page.check('input[data-field=last_four]'); await page.fill('input[aria-label="Last four digits"]', '1234');
    await page.check('input[data-field=billing_zip]'); await page.fill('input[aria-label="Billing ZIP code"]', '02139');
    await page.fill('input[aria-label="Social Security number"]', '000-12-3456');   // typed but not ticked
    await page.click('button:has-text("Send selected")'); await idle();
    d = await data();
    const kase = () => d.cases.find(x => x.case_id === c.case_id);
    record('Identity sends only the ticked fields', JSON.stringify(kase().identity.disclosures.at(-1).fields) === '["last_four","billing_zip"]' && kase().identity.verified);
    record('Identity values are not stored in the transcript', !JSON.stringify(kase().transcript).includes('02139') && !JSON.stringify(d).includes('000-12-3456'));
    record('The first offer is presented after verification', d.offers.filter(o => o.case_id === c.case_id).length === 1);
    await shot('verified');

    // Two requests in one message, then a message that tries to accept by text. The first send loses its response.
    let dropped = false;
    await page.route('**/api/call', async route => {
      const body = route.request().postDataJSON();
      if (!dropped && body.name === 'counterline.cases.send_message') { dropped = true; await route.fetch(); await route.abort('failed'); } else await route.continue();
    });
    await page.fill('textarea[aria-label=Message]', 'Thanks. Can you explain the terms, and is there anything better?');
    await page.click('button:has-text("Send")'); await idle();
    await page.click('button:has-text("Send")'); await idle();
    await page.unroute('**/api/call');
    d = await data();
    const customerTurns = kase().transcript.filter(t => t.speaker === 'customer' && t.text.startsWith('Thanks. Can you explain'));
    record('Retry after a lost committed response has one effect', customerTurns.length === 1);
    const rules = kase().transcript.filter(t => t.speaker === 'representative').map(t => t.rule);
    record('Two requests are answered in the order written', rules.indexOf('explain_terms:offers') < rules.indexOf('ask_for_better_offer:presented') && rules.includes('ask_for_better_offer:presented'));
    const before = d.commitments.length;
    await page.fill('textarea[aria-label=Message]', "Yes, I'll take the 300.");
    await page.click('button:has-text("Send")'); await idle();
    record('A chat message never accepts an offer', (await data()).commitments.length === before);
    await shot('chat');

    // Text is rendered as text.
    await page.fill('textarea[aria-label=Message]', '<img src=x onerror="window.injected=true">hello');
    await page.click('button:has-text("Send")'); await idle();
    record('App text is rendered as text, not HTML', await page.evaluate(() => window.injected === undefined) && await page.locator('.turn', {hasText: '<img src=x'}).count() === 1);

    // Transfer through the quick action dialog.
    await page.click('button[data-action=request_transfer]');
    await page.fill('dialog input[aria-label=Department]', 'retention'); await page.click('dialog button:has-text("Request")'); await idle();
    d = await data();
    record('Transfer by alias moves the case to the specialist tier', kase().tier === 'specialist' && kase().status === 'escalated');
    await shot('transfer');

    // Two-step acceptance: step one changes no offer; cancel leaves no commitment; confirm creates one.
    const waiver = page.locator('.offer', {hasText: 'Annual fee waiver'});
    await waiver.locator('button:has-text("Accept")').click(); await page.waitForSelector('dialog[open]');
    d = await data();
    const wv = d.offers.find(o => o.case_id === c.case_id && o.title === 'Annual fee waiver');
    record('Accept step one shows a summary and changes no offer', wv.state === 'presented' && d.confirmations.some(x => x.offer_id === wv.offer_id && !x.used_at));
    await shot('confirm');
    await page.click('dialog button:has-text("Cancel")');
    record('Cancelling the confirmation creates no commitment', (await data()).commitments.length === before);
    await waiver.locator('button:has-text("Accept")').click(); await page.waitForSelector('dialog[open]');
    await page.click('dialog button:has-text("Confirm")'); await idle();
    d = await data();
    const m = d.commitments.find(x => x.offer_id === wv.offer_id);
    record('Confirming creates one pending commitment and closes the group', m && m.status === 'pending' && d.offers.filter(o => o.case_id === c.case_id && o.state === 'unavailable').length === 4);
    await shot('accepted');

    // A stale view reports the conflict and changes nothing.
    const current = await infra.call('env.snapshot');
    const applied = await infra.call('env.apply_event', {expected_version: current.version, event: {event_id: 'ev-web-0001', at: '2026-12-02T09:30:00-05:00', operation: 'counterline.case.followup', payload: {case_id: c.case_id, script_id: 'followup-credit-processing'}}});
    assert.equal(applied.status, 'committed', JSON.stringify(applied));
    const turnsBefore = (await data()).cases.find(x => x.case_id === c.case_id).transcript.length;
    await page.click('button[data-action=ask_status]'); await idle();
    record('A stale view shows the conflict', await page.locator('#status[data-code=stale_version]').count() === 1);
    record('A stale write changes nothing', (await data()).cases.find(x => x.case_id === c.case_id).transcript.length === turnsBefore);
    await page.click('button:has-text("Refresh")'); await idle();
    record('Refresh shows the scenario follow-up', await page.locator('.turn', {hasText: 'being processed'}).count() > 0);

    // Reload: committed data persists.
    await page.reload(); await page.waitForSelector('#status:has-text("Ready")');
    record('Reload shows the same case and commitment', await page.locator('.offer.accepted', {hasText: 'Annual fee waiver'}).count() === 1);

    // Commitments: the page separates a promise and a report from settlement; contest one.
    await page.click('nav button:has-text("Commitments")'); await idle();
    record('Commitments page says a report is not proof of payment', await page.getByText('Neither shows that money reached your account').count() === 1);
    await page.locator('.panel', {hasText: m.commitment_id}).locator('input[aria-label=Reason]').fill('The waiver does not show on my card account.');
    await page.locator('.panel', {hasText: m.commitment_id}).locator('button:has-text("Contest")').click(); await idle();
    record('Contest is recorded in the App', (await data()).commitments.find(x => x.commitment_id === m.commitment_id).status === 'contested');
    await shot('commitments');

    // Help center.
    await page.click('nav button:has-text("Help center")'); await idle();
    await page.fill('input[aria-label="Search help"]', 'transfer'); await page.press('input[aria-label="Search help"]', 'Enter'); await idle();
    await page.click('.case-row:has-text("Talking to the right team")'); await idle();
    await page.getByText('also called the retention team').waitFor();
    record('Help search and article read work', await page.getByText('also called the retention team').count() === 1);
    await shot('help');

    // Settings.
    await page.click('nav button:has-text("Settings")'); await idle();
    await page.check('#email-copies'); await idle();
    record('Email-copy preference is saved in the App', (await data()).preferences.email_copies === true);

    // Close and reopen; a closed case has no composer.
    await page.click('nav button:has-text("Cases")'); await idle();
    await page.click('button:has-text("Close case")'); await idle();
    record('Closed case shows no composer or quick actions', (await data()).cases.find(x => x.case_id === c.case_id).status === 'closed' && await page.locator('textarea[aria-label=Message]').count() === 0 && await page.locator('[aria-label="Quick actions"]').count() === 0);
    await page.click('button:has-text("Reopen")'); await idle();
    record('Reopen restores the case', (await data()).cases.find(x => x.case_id === c.case_id).status === 'open');

    // Direct management request through the business API is refused.
    const direct = await page.evaluate(async () => {
      const {csrf} = await (await fetch('/session')).json();
      const r = await fetch('/api/call', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Pale-CSRF': csrf}, body: JSON.stringify({name: 'env.reset', arguments: {}})});
      return r.status;
    });
    record('Direct management request is refused', direct === 403);

    // Narrow screen: no horizontal page scroll.
    await page.setViewportSize({width: 390, height: 844}); await page.reload(); await page.waitForSelector('#status:has-text("Ready")');
    record('Narrow layout has no horizontal scroll', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await shot('narrow');
    record('No JavaScript errors', errors.length === 0);
    await context.close();
    const report = {schema: 'pale.web-acceptance.v1', app: 'counterline', checked_at: new Date().toISOString(), node: process.version,
      browser: browser.version(), checks, read_tools_not_used_by_the_page: unusedReads, passed: true};
    fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    return report;
  } finally {
    if (infra) await infra.close();
    if (host) await host.close();
    await browser.close();
    fs.rmSync(stateDir, {recursive: true, force: true});
  }
}

if (require.main === module) main().then(r => { console.log(r.checks.map(c => 'ok - ' + c).join('\n')); console.log('PASS: Counterline web, ' + r.checks.length + ' checks.'); })
  .catch(e => { console.error(e); process.exitCode = 1; });
module.exports = {main};
