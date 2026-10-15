/* Technical Support equipment review; uses the existing shared UI and session. */
(function () {
  const API = '/api/equipment-requests';
  let sessionToken = null, rows = null, checks = {}, error = '', confirmation = null, busy = false;
  const visible = () => currentRole === 'technical' && currentPage === 'equipment' && document.getElementById('equipmentReview');
  const period = (row) => [row.start_datetime, row.end_datetime].map(value => {
    const date = new Date(value);
    return value && !isNaN(date) ? date.toLocaleString('en-SG', {
      timeZone: 'Asia/Singapore', day: 'numeric', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    }) : 'Time needs clarification';
  }).join(' – ') + ' (Singapore time)';

  function resetSession() {
    if (sessionToken !== authSession?.access_token) {
      sessionToken = authSession?.access_token;
      rows = null; checks = {}; error = ''; confirmation = null; busy = false;
    }
  }

  async function request(path, method = 'GET') {
    const token = sessionToken;
    const response = await authenticatedFetch(API + path, {method});
    const data = await response.json();
    if (token !== authSession?.access_token) throw new Error('The session has changed. Reload equipment requests.');
    if (!response.ok) throw new Error(data.error || 'Unable to load equipment requests.');
    return data;
  }

  function details(item) {
    const r = item.reservation;
    return `<h3>${escapeHtml(item.event.name || r.event_id)}</h3>` +
      `<div class="equipment"><span>Equipment</span><strong>${escapeHtml(item.equipment.name || r.equipment_id)}</strong></div>` +
      `<div class="equipment"><span>Type / required quantity</span><strong>${escapeHtml(item.equipment.type || 'Not recorded')} / ${escapeHtml(r.quantity_requested)}</strong></div>` +
      `<p class="muted">${escapeHtml(period(r))}</p>`;
  }

  function page() {
    resetSession();
    let content = rows === null ? '<p class="muted">Loading equipment requests…</p>' : rows.length ? rows.map(item => {
      const r = item.reservation, id = r.reservation_id, check = checks[id];
      const eligible = r.status === 'planning' && ['planning', 'confirmed'].includes(item.event.status);
      return `<section class="panel" style="margin-bottom:20px">${details(item)}` +
        `<div class="equipment"><span>Request status</span><strong>${escapeHtml(r.status)}</strong></div>` +
        `<p class="muted">${check ? `Available quantity: ${escapeHtml(check.available_quantity)}${check.sufficient_stock ? '' : ' — insufficient stock for this request.'}` : 'Check stock before acceptance. Earlier requests retain priority.'}</p>` +
        (eligible ? `<div class="form-actions"><button class="btn btn-soft" data-equipment-check="${escapeAttribute(id)}" ${busy ? 'disabled' : ''}>Check availability</button>` +
          `<button class="btn btn-primary" data-equipment-accept="${escapeAttribute(id)}" ${busy || !check?.sufficient_stock ? 'disabled' : ''}>Accept reviewed request</button></div>` :
          `<p class="muted">${r.status === 'reserved' ? 'Reservation saved.' : 'Event is not eligible for acceptance.'}</p>`) + '</section>';
    }).join('') : '<section class="panel empty-state"><h3>No equipment requests</h3><p class="muted">No pending or reserved equipment requests are visible to your account.</p></section>';
    if (confirmation) content = `<section class="panel" role="status" style="margin-bottom:20px"><h2>Equipment reservation confirmed</h2>${details(confirmation)}<p class="muted">Saved status: ${escapeHtml(confirmation.reservation.status)}</p></section>` + content;
    return pageHead('Equipment requests', 'Review Coordinator requests and reserve available stock.',
      `<button class="btn btn-soft" id="equipmentRefresh" ${busy ? 'disabled' : ''}>Refresh</button>`) +
      `<div id="equipmentReview"><p class="form-error" role="alert" aria-live="polite">${escapeHtml(error)}</p>${content}</div>`;
  }

  function render() { if (visible()) renderPage(); }

  async function load() {
    busy = true; error = ''; render();
    try { const data = await request(''); rows = data.requests; checks = {}; }
    catch (err) { error = err.message; rows = []; }
    finally { busy = false; render(); }
  }

  async function act(id, accept) {
    if (busy) return;
    busy = true; error = ''; confirmation = null; render();
    try {
      const data = await request(`/${encodeURIComponent(id)}/${accept ? 'accept' : 'availability'}`, accept ? 'POST' : 'GET');
      if (accept) {
        confirmation = data;
        rows = rows.map(item => item.reservation.reservation_id === id ? data : item);
        checks = {}; // Other requests' cached quantities may now be stale.
      } else { checks[id] = data; }
    } catch (err) { error = err.message; delete checks[id]; }
    finally { busy = false; render(); }
  }

  pages.technical.equipment = page;
  const originalRender = window.renderPage;
  window.renderPage = function () {
    const result = originalRender.apply(this, arguments);
    if (!visible()) return result;
    document.getElementById('equipmentRefresh').onclick = load;
    document.querySelectorAll('[data-equipment-check]').forEach(button => {
      button.onclick = () => act(button.dataset.equipmentCheck, false);
    });
    document.querySelectorAll('[data-equipment-accept]').forEach(button => {
      button.onclick = () => act(button.dataset.equipmentAccept, true);
    });
    if (rows === null && !busy) load();
    return result;
  };
})();
