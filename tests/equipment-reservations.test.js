const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/js/equipment-reservations.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture(free = 1, acceptError = null) {
  const row = {reservation_id: 'request-1', event_id: 'event-1', equipment_id: 'eq-1',
    quantity_requested: 1, status: 'planning', start_datetime: '2026-11-20T01:00:00Z',
    end_datetime: '2026-11-20T04:00:00Z'};
  const item = {reservation: row, event: {name: '<script>event</script>', status: 'planning'},
    equipment: {name: 'Projector', type: 'Projector'}};
  const calls = [], refresh = {}, check = {dataset: {equipmentCheck: row.reservation_id}},
    accept = {dataset: {equipmentAccept: row.reservation_id}};
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  const context = {
    currentRole: 'technical', currentPage: 'equipment', authSession: {access_token: 'token'},
    pages: {technical: {}}, escapeHtml: escape, escapeAttribute: escape,
    pageHead: (title, sub, action) => title + sub + action,
    document: {getElementById: id => id === 'equipmentRefresh' ? refresh : {},
      querySelectorAll: selector => selector.includes('check') ? [check] : [accept]},
    authenticatedFetch: async (url, options) => {
      calls.push({url, options});
      if (url.endsWith('/availability')) return {ok: true, json: async () => ({...item, available_quantity: free, sufficient_stock: free >= 1})};
      if (url.endsWith('/accept')) return acceptError
        ? {ok: false, json: async () => ({error: acceptError})}
        : {ok: true, json: async () => ({...item, reservation: {...row, status: 'reserved', decided_by: 'tss'}})};
      return {ok: true, json: async () => ({requests: [item]})};
    },
  };
  context.window = context;
  context.renderPage = () => { context.html = context.pages.technical.equipment(); };
  vm.createContext(context);
  vm.runInContext(source, context);
  return {context, calls, check, accept, refresh};
}

test('review checks stock, posts only request ID, and renders the returned reservation', async () => {
  const f = fixture();
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /&lt;script&gt;event&lt;\/script&gt;/);
  assert.match(f.context.html, /09:00/); // UTC instants displayed in Singapore time.
  assert.match(f.context.html, /data-equipment-accept="request-1" disabled/);
  await f.check.onclick();
  assert.doesNotMatch(f.context.html, /data-equipment-accept="request-1" disabled/);
  await f.accept.onclick();
  assert.match(f.context.html, /Equipment reservation confirmed/);
  assert.match(f.context.html, /Saved status: reserved/);
  const call = f.calls.find(call => call.url.endsWith('/accept'));
  assert.equal(call.options.method, 'POST');
  assert.equal(call.options.body, undefined);
});

test('insufficient stock disables final acceptance and explains the quantity', async () => {
  const f = fixture(0);
  f.context.renderPage(); await tick(); await f.check.onclick();
  assert.match(f.context.html, /insufficient stock/);
  assert.match(f.context.html, /data-equipment-accept="request-1" disabled/);
  assert.equal(f.calls.filter(call => call.url.endsWith('/accept')).length, 0);
});

test('RPC conflicts remain visible without an optimistic reserved status', async () => {
  const f = fixture(1, 'Equipment is required for an earlier request.');
  f.context.renderPage(); await tick(); await f.check.onclick(); await f.accept.onclick();
  assert.match(f.context.html, /required for an earlier request/);
  assert.doesNotMatch(f.context.html, /Equipment reservation confirmed/);
  assert.match(f.context.html, /<strong>planning<\/strong>/);
  assert.match(f.context.html, /data-equipment-accept="request-1" disabled/);
});
