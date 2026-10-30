/* Track Event Readiness and Outstanding Actions - coordinator "Event Readiness" screen.
 * Loaded after app.js. app.js itself is NOT modified: at load this file adds an
 * "Event Readiness" item to the coordinator navigation and registers its page.
 * Reuses app.js helpers: pageHead, escapeHtml, escapeAttribute, authenticatedFetch,
 * roles, pages, renderPage and toast. Styling reuses existing classes.
 */
(function () {
  const API = '/api/track-readiness-actions';
  const state = { events: null, selectedId: null, data: null, error: '' };

  // ---------- helpers ----------
  const body = () => document.getElementById('traBody');

  async function request(path, method) {
    const response = await authenticatedFetch(API + path, { method: method || 'GET' });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
  }

  function formatDate(value) {
    if (!value) return 'No deadline';
    const dateOnly = String(value).length === 10;
    const d = new Date(dateOnly ? value + 'T00:00:00Z' : value);
    if (isNaN(d)) return String(value);
    return d.toLocaleDateString('en-SG', {
      day: 'numeric', month: 'long', year: 'numeric', timeZone: dateOnly ? 'UTC' : undefined,
    });
  }

  // Equipment reservations store "reserved" for the display label "Confirmed".
  const equipmentLabel = (status) => (status === 'reserved' ? 'Confirmed' : status || 'Unknown');
  const capitalise = (text) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : 'Unknown');

  // ---------- views ----------
  function listView() {
    if (state.events === null) return '<section class="panel"><p class="muted">Loading assigned events...</p></section>';
    if (!state.events.length) {
      return '<section class="panel empty-state"><h3>No assigned events</h3>' +
        '<p class="muted">No events are currently assigned to your account.</p></section>';
    }
    return '<section class="panel"><div class="list">' + state.events.map((e, i) =>
      `<div class="list-row"><div class="date-tile">${i + 1}</div><div><h4>${escapeHtml(e.name || 'Untitled event')}</h4>` +
      `<div class="muted">Event status: ${escapeHtml(e.status || 'unknown')}</div></div>` +
      `<button class="btn btn-soft btn-small" type="button" data-tra-open="${escapeAttribute(e.event_id)}">View readiness</button></div>`
    ).join('') + '</div></section>';
  }

  function conditionRow(condition) {
    const cls = condition.complete ? 'confirmed' : 'pending';
    return `<div class="equipment"><div><h4>${escapeHtml(condition.label)}</h4>` +
      `<span class="capacity">${escapeHtml(condition.detail)}</span></div>` +
      `<span class="status ${cls}">${condition.complete ? 'Complete' : 'Outstanding'}</span></div>`;
  }

  function detailView() {
    const d = state.data;
    if (!d) return '<section class="panel"><p class="muted">Loading readiness...</p></section>';
    const ready = d.readiness === 'Ready for Confirmation';
    const eventStatus = d.event.status || 'unknown';

    const banner = '<section class="panel"><div class="event-banner"><div>' +
      `<span class="status ${ready ? 'ready' : 'pending'}">${escapeHtml(d.readiness)}</span>` +
      `<h2 style="margin-top:12px">${escapeHtml(d.event.name || 'Untitled event')}</h2>` +
      `<p class="muted">Event status: ${escapeHtml(eventStatus)}</p></div></div>` +
      Object.values(d.conditions).map(conditionRow).join('') + '</section>';

    const venues = d.venue_bookings.length
      ? d.venue_bookings.map((b) => `<div class="equipment"><span>Venue booking</span><strong>${escapeHtml(capitalise(b.status))}</strong></div>`).join('')
      : '<p class="muted">No venue booking has been requested.</p>';
    const reservations = d.equipment_reservations.length
      ? d.equipment_reservations.map((r) => `<div class="equipment"><span>${escapeHtml(r.equipment_name || 'Equipment')}</span>` +
        `<strong>${escapeHtml(equipmentLabel(r.status))}</strong></div>`).join('')
      : '<p class="muted">No equipment reservations.</p>';
    const statuses = `<section class="panel" style="margin-top:20px"><div class="panel-head"><h2>Booking and reservation status</h2></div>${venues}${reservations}</section>`;

    const actions = '<section class="panel" style="margin-top:20px"><div class="panel-head"><h2>Outstanding actions</h2></div>' +
      (d.outstanding_actions.length
        ? d.outstanding_actions.map((a) => `<div class="task"><span>${escapeHtml(a.message)}</span></div>`).join('')
        : '<div class="notice"><strong>No outstanding actions</strong><span class="muted">All readiness conditions are met.</span></div>') +
      '</section>';

    const tasks = d.unfinished_tasks.length
      ? '<section class="panel" style="margin-top:20px"><div class="panel-head"><h2>Unfinished tasks</h2></div>' +
        d.unfinished_tasks.map((t) => `<div class="list-row"><div class="date-tile">${t.overdue ? '!' : '·'}</div><div>` +
          `<h4>${escapeHtml(t.name || 'Untitled task')}</h4><div class="muted">Responsible: ${escapeHtml(t.responsible || 'Unassigned')} · ` +
          `Deadline: ${escapeHtml(formatDate(t.deadline))}</div></div>` +
          (t.overdue ? '<span class="status issue">Overdue</span>' : '<span></span>') + '</div>').join('') +
        '</section>'
      : '';

    const canAttempt = eventStatus === 'approved';
    const footer = '<p class="form-error" id="traError" role="alert" aria-live="polite">' + escapeHtml(state.error) + '</p>' +
      '<div class="form-actions"><button class="btn btn-outline" type="button" id="traBack">Back to assigned events</button>' +
      '<button class="btn btn-soft" type="button" id="traRefresh">Refresh readiness</button>' +
      (canAttempt ? '<button class="btn btn-primary" type="button" id="traConfirm">Confirm event</button>' : '') + '</div>' +
      (eventStatus === 'confirmed' ? '<div class="notice"><strong>This event is confirmed</strong></div>' : '');

    return banner + statuses + actions + tasks + footer;
  }

  function render() {
    const box = body();
    if (!box) return;
    box.innerHTML = state.selectedId ? detailView() : listView();
    box.querySelectorAll('[data-tra-open]').forEach((b) =>
      b.addEventListener('click', () => openEvent(b.dataset.traOpen)));
    const on = (id, handler) => { const el = document.getElementById(id); if (el) el.addEventListener('click', handler); };
    on('traBack', () => { state.selectedId = null; state.data = null; state.error = ''; render(); loadEvents(); });
    on('traRefresh', () => { state.error = ''; loadReadiness(); });
    on('traConfirm', confirmEvent);
  }

  // ---------- loading ----------
  async function loadEvents() {
    try {
      const { ok, data } = await request('/events');
      state.events = ok ? data.events || [] : [];
      if (!ok) state.error = data.error || 'Unable to load assigned events.';
    } catch (error) { state.events = []; state.error = error.message; }
    render();
    if (state.error && !state.selectedId) { toast(state.error); state.error = ''; }
  }

  async function loadReadiness() {
    try {
      const { ok, data } = await request('/events/' + encodeURIComponent(state.selectedId));
      if (ok) { state.data = data; state.error = ''; } else { state.error = data.error || 'Unable to load readiness.'; }
    } catch (error) { state.error = error.message; }
    render();
  }

  function openEvent(eventId) {
    state.selectedId = eventId;
    state.data = null;
    state.error = '';
    render();
    loadReadiness();
  }

  async function confirmEvent() {
    const button = document.getElementById('traConfirm');
    if (button) button.disabled = true;
    try {
      const { ok, data } = await request('/events/' + encodeURIComponent(state.selectedId) + '/confirm', 'POST');
      if (ok) {
        toast('The event has been confirmed.');
        state.error = '';
        await loadReadiness();  // shows the refreshed readiness and the new status
        return;
      }
      state.error = data.error || 'Unable to confirm the event.';
      if (data.readiness) state.data = data.readiness;  // current readiness with outstanding actions
    } catch (error) { state.error = error.message; }
    render();
  }

  // ---------- page + hook into the existing app without editing app.js ----------
  function readinessPage() {
    state.events = null;
    state.selectedId = null;
    state.data = null;
    state.error = '';
    return pageHead('Event readiness', 'See what remains before an assigned event can be confirmed.') +
      '<div id="traBody"></div>';
  }

  function bindReadinessPage() {
    if (!body()) return;
    render();
    loadEvents();
  }

  if (typeof pages === 'undefined' || typeof roles === 'undefined' || typeof renderPage !== 'function' ||
      !pages.coordinator || !roles.coordinator) {
    console.warn('track-readiness-actions.js: could not attach to app.js (pages/roles/renderPage not found).');
    return;
  }
  if (!roles.coordinator.nav.some((item) => item[2] === 'readiness')) {
    const at = roles.coordinator.nav.findIndex((item) => item[2] === 'assignments');
    roles.coordinator.nav.splice(at + 1, 0, ['✓', 'Event Readiness', 'readiness']);
  }
  pages.coordinator.readiness = readinessPage;
  const originalRenderPage = window.renderPage;  // keeps wrappers added by other scripts
  window.renderPage = function () {
    const result = originalRenderPage.apply(this, arguments);
    if (typeof currentRole !== 'undefined' && currentRole === 'coordinator' && currentPage === 'readiness') bindReadinessPage();
    return result;
  };
  console.info('track-readiness-actions.js: Event Readiness page attached.');
})();