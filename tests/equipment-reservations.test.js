const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/js/equipment-reservations.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture(free = 1, acceptError = null, options = {}) {
  const row = {reservation_id: 'request-1', event_id: 'event-1', equipment_id: 'eq-1',
    quantity_requested: options.requestedQuantity ?? 1, quantity_suggested: options.suggestedQuantity ?? 1,
    proposal_version: 1, organiser_agreed_version: options.unagreed ? null : 1,
    organiser_agreed_by: options.unagreed ? null : 'owner', organiser_agreed_at: options.unagreed ? null : '2026-11-19T09:00:00Z', status: 'requested', start_datetime: '2026-11-20T01:00:00Z',
    end_datetime: '2026-11-20T04:00:00Z'};
  const item = {reservation: row, event: {event_id: 'event-1', organiser_id: 'owner', name: '<script>event</script>', status: options.eventStatus || 'planning',
    description: '<img src=x onerror=alert(1)>', technical_requirements: 'Projector and technician',
    venue_booking: [{booking_id: 'booking-1', venue_id: 'venue-1', status: 'confirmed',
      requested_start: row.start_datetime, requested_end: row.end_datetime,
      venue: {name: 'Seminar Room', location: 'Building A'}}]},
    equipment: {name: 'Projector', type: 'Projector'}};
  if (options.pendingVenueAlternative) item.event.venue_booking.push({
    booking_id: 'alternative', venue_id: 'venue-2', status: 'requested',
    requested_start: '2026-11-21T01:00:00Z', requested_end: '2026-11-21T04:00:00Z'
  });
  const calls = [], elements = new Map();
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  const context = {
    currentRole: options.role || 'technical', currentPage: options.page || 'equipment', authSession: {access_token: 'token'},
    pages: {technical: {}, organiser: {}}, roles: {organiser: {nav: []}}, escapeHtml: escape, escapeAttribute: escape,
    stats: items => items.map(item => item.join(' ')).join(' '),
    pageHead: (title, sub, action) => title + sub + action,
    document: {getElementById: id => {
      if (!context.html?.includes(`id="${id}"`)) return null;
      if (!elements.has(id)) elements.set(id, {});
      return elements.get(id);
    }, querySelectorAll: selector => {
      const attribute = selector.slice(1, -1);
      const datasetKey = attribute.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      const matches = [...(context.html || '').matchAll(new RegExp(`<(?:button|form)[^>]*${attribute}="([^"]*)"[^>]*>`, 'g'))];
      return matches.map(match => {
        const key = attribute + ':' + match[1];
        if (!elements.has(key)) {
          const dataset = {[datasetKey]: match[1]};
          for (const attr of match[0].matchAll(/data-([a-z-]+)="([^"]*)"/g)) dataset[attr[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = attr[2];
          elements.set(key, {dataset});
        }
        const element = elements.get(key);
        element.disabled = /\bdisabled\b/.test(match[0]);
        return element;
      });
    }},
    authenticatedFetch: async (url, requestOptions) => {
      calls.push({url, options: requestOptions});
      if (options.fetch) return options.fetch(url, requestOptions, item);
      if (url.endsWith('/context')) return {ok: true, json: async () => ({events: options.orphan ? [item.event] : [], equipment: [{equipment_id: 'eq-1', name: 'Projector', type: 'Projector'}]})};
      if (url.endsWith('/proposals')) {
        const payload = JSON.parse(requestOptions.body);
        return {ok: true, json: async () => ({...item, reservation: {...row, quantity_suggested: payload.quantity_suggested, proposal_version: 2, organiser_agreed_version: null, organiser_agreed_by: null, organiser_agreed_at: null}})};
      }
      if (url.endsWith('/agree')) return options.agreeError
        ? {ok: false, json: async () => ({error: options.agreeError})}
        : {ok: true, json: async () => ({...item, reservation: {...row, organiser_agreed_version: row.proposal_version, organiser_agreed_by: 'owner', organiser_agreed_at: '2026-11-19T09:00:00Z'}})};
      if (url.endsWith('/availability')) return {ok: true, json: async () => ({...item, available_quantity: free, sufficient_stock: free >= 1})};
      if (url.endsWith('/accept')) return acceptError
        ? {ok: false, json: async () => ({error: acceptError})}
        : {ok: true, json: async () => ({...item, reservation: {...row, status: 'reserved', decided_by: 'tss'}})};
      if (url.endsWith('/request-1')) return options.detailError
        ? {ok: false, json: async () => ({error: options.detailError})}
        : {ok: true, json: async () => item};
      return options.listError
        ? {ok: false, json: async () => ({error: options.listError})}
        : {ok: true, json: async () => ({requests: options.empty || options.orphan ? [] : [item]})};
    },
  };
  context.window = context;
  context.renderPage = () => { context.html = context.pages[context.currentRole][context.currentPage](); };
  context.go = page => { context.currentPage = page; context.renderPage(); };
  vm.createContext(context);
  vm.runInContext(source, context);
  return {context, calls,
    get check() { return context.document.querySelectorAll('[data-equipment-check]')[0]; },
    get accept() { return context.document.querySelectorAll('[data-equipment-accept]')[0]; },
    get open() { return context.document.querySelectorAll('[data-equipment-open]')[0]; },
    get refresh() { return context.document.getElementById('equipmentRefresh'); },
  };
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
  assert.match(f.context.html, /assigned Coordinator under Event Readiness for final approval/);
  assert.match(f.context.html, /event remains in planning/);
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
  assert.doesNotMatch(f.context.html, /assigned Coordinator under Event Readiness for final approval/);
  assert.match(f.context.html, /<strong>requested<\/strong>/);
  assert.match(f.context.html, /data-equipment-accept="request-1" disabled/);
});

test('dashboard cards open fresh request details and accept through the existing RPC endpoint', async () => {
  const f = fixture(1, null, {page: 'dashboard'});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /Pending equipment requests 1/);
  assert.doesNotMatch(f.context.html, /Analytics Workshop|Film Society|Returns due/);
  assert.ok(f.open);
  f.open.onclick(); await tick();
  assert.equal(f.context.currentPage, 'equipmentdetails');
  assert.ok(f.calls.some(call => call.url === '/api/equipment-requests/request-1'));
  assert.match(f.context.html, /Seminar Room — confirmed/);
  assert.match(f.context.html, /Projector and technician/);
  assert.match(f.context.html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(f.context.html, /<img src=x/);
  await f.check.onclick();
  assert.equal(f.accept.disabled, false);
  await f.accept.onclick();
  assert.match(f.context.html, /Equipment reservation confirmed/);
  assert.equal(f.accept, undefined);
  f.context.document.getElementById('equipmentBack').onclick();
  assert.equal(f.context.currentPage, 'assignments');
  assert.match(f.context.html, /reserved/);
  f.context.go('dashboard');
  assert.match(f.context.html, /Pending equipment requests 0/);
  assert.match(f.context.html, /Accepted equipment requests 1/);
});

test('assignments list contains saved request cards and no invented assignments', async () => {
  const f = fixture(1, null, {page: 'assignments'});
  f.context.renderPage(); await tick();
  assert.ok(f.open);
  assert.match(f.context.html, /&lt;script&gt;event&lt;\/script&gt;/);
  assert.doesNotMatch(f.context.html, /SMU Innovators Night|Analytics Workshop/);
  assert.equal(f.calls.filter(call => call.url === '/api/equipment-requests').length, 1);
});

test('empty dashboards explain how organiser requests reach the inbox', async () => {
  const f = fixture(1, null, {page: 'dashboard', empty: true});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /No equipment requests/);
  assert.match(f.context.html, /After Coordinator approval/);
  assert.equal(f.open, undefined);
});

test('load errors remain visible and do not fabricate dashboard cards', async () => {
  const f = fixture(1, null, {page: 'dashboard', listError: 'Required event information is not accessible.'});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /Required event information is not accessible/);
  assert.equal(f.open, undefined);
  assert.equal(f.calls.filter(call => call.url === '/api/equipment-requests').length, 1); // No automatic failing-request loop.
});

test('an inaccessible existing equipment row does not hide new organiser requirements', async () => {
  const f = fixture(1, null, {page: 'dashboard', orphan: true, eventStatus: 'planning', listError: 'Required event information is not accessible.'});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /Required event information is not accessible/);
  assert.equal(f.context.document.querySelectorAll('[data-equipment-event]').length, 1);
  f.context.document.querySelectorAll('[data-equipment-event]')[0].onclick();
  assert.match(f.context.html, /Original organiser requirements/);
  assert.equal(f.context.document.querySelectorAll('[data-equipment-proposal]').length, 1);
});

test('failed detail loading shows the error and supports an explicit retry', async () => {
  const f = fixture(1, null, {page: 'assignments', detailError: 'Equipment request not found or inaccessible.'});
  f.context.renderPage(); await tick();
  f.open.onclick(); await tick();
  assert.match(f.context.html, /Equipment request not found or inaccessible/);
  assert.equal(f.check, undefined);
  assert.equal(f.calls.filter(call => call.url.endsWith('/request-1')).length, 1);
  await f.refresh.onclick();
  assert.equal(f.calls.filter(call => call.url.endsWith('/request-1')).length, 2);
  assert.match(f.context.html, /Equipment request not found or inaccessible/);
});

test('detail stock conflicts retain pending status and clear approval eligibility', async () => {
  const f = fixture(1, 'Equipment is required for an earlier request.', {page: 'dashboard'});
  f.context.renderPage(); await tick();
  f.open.onclick(); await tick(); await f.check.onclick(); await f.accept.onclick();
  assert.match(f.context.html, /required for an earlier request/);
  assert.match(f.context.html, /<strong>requested<\/strong>/);
  assert.equal(f.accept.disabled, true);
  assert.doesNotMatch(f.context.html, /Equipment reservation confirmed/);
});

test('refresh invalidates the previous availability check before another acceptance', async () => {
  const f = fixture();
  f.context.renderPage(); await tick(); await f.check.onclick();
  assert.equal(f.accept.disabled, false);
  await f.refresh.onclick();
  assert.equal(f.accept.disabled, true);
});

test('a previous session response cannot populate the new account dashboard', async () => {
  let releaseOld;
  let count = 0;
  const f = fixture(1, null, {page: 'dashboard', fetch: async (url, options, item) => {
    if (++count === 1) return new Promise(resolve => { releaseOld = () => resolve({ok: true, json: async () => ({requests: [item]})}); });
    return {ok: true, json: async () => ({requests: []})};
  }});
  f.context.renderPage();
  f.context.authSession = {access_token: 'different-account'};
  f.context.renderPage(); await tick();
  releaseOld(); await tick();
  assert.match(f.context.html, /No equipment requests/);
  assert.doesNotMatch(f.context.html, /&lt;script&gt;event/);
  assert.equal(f.open, undefined);
});


test('approved organiser requirements appear before any equipment proposal exists', async () => {
  const f = fixture(1, null, {page: 'dashboard', orphan: true, eventStatus: 'planning'});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /Open organiser request/);
  assert.match(f.context.html, /<strong>planning<\/strong>/);
  const button = f.context.document.querySelectorAll('[data-equipment-event]')[0];
  button.onclick();
  assert.equal(f.context.currentPage, 'equipmentevent');
  assert.match(f.context.html, /Original organiser requirements/);
  assert.equal(f.context.document.querySelectorAll('[data-equipment-proposal]').length, 1);
});

test('staff can save an offered quantity without replacing the original requested quantity', async () => {
  const f = fixture(3, null, {requestedQuantity: 5, suggestedQuantity: 3, unagreed: true});
  f.context.renderPage(); await tick();
  const form = f.context.document.querySelectorAll('[data-equipment-proposal]')[0];
  form.elements = {equipment_id: {value: 'eq-1'},quantity_suggested: {value: '3'},
    start_datetime: {value: '2026-11-20T09:00'},end_datetime: {value: '2026-11-20T12:00'}};
  form.onsubmit({preventDefault() {}}); await tick();
  const call = f.calls.find(call => call.url.endsWith('/proposals'));
  const payload = JSON.parse(call.options.body);
  assert.equal(payload.quantity_suggested, 3);
  assert.equal(payload.quantity_requested, undefined);
  assert.equal(payload.start_datetime, '2026-11-20T09:00+08:00');
  assert.match(f.context.html, /Awaiting organiser agreement/);
  assert.equal(f.accept.disabled, true);
});

test('equipment proposal uses the confirmed venue period despite pending alternatives', async () => {
  const f = fixture(1, null, {page: 'dashboard', orphan: true, pendingVenueAlternative: true});
  f.context.renderPage(); await tick();
  f.context.document.querySelectorAll('[data-equipment-event]')[0].onclick();
  assert.match(f.context.html, /name="start_datetime"[^>]*value="2026-11-20T09:00"/);
  assert.match(f.context.html, /name="end_datetime"[^>]*value="2026-11-20T12:00"/);
  assert.doesNotMatch(f.context.html, /value="2026-11-21T09:00"/);
});

test('staff acceptance remains disabled until the current proposal is agreed', async () => {
  const f = fixture(3, null, {requestedQuantity: 5, suggestedQuantity: 3, unagreed: true});
  f.context.renderPage(); await tick(); await f.check.onclick();
  assert.equal(f.accept.disabled, true);
  assert.match(f.context.html, /Awaiting organiser agreement/);
});

test('organiser can agree to a smaller offer and sends only the reviewed version', async () => {
  const f = fixture(3, null, {role: 'organiser', page: 'equipmentoffers', requestedQuantity: 5, suggestedQuantity: 3, unagreed: true});
  f.context.renderPage(); await tick();
  assert.match(f.context.html, /Original requested quantity/);
  assert.match(f.context.html, /<strong>5<\/strong>/);
  assert.match(f.context.html, /<strong>3<\/strong>/);
  const button = f.context.document.querySelectorAll('[data-equipment-agree]')[0];
  await button.onclick();
  const call = f.calls.find(call => call.url.endsWith('/agree'));
  assert.deepEqual(JSON.parse(call.options.body), {proposal_version: 1});
  assert.match(f.context.html, /Agreement saved/);
  assert.match(f.context.html, /awaiting Technical Support checks/);
  assert.equal(f.calls.some(call => call.url.endsWith('/accept')), false);
});

test('stale organiser agreement shows an error instead of confirming consent', async () => {
  const f = fixture(1, null, {role: 'organiser', page: 'equipmentoffers', unagreed: true, agreeError: 'The proposal changed. Reload.'});
  f.context.renderPage(); await tick();
  await f.context.document.querySelectorAll('[data-equipment-agree]')[0].onclick();
  assert.match(f.context.html, /The proposal changed/);
  assert.doesNotMatch(f.context.html, /Agreement saved/);
});

for (const status of ['draft', 'requested', 'changes_requested']) {
  test(`Technical Support inbox excludes ${status} events until Coordinator approval`, async () => {
    const f = fixture(1, null, {page: 'dashboard', orphan: true, eventStatus: status});
    f.context.renderPage(); await tick();
    assert.equal(f.context.document.querySelectorAll('[data-equipment-event]').length, 0);
    assert.match(f.context.html, /After Coordinator approval/);
  });
}
