/* Technical Support request cards and review, using the shared UI and session. */
(function () {
  const API = '/api/equipment-requests';
  const reviewPages = new Set(['dashboard', 'assignments', 'equipment', 'equipmentdetails', 'equipmentevent']);
  let sessionToken = null, epoch = 0, rows = null, selected = null, detail = null;
  let events = [], catalogue = [], catalogueItems = [], selectedEvent = null;
  let checks = {}, error = '', notice = '', confirmation = null, busy = false;
  const visible = () => currentRole === 'technical' && reviewPages.has(currentPage) && document.getElementById('equipmentReview');
  const current = generation => generation === epoch && sessionToken === authSession?.access_token;
  const period = row => [row.start_datetime, row.end_datetime].map(value => {
    const date = new Date(value);
    return value && !isNaN(date) ? date.toLocaleString('en-SG', {
      timeZone: 'Asia/Singapore', day: 'numeric', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    }) : 'Time needs clarification';
  }).join(' – ') + ' (Singapore time)';
  const field = (label, value) => `<div class="equipment"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value || 'Not recorded')}</strong></div>`;

  function resetSession() {
    if (sessionToken !== authSession?.access_token) {
      sessionToken = authSession?.access_token; epoch++;
      rows = null; selected = null; detail = null; checks = {}; events = []; catalogue = []; catalogueItems = []; selectedEvent = null;
      error = ''; notice = ''; confirmation = null; busy = false;
    }
  }

  async function request(path, method = 'GET', payload) {
    const generation = epoch;
    const response = await authenticatedFetch(API + path, {method, ...(payload ? {headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)} : {})});
    const data = await response.json();
    if (!current(generation)) throw new Error('The session has changed. Reload equipment requests.');
    if (!response.ok) throw new Error(data.error || 'Unable to load equipment requests.');
    return data;
  }

  function details(item) {
    const r = item.reservation;
    return `<h3>${escapeHtml(item.event.name || r.event_id)}</h3>` +
      field('Equipment', item.equipment.name || r.equipment_id) +
      field('Type / organiser requested quantity', `${item.equipment.type || 'Not recorded'} / ${r.quantity_requested ?? 'See original requirements'}`) +
      field('Suggested quantity', r.quantity_suggested ?? 'Not proposed') +
      `<p class="muted">${escapeHtml(period(r))}</p>`;
  }

  function requestCard(item) {
    return `<article class="event-card">${details(item)}` + field('Request status', item.reservation.status) +
      `<button class="btn btn-soft" data-equipment-open="${escapeAttribute(item.reservation.reservation_id)}" ${busy ? 'disabled' : ''}>Open request details</button></article>`;
  }

  function requestReview(item) {
    const r = item.reservation, id = r.reservation_id, check = checks[id];
    const agreed = r.proposal_version > 0 && r.organiser_agreed_version === r.proposal_version && r.organiser_agreed_by && r.organiser_agreed_at;
    const eligible = r.status === 'requested' && ['approved', 'confirmed'].includes(item.event.status);
    const availability = !check
      ? {kind: 'neutral', title: 'Availability not checked', text: 'Check current stock and scheduling before acceptance. Earlier requests retain priority.'}
      : check.error
        ? {kind: 'error', title: 'Availability check could not be completed', text: check.error}
        : check.sufficient_stock
          ? {kind: 'success', title: `${check.available_quantity} available`, text: `Enough stock is available for the suggested quantity of ${r.quantity_suggested}.`}
          : {kind: 'warning', title: 'Not enough equipment available', text: `Available quantity: ${check.available_quantity} — insufficient stock for this request.`};
    return `<section class="panel equipment-review-card" style="margin-bottom:20px">` +
      `<div class="panel-head equipment-review-head"><div><p class="equipment-kicker">Equipment request</p><h2>${escapeHtml(item.event.name || r.event_id)}</h2></div>` +
      `<span class="status ${r.status === 'reserved' ? 'confirmed' : 'pending'}">${escapeHtml(r.status)}</span></div>` +
      `<div class="equipment-summary-grid">${field('Equipment', item.equipment.name || r.equipment_id)}` +
      field('Type', item.equipment.type) + field('Suggested quantity', r.quantity_suggested ?? 'Not proposed') +
      field('Request status', r.status) + `</div><p class="equipment-period">${escapeHtml(period(r))}</p>` +
      (eligible ? `<div class="equipment-review-section">${proposalForm(item.event, r)}</div>` +
        `<div class="equipment-review-section equipment-decision"><div class="equipment-agreement"><span>Organiser agreement</span><strong>${agreed ? 'Agreed to current proposal' : 'Awaiting organiser agreement'}</strong></div>` +
        `<div class="availability-state availability-${availability.kind}" role="${availability.kind === 'error' ? 'alert' : 'status'}"><div class="availability-icon" aria-hidden="true">${availability.kind === 'success' ? '✓' : availability.kind === 'warning' || availability.kind === 'error' ? '!' : '○'}</div>` +
        `<div><strong>${escapeHtml(availability.title)}</strong><p>${escapeHtml(availability.text)}</p></div></div>` +
        `<div class="equipment-actions"><button class="btn btn-soft" data-equipment-check="${escapeAttribute(id)}" ${busy || !r.quantity_suggested ? 'disabled' : ''}>Check availability</button>` +
        `<button class="btn btn-primary" data-equipment-accept="${escapeAttribute(id)}" ${busy || !agreed || !check?.sufficient_stock ? 'disabled' : ''}>Accept reviewed request</button></div></div>` :
        `<div class="availability-state availability-${r.status === 'reserved' ? 'success' : 'neutral'}"><div class="availability-icon" aria-hidden="true">${r.status === 'reserved' ? '✓' : '○'}</div><div><strong>${r.status === 'reserved' ? 'Reservation saved' : 'Request unavailable'}</strong><p>${r.status === 'reserved' ? 'This equipment reservation has been recorded.' : 'This event is not eligible for acceptance.'}</p></div></div>`) + '</section>';
  }

  function eventDetails(item) {
    const event = item.event;
    const bookings = (event.venue_booking || []).filter(b => ['requested', 'tentative', 'confirmed'].includes(b.status));
    return `<section class="panel" style="margin-bottom:20px"><h2>Event and booking details</h2>` +
      field('Event status', event.status) + field('Description', event.description) +
      field('Event technical requirements', event.technical_requirements) +
      field('Request technical requirements', item.reservation.technical_requirements) +
      field('Venue requirements', event.venue_requirements) +
      (bookings.length ? bookings.map(b => field('Venue booking', `${b.venue?.name || b.venue_id} — ${b.status}`) +
        field('Venue location', b.venue?.location) + `<p class="muted">${escapeHtml(period({start_datetime: b.requested_start, end_datetime: b.requested_end}))}</p>`).join('') :
        '<p class="muted">No active venue booking is visible for this event.</p>') +
      field('Request ID', item.reservation.reservation_id) +
      (item.reservation.status === 'reserved' ? field('Accepted at', item.reservation.decided_at) : '') + '</section>';
  }

  const localTime = value => {
    const date = value ? new Date(value) : null;
    return date && !isNaN(date) ? date.toLocaleString('sv-SE', {timeZone: 'Asia/Singapore'}).replace(' ', 'T').slice(0, 16) : '';
  };

  function proposalForm(event, row = null) {
    if (!['approved', 'confirmed'].includes(event.status)) return '<p class="notice">Submitted requirements received. Equipment proposals can be saved after Coordinator review moves the event to approved.</p>';
    if (!catalogue.length) return '<p class="muted">Refresh to load the active equipment catalogue before making a proposal.</p>';
    const confirmedBookings = (event.venue_booking || []).filter(b => b.status === 'confirmed');
    const booking = confirmedBookings.length === 1 ? confirmedBookings[0] : null;
    const start = row?.start_datetime || booking?.requested_start || event.start_datetime || event.preferred_start_datetime;
    const end = row?.end_datetime || booking?.requested_end || event.end_datetime || event.preferred_end_datetime;
    const items = row ? catalogue.filter(e => e.equipment_id === row.equipment_id) : catalogue.filter(e => !(rows || []).some(item => item.reservation.event_id === event.event_id && item.reservation.equipment_id === e.equipment_id));
    if (!items.length) return '<p class="muted">No additional active catalogue items are available here. Review existing proposals, or ask the equipment team to clarify inactive items.</p>';
    return `<form data-equipment-proposal="${escapeAttribute(event.event_id || row?.event_id)}" data-reservation="${escapeAttribute(row?.reservation_id || '')}" data-version="${row?.proposal_version || 0}">` +
      '<h3>Suggested equipment provision</h3><p class="muted">Save a proposal for the organiser to agree to. This does not reserve stock. Final reservation requires agreement and a confirmed venue booking for the same period.</p><div class="form-grid">' +
      `<div class="field"><label>Equipment<select name="equipment_id">${items.map(e => `<option value="${escapeAttribute(e.equipment_id)}">${escapeHtml(e.name)} (${escapeHtml(e.type || 'Equipment')})</option>`).join('')}</select></label></div>` +
      `<div class="field"><label>Suggested quantity<input name="quantity_suggested" type="number" min="1" step="1" value="${row?.quantity_suggested || ''}" required></label></div>` +
      `<div class="field"><label>Start (Singapore time)<input name="start_datetime" type="datetime-local" value="${escapeAttribute(localTime(start))}" required></label></div>` +
      `<div class="field"><label>End (Singapore time)<input name="end_datetime" type="datetime-local" value="${escapeAttribute(localTime(end))}" required></label></div></div>` +
      `<button class="btn btn-soft" type="submit" ${busy ? 'disabled' : ''}>Save suggested quantity</button></form>`;
  }

  function eventCard(event) {
    return `<article class="event-card"><h3>${escapeHtml(event.name)}</h3>${field('Organiser requirements', event.technical_requirements)}${field('Event status', event.status)}` +
      `<button class="btn btn-soft" data-equipment-event="${escapeAttribute(event.event_id)}" ${busy ? 'disabled' : ''}>Open organiser request</button></article>`;
  }

  const statusLabel = status => ({available: 'Available', damaged: 'Damaged', under_repair: 'Under Repair', unavailable: 'Unavailable'})[status] || status;

  function operationalCatalogue() {
    const body = !catalogueItems.length
      ? '<p class="muted">No equipment catalogue items are visible to your account.</p>'
      : catalogueItems.map(item => `<form data-equipment-status-form="${escapeAttribute(item.equipment_id)}" class="event-card" style="margin-bottom:12px">` +
          `<h3>${escapeHtml(item.name || 'Unnamed equipment')}</h3>` +
          field('Type', item.type) + field('Total quantity', item.total_quantity) +
          `<div class="field"><label>Operational status<select name="operational_status">${['available', 'damaged', 'under_repair', 'unavailable'].map(status =>
            `<option value="${status}" ${item.operational_status === status ? 'selected' : ''}>${statusLabel(status)}</option>`).join('')}</select></label></div>` +
          `<p class="muted">${item.active ? 'Active catalogue item' : 'Inactive catalogue item; it remains excluded from new reservations.'}</p>` +
          `<button class="btn btn-soft" type="submit" ${busy ? 'disabled' : ''}>Save operational status</button></form>`).join('');
    return `<section class="panel" style="margin-bottom:20px"><h2>Equipment operational status</h2>` +
      '<p class="muted">Only active items marked Available can be selected for a new reservation.</p>' + body + '</section>';
  }

  async function saveOperationalStatus(form) {
    if (busy) return;
    const generation = epoch, id = form.dataset.equipmentStatusForm;
    busy = true; error = ''; notice = ''; render();
    try {
      const saved = await request(`/catalogue/${encodeURIComponent(id)}/operational-status`, 'PATCH', {
        operational_status: form.elements.operational_status.value
      });
      if (!current(generation)) return;
      catalogueItems = catalogueItems.map(item => item.equipment_id === id ? saved : item);
      catalogue = catalogue.filter(item => item.equipment_id !== id);
      if (saved.active && saved.operational_status === 'available') catalogue.push(saved);
      catalogue.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
      checks = {};
      notice = `${saved.name || 'Equipment'} is now ${statusLabel(saved.operational_status)}.`;
    } catch (err) { if (current(generation)) error = err.message; }
    finally { if (current(generation)) { busy = false; render(); } }
  }

  async function saveProposal(form) {
    if (busy) return;
    const values = form.elements;
    const payload = {event_id: form.dataset.equipmentProposal, equipment_id: values.equipment_id.value,
      quantity_suggested: Number(values.quantity_suggested.value),
      start_datetime: values.start_datetime.value + '+08:00', end_datetime: values.end_datetime.value + '+08:00'};
    if (form.dataset.reservation) Object.assign(payload, {reservation_id: form.dataset.reservation, proposal_version: Number(form.dataset.version)});
    const generation = epoch;
    busy = true; error = ''; confirmation = null; render();
    try {
      const saved = await request('/proposals', 'POST', payload);
      if (!current(generation)) return;
      rows = (rows || []).filter(item => item.reservation.reservation_id !== saved.reservation.reservation_id).concat([saved]);
      selected = saved.reservation.reservation_id; detail = saved; checks = {};
      go('equipmentdetails');
    } catch (err) { if (current(generation)) error = err.message; }
    finally { if (current(generation)) { busy = false; render(); } }
  }

  function page() {
    resetSession();
    const isDetail = currentPage === 'equipmentdetails';
    const title = isDetail ? 'Equipment request details' : currentPage === 'dashboard' ? 'Technical operations' : currentPage === 'assignments' ? 'Event equipment requests' : 'Equipment';
    let content;
    if (currentPage === 'equipmentevent') {
      const event = events.find(e => e.event_id === selectedEvent);
      content = event ? `<section class="panel"><h2>${escapeHtml(event.name)}</h2>${field('Original organiser requirements', event.technical_requirements)}${field('Description', event.description)}${proposalForm(event)}</section>` : '<p class="muted">This organiser request is not available. Return to the requests list and refresh.</p>';
    } else if (isDetail) {
      content = detail ? eventDetails(detail) + requestReview(detail) : `<p class="muted">${error ? 'Request details could not be loaded. Use Refresh to try again.' : 'Loading request details…'}</p>`;
    } else if (rows === null) {
      content = '<p class="muted">Loading equipment requests…</p>';
    } else if (!rows.length && !events.length) {
      content = '<section class="panel empty-state"><h3>No equipment requests</h3><p class="muted">No pending or reserved equipment requests are visible to your account. After Coordinator approval, organiser events with equipment or technical requirements will appear here. Refresh to check for new submissions.</p></section>';
    } else {
      content = currentPage === 'equipment' ? rows.map(requestReview).join('') :
        `<div class="event-grid">${rows.map(requestCard).join('')}</div>`;
      const orphanEvents = events;
      if (orphanEvents.length) content = `<div class="event-grid">${orphanEvents.map(eventCard).join('')}</div>` + content;
      if (currentPage === 'dashboard') content = stats([
        ['Events with requests', String(new Set([...rows.map(item => item.reservation.event_id), ...events.map(e => e.event_id)]).size), '▣', 'Loaded from Supabase'],
        ['Pending equipment requests', String(rows.filter(item => item.reservation.status === 'requested').length), '⌘', 'Awaiting review'],
        ['Accepted equipment requests', String(rows.filter(item => item.reservation.status === 'reserved').length), '✓', 'Saved reservations']
      ]) + content;
    }
    if (currentPage === 'equipment' && !isDetail) content = operationalCatalogue() + content;
    if (confirmation) content = `<section class="panel" role="status" style="margin-bottom:20px"><h2>Equipment reservation confirmed</h2>${details(confirmation)}<p class="muted">Saved status: ${escapeHtml(confirmation.reservation.status)}</p>` +
      (confirmation.event.status === 'approved' ? '<p class="notice">The reservation is available to the assigned Coordinator under Event Readiness for final approval. The event remains approved until the Coordinator confirms that all arrangements are ready.</p>' : '') + '</section>' + content;
    const back = isDetail || currentPage === 'equipmentevent' ? '<button class="btn btn-soft" id="equipmentBack">Back to requests</button>' : '';
    return pageHead(title, 'Review organiser requirements, propose quantities, and reserve agreed equipment.',
      `${back}<button class="btn btn-soft" id="equipmentRefresh" ${busy ? 'disabled' : ''}>Refresh</button>`) +
      `<div id="equipmentReview"><p class="form-error" role="alert" aria-live="polite">${escapeHtml(error)}</p><p role="status" aria-live="polite">${escapeHtml(notice)}</p>${content}</div>`;
  }

  function render() { if (visible()) renderPage(); }

  async function load() {
    if (busy) return;
    const generation = epoch, id = currentPage === 'equipmentdetails' ? selected : null;
    busy = true; error = ''; notice = ''; confirmation = null; checks = {}; render();
    try {
      if (id) {
        const data = await request(`/${encodeURIComponent(id)}`);
        if (current(generation) && selected === id) detail = data;
      } else {
        // Organiser requirements must remain visible even if an older equipment
        // row has inaccessible metadata. Report each failure without hiding the
        // independently loaded inbox.
        const results = await Promise.allSettled([request(''), request('/context'), request('/catalogue')]);
        if (!current(generation)) return;
        rows = results[0].status === 'fulfilled' ? results[0].value.requests.filter(item => ['approved', 'confirmed'].includes(item.event.status)) : [];
        const context = results[1].status === 'fulfilled' ? results[1].value : {};
        events = (context.events || []).filter(event => ['approved', 'confirmed'].includes(event.status)); catalogue = context.equipment || [];
        catalogueItems = results[2].status === 'fulfilled' ? results[2].value.equipment || [] : [];
        error = results.filter(result => result.status === 'rejected').map(result => result.reason.message).join(' ');
      }
    } catch (err) {
      if (!current(generation)) return;
      error = err.message;
      if (id) detail = null; else rows = [];
    } finally {
      if (current(generation)) { busy = false; render(); }
    }
  }

  async function act(id, accept) {
    if (busy) return;
    const generation = epoch;
    busy = true; error = ''; confirmation = null; render();
    try {
      const data = await request(`/${encodeURIComponent(id)}/${accept ? 'accept' : 'availability'}`, accept ? 'POST' : 'GET');
      if (!current(generation)) return;
      if (selected === id) detail = data;
      if (accept) {
        confirmation = data;
        if (rows) rows = rows.map(item => item.reservation.reservation_id === id ? data : item);
        checks = {};
      } else checks[id] = data;
    } catch (err) {
      if (current(generation)) {
        if (accept) { error = err.message; delete checks[id]; }
        else { error = ''; checks[id] = {error: err.message, sufficient_stock: false}; }
      }
    } finally {
      if (current(generation)) { busy = false; render(); }
    }
  }

  pages.technical.dashboard = page;
  pages.technical.assignments = page;
  pages.technical.equipment = page;
  pages.technical.equipmentdetails = page;
  pages.technical.equipmentevent = page;
  const originalRender = window.renderPage;
  window.renderPage = function () {
    const result = originalRender.apply(this, arguments);
    if (!visible()) return result;
    document.getElementById('equipmentRefresh').onclick = load;
    const back = document.getElementById('equipmentBack');
    if (back) back.onclick = () => { confirmation = null; error = ''; go('assignments'); };
    document.querySelectorAll('[data-equipment-event]').forEach(button => {
      button.onclick = () => { selectedEvent = button.dataset.equipmentEvent; error = ''; confirmation = null; go('equipmentevent'); };
    });
    document.querySelectorAll('[data-equipment-proposal]').forEach(form => {
      form.onsubmit = event => { event.preventDefault(); saveProposal(form); };
    });
    document.querySelectorAll('[data-equipment-status-form]').forEach(form => {
      form.onsubmit = event => { event.preventDefault(); saveOperationalStatus(form); };
    });
    document.querySelectorAll('[data-equipment-open]').forEach(button => {
      button.onclick = () => {
        if (busy) return;
        selected = button.dataset.equipmentOpen; detail = null; checks = {}; confirmation = null; error = '';
        go('equipmentdetails');
      };
    });
    document.querySelectorAll('[data-equipment-check]').forEach(button => {
      button.onclick = () => act(button.dataset.equipmentCheck, false);
    });
    document.querySelectorAll('[data-equipment-accept]').forEach(button => {
      button.onclick = () => act(button.dataset.equipmentAccept, true);
    });
    if (!busy && !error && (currentPage === 'equipmentdetails' ? selected && !detail : rows === null)) load();
    return result;
  };
})();

/* Organiser response is part of the equipment workflow, not a new login flow. */
(function () {
  if (!pages.organiser || typeof roles === 'undefined' || !roles.organiser) return;
  let token = null, rows = null, busy = false, error = '', notice = '';
  const active = () => currentRole === 'organiser' && currentPage === 'equipmentoffers';
  const same = requestToken => requestToken === authSession?.access_token && requestToken === token;
  const render = () => { if (active()) renderPage(); };
  const agreed = r => r.proposal_version > 0 && r.organiser_agreed_version === r.proposal_version && r.organiser_agreed_by && r.organiser_agreed_at;
  function page() {
    if (token !== authSession?.access_token) { token = authSession?.access_token; rows = null; busy = false; error = ''; notice = ''; }
    const content = rows === null ? '<p class="muted">Loading equipment proposals…</p>' : !rows.length ? '<section class="panel"><p>No equipment proposals are visible for your events yet.</p></section>' : rows.map(item => {
      const r = item.reservation;
      const displayTime = value => value ? new Date(value).toLocaleString('en-SG', {timeZone: 'Asia/Singapore'}) : 'Not recorded';
      return `<section class="panel" style="margin-bottom:20px"><h2>${escapeHtml(item.event.name)}</h2>` +
        `<p>${escapeHtml(item.event.technical_requirements || 'No original technical requirements recorded.')}</p>` +
        `<div class="equipment"><span>Equipment</span><strong>${escapeHtml(item.equipment.name)}</strong></div>` +
        `<div class="equipment"><span>Original requested quantity</span><strong>${escapeHtml(r.quantity_requested ?? 'See original requirements')}</strong></div>` +
        `<div class="equipment"><span>Technical Support suggests</span><strong>${escapeHtml(r.quantity_suggested)}</strong></div>` +
        `<p class="muted">${escapeHtml(displayTime(r.start_datetime))} – ${escapeHtml(displayTime(r.end_datetime))} (Singapore time)</p>` +
        (r.status === 'reserved' ? '<p>Equipment reservation saved.</p>' : agreed(r) ? '<p>You agreed to this proposal. Final reservation is awaiting Technical Support checks.</p>' :
          `<button class="btn btn-primary" data-equipment-agree="${escapeAttribute(r.reservation_id)}" data-version="${r.proposal_version}" ${busy ? 'disabled' : ''}>Agree to suggested quantity</button>`) + '</section>';
    }).join('');
    return pageHead('Equipment proposals', 'Review the item, suggested quantity and period before agreeing.', '<button class="btn btn-soft" id="equipmentOffersRefresh">Refresh</button>') +
      `<div id="equipmentOffers"><p class="form-error" role="alert">${escapeHtml(error)}</p><p role="status">${escapeHtml(notice)}</p>${content}</div>`;
  }
  async function call(path, payload) {
    const response = await authenticatedFetch('/api/equipment-requests' + path, payload ? {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    } : {});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to complete the equipment operation.');
    return data;
  }
  async function load() {
    if (busy) return;
    const requestToken = token;
    busy = true; error = ''; notice = ''; render();
    try { const data = await call('/organiser'); if (same(requestToken)) rows = data.requests; }
    catch (err) { if (same(requestToken)) { error = err.message; rows = []; } }
    finally { if (same(requestToken)) { busy = false; render(); } }
  }
  async function agree(id, version) {
    if (busy) return;
    const requestToken = token;
    busy = true; error = ''; notice = ''; render();
    try {
      const saved = await call(`/${encodeURIComponent(id)}/agree`, {proposal_version: version});
      if (!same(requestToken)) return;
      rows = rows.map(item => item.reservation.reservation_id === id ? saved : item);
      notice = 'Agreement saved. Technical Support must recheck availability before reserving the equipment.';
    } catch (err) { if (same(requestToken)) error = err.message; }
    finally { if (same(requestToken)) { busy = false; render(); } }
  }
  if (!roles.organiser.nav.some(item => item[2] === 'equipmentoffers')) roles.organiser.nav.push(['⌘', 'Equipment proposals', 'equipmentoffers']);
  pages.organiser.equipmentoffers = page;
  const original = window.renderPage;
  window.renderPage = function () {
    const result = original.apply(this, arguments);
    if (!active()) return result;
    document.getElementById('equipmentOffersRefresh').onclick = load;
    document.querySelectorAll('[data-equipment-agree]').forEach(button => {
      button.onclick = () => agree(button.dataset.equipmentAgree, Number(button.dataset.version));
    });
    if (rows === null && !busy && !error) load();
    return result;
  };
})();
