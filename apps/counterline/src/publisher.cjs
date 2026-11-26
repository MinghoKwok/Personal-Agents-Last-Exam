'use strict';
// App-owned outbound adapter for the optional Mail copies. Infra supplies trusted clients: an Infra
// connection to this Counterline instance and a Messaging connection fixed to this publisher. Reading
// through the Infra snapshot keeps these reads out of the Agent's audit. Counterline's own commit and
// Mail's receipt are separate commits; a copy has no business confirmation.
const pending = data => data.outbox.filter(n => n.status === 'pending_delivery');

// Mail's receiver-owned channel.email message. Title, body and time are frozen on the notification,
// so a retry sends identical bytes (Messaging fingerprints the whole message).
function message(data, n) {
  return {specversion: '1.0', id: 'counterline-' + n.notification_id,
    source: 'urn:pale:app:counterline:account:' + encodeURIComponent(data.account_id),
    type: 'org.pale.mail.notification.v1', time: n.time, datacontenttype: 'application/json',
    dataschema: 'urn:pale:email-payload:1', subject: n.notification_id,
    data: {channel: 'channel.email', recipient: {kind: 'person_ref', id: n.recipient_person_id},
      source_object: {app_id: 'counterline', account_id: data.account_id, object_type: 'notification', object_id: n.notification_id},
      content: {title: n.title, body: {format: 'text/plain', text: n.body}, asset_ids: []}, extensions: []}};
}

// Publish every pending copy once, then record each Messaging outcome on Counterline.
async function deliver({infra, router}) {
  const results = [];
  const snap = await infra.call('env.snapshot'), data = snap.snapshot.data;
  for (const n of pending(data)) {
    const receipt = await router.call('router.publish', {request_id: n.notification_id, message: message(data, n)});
    const status = ['committed', 'rejected', 'unknown', 'halted'].includes(receipt.status) ? receipt.status : 'unknown';
    const current = await infra.call('env.snapshot');
    const recorded = await infra.call('env.apply_event', {expected_version: current.version, event: {
      event_id: 'dlv-' + n.notification_id + '-' + current.version.revision, at: current.snapshot.virtual_now,
      operation: 'counterline.notification.delivery_recorded',
      payload: {notification_id: n.notification_id, status, code: receipt.code || null, stop_run: receipt.stop_run === true,
        router_event_id: receipt.event_id || null}}});
    results.push({notification_id: n.notification_id, receipt, recorded: recorded.status});
    if (receipt.stop_run) break; // the run halts for reconciliation, per the Messaging rules
  }
  return results;
}

module.exports = {pending, message, deliver};
