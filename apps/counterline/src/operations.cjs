'use strict';
// Agent tool handlers. Reads never change data; writes return { data, result }.
const { fail, copy, byId, nextId } = require('./util.cjs');
const { offerView, commitmentView, caseSummary } = require('./views.cjs');
const { log } = require('./diagnostics.cjs');
const APP = 'counterline';

function read(ctx, data, name, args) {
  const now = ctx.virtual_now;
  switch (name) {
    case `${APP}.help.search`: {
      const q = (args.query || '').toLocaleLowerCase();
      const hits = data.help_articles.filter(a => [a.title, a.body, ...a.tags].join(' ').toLocaleLowerCase().includes(q));
      return { articles: hits.map(({ article_id, title, tags }) => ({ article_id, title, tags: copy(tags) })) };
    }
    case `${APP}.help.get`:
      return { article: copy(byId(data.help_articles, 'article_id', args.article_id, 'Article')) };
    case `${APP}.cases.list`:
      return { cases: data.cases.filter(c => !args.status || c.status === args.status).map(caseSummary) };
    case `${APP}.cases.get`: {
      const c = byId(data.cases, 'case_id', args.case_id, 'Case');
      return { case: copy(c), offers: data.offers.filter(o => o.case_id === c.case_id).map(o => offerView(o, now)), now };
    }
    case `${APP}.offers.get`:
      return { offer: offerView(byId(data.offers, 'offer_id', args.offer_id, 'Offer'), now), now };
    case `${APP}.commitments.list`:
      return { commitments: data.commitments.filter(m => !args.status || m.status === args.status).map(m => commitmentView(m, now)), now };
    case `${APP}.commitments.get`:
      return { commitment: commitmentView(byId(data.commitments, 'commitment_id', args.commitment_id, 'Commitment'), now), now };
    default:
      return null;
  }
}

function openCase(ctx, data, args) {
  const p = data.provider;
  const topic = byId(p.topics, 'topic_id', args.topic_id, 'Topic');
  const greeting = byId(p.scripts, 'script_id', topic.greeting_script_id, 'Script');
  const case_id = nextId('cs', new Set(data.cases.map(c => c.case_id)));
  const at = ctx.virtual_now;
  data.cases.push({
    case_id, topic_id: topic.topic_id, account_ref: args.account_ref, status: 'open', tier: 'frontline',
    opened_at: at, closed_at: null,
    transcript: [
      { turn_id: 't-0001', at, speaker: 'customer', text: args.message, source: 'text', recognized: [], rule: null },
      { turn_id: 't-0002', at, speaker: 'representative', text: greeting.text, source: 'script', recognized: [], rule: `topic:${topic.topic_id}:greeting` }
    ]
  });
  log(ctx, 'counterline.case_opened', { case_id, topic_id: topic.topic_id });
  return { data, result: { case_id } };
}

function handleTool(ctx, data, name, args) {
  const view = read(ctx, data, name, args);
  if (view) return { data, result: view };
  if (name === `${APP}.cases.open`) return openCase(ctx, data, args);
  fail('unknown_tool', `Unknown Counterline operation: ${name}.`);
}
module.exports = { handleTool };
