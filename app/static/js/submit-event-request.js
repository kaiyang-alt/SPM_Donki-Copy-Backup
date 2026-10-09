/* Submit Event Request - organiser "Create event" screen.
 * Loaded after app.js (already in index.html); app.js, app.py and index.html are NOT modified.
 * At load it swaps pages.organiser.create for this form and re-binds after each render.
 * Reuses app.js helpers: pageHead, escapeHtml, escapeAttribute, authenticatedFetch,
 * loadAuthorisedEvents, renderPage, go and toast. Styling reuses existing classes.
 */
(function () {
  const API = '/api/event-requests';
  const state = { eventId: null, result: null };
  const pad = (n) => String(n).padStart(2, '0');

  // ---------- markup ----------
  function field(key, label, control, full) {
    return `<div class="field${full ? ' full' : ''}"><label for="er_${key}">${label}</label>${control}` +
      `<p class="form-error" data-er-error="${key}" style="min-height:0"></p></div>`;
  }
  const input = (key, type, extra = '') => `<input id="er_${key}" type="${type}" ${extra}>`;
  const textarea = (key, placeholder = '') => `<textarea id="er_${key}" placeholder="${placeholder}"></textarea>`;
  const check = (key, label) =>
    `<div style="grid-column:1/-1"><div class="task"><input type="checkbox" id="er_${key}"><label for="er_${key}">${label}</label></div></div>`;

  function formHtml() {
    return '<div id="erDrafts"></div><section class="panel"><div class="form-grid">' +
      field('name', 'Event name *', input('name', 'text'), true) +
      field('description', 'Description', textarea('description'), true) +
      field('purpose', 'Purpose', textarea('purpose'), true) +
      field('preferred_date', 'Preferred date *', input('preferred_date', 'date')) +
      field('expected_attendance', 'Expected number of attendees *', input('expected_attendance', 'number', 'min="1" step="1"')) +
      field('start_time', 'Preferred start time *', input('start_time', 'time')) +
      field('end_time', 'Preferred end time *', input('end_time', 'time')) +
      field('venue_requirements', 'Venue requirements', textarea('venue_requirements', 'Capacity, location and facility needs'), true) +
      field('layout_requirements', 'Room layout requirements', textarea('layout_requirements', 'For example theatre, classroom or round tables'), true) +
      field('accessibility_needs', 'Accessibility and facility requirements', textarea('accessibility_needs'), true) +
      check('technical_support_required', 'Equipment / technical support required') +
      field('technical_requirements', 'Equipment and technical support requirements', textarea('technical_requirements'), true) +
      check('registration_enabled', 'Attendee registration required') +
      '</div><p class="form-error" id="erError" role="alert" aria-live="polite"></p>' +
      '<div class="form-actions">' +
      '<button class="btn btn-outline" type="button" id="erNew">New request</button>' +
      '<button class="btn btn-soft" type="button" id="erSaveDraft">Save draft</button>' +
      '<button class="btn btn-primary" type="button" id="erSubmit">Submit request</button>' +
      '</div></section>';
  }

  function confirmationHtml(event) {
    return pageHead('Event request submitted', 'Your request has been recorded.') +
      '<section class="panel"><div class="event-banner"><div>' +
      `<span class="status pending">${escapeHtml(event.status)}</span>` +
      '<h2 style="margin-top:12px">Your event request was submitted successfully</h2>' +
      '<p class="muted">The planning process can now begin.</p></div></div>' +
      `<div class="equipment"><span>Event name</span><strong>${escapeHtml(event.name)}</strong></div>` +
      `<div class="equipment"><span>Status</span><strong>${escapeHtml(event.status)}</strong></div>` +
      '<div class="form-actions"><button class="btn btn-soft" onclick="go(\'events\')">Back to my events</button>' +
      '<button class="btn btn-primary" onclick="go(\'create\')">Create another request</button></div></section>';
  }

  function eventRequestPage() {
    const result = state.result;
    state.result = null;
    state.eventId = null;
    if (result) return confirmationHtml(result);
    return pageHead('Create an event request',
      'Save an incomplete request as a draft, or submit it once the fields marked * are complete.') + formHtml();
  }

  // ---------- helpers ----------
  const el = (key) => document.getElementById('er_' + key);
  const val = (key) => el(key).value;

  function toIso(date, time) {
    if (!date || !time) return null;
    const d = new Date(`${date}T${time}`);
    return isNaN(d) ? null : d.toISOString();
  }

  function splitDateTime(iso) {
    const d = iso ? new Date(iso) : null;
    if (!d || isNaN(d)) return { date: '', time: '' };
    return {
      date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
      time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
    };
  }

  function collect() {
    const date = val('preferred_date');
    return {
      event_id: state.eventId,
      name: val('name'),
      description: val('description'),
      purpose: val('purpose'),
      expected_attendance: val('expected_attendance'),
      preferred_start_datetime: toIso(date, val('start_time')),
      preferred_end_datetime: toIso(date, val('end_time')),
      venue_requirements: val('venue_requirements'),
      layout_requirements: val('layout_requirements'),
      accessibility_needs: val('accessibility_needs'),
      technical_support_required: el('technical_support_required').checked,
      technical_requirements: val('technical_requirements'),
      registration_enabled: el('registration_enabled').checked,
    };
  }

  function fillForm(event) {
    ['name', 'description', 'purpose', 'expected_attendance', 'venue_requirements',
      'layout_requirements', 'accessibility_needs', 'technical_requirements'].forEach((key) => {
      el(key).value = event && event[key] != null ? event[key] : '';
    });
    el('technical_support_required').checked = !!(event && event.technical_support_required);
    el('registration_enabled').checked = !!(event && event.registration_enabled);
    const start = splitDateTime(event && event.preferred_start_datetime);
    const end = splitDateTime(event && event.preferred_end_datetime);
    el('preferred_date').value = start.date || end.date;
    el('start_time').value = start.time;
    el('end_time').value = end.time;
    state.eventId = event ? event.event_id : null;
    clearErrors();
  }

  function clearErrors() {
    document.querySelectorAll('[data-er-error]').forEach((p) => { p.textContent = ''; });
    document.querySelectorAll('[id^="er_"]').forEach((i) => { i.style.borderColor = ''; });
    document.getElementById('erError').textContent = '';
  }

  function flag(key, message) {
    const p = document.querySelector(`[data-er-error="${key}"]`);
    if (p) p.textContent = message;
    const i = el(key);
    if (i) i.style.borderColor = '#8A3E36';
  }

  // The database keeps one timestamp per value, so a date and a time must be entered together.
  function scheduleProblems() {
    const date = val('preferred_date'), start = val('start_time'), end = val('end_time');
    const problems = {};
    if (!date && (start || end)) problems.preferred_date = 'Enter the preferred date together with the time.';
    if (date && !start) problems.start_time = 'Enter the preferred start time together with the date.';
    return problems;
  }

  function showServerErrors(body) {
    const summary = [];
    (body.missing_fields || []).forEach((m) => {
      summary.push(m.label);
      if (m.field === 'preferred_start_datetime') {
        if (!val('preferred_date')) flag('preferred_date', 'Preferred date is required.');
        if (!val('start_time')) flag('start_time', 'Preferred start time is required.');
      } else if (m.field === 'preferred_end_datetime') {
        if (!val('preferred_date')) flag('preferred_date', 'Preferred date is required.');
        if (!val('end_time')) flag('end_time', 'Preferred end time is required.');
      } else {
        flag(m.field, `${m.label} is required.`);
      }
    });
    const uiKey = { preferred_start_datetime: 'start_time', preferred_end_datetime: 'end_time' };
    (body.invalid_fields || []).forEach((m) => flag(uiKey[m.field] || m.field, m.message));
    document.getElementById('erError').textContent =
      (body.error || 'Something went wrong.') + (summary.length ? ` Missing: ${summary.join(', ')}.` : '');
  }

  async function request(path, method, payload) {
    const response = await authenticatedFetch(API + path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: payload ? JSON.stringify(payload) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data };
  }

  // ---------- drafts ----------
  async function loadDrafts() {
    const box = document.getElementById('erDrafts');
    if (!box) return;
    try {
      const { ok, data } = await request('', 'GET');
      if (!ok) return;
      const drafts = (data.events || []).filter((e) => e.status === 'draft');
      box.innerHTML = drafts.length
        ? '<section class="panel" style="margin-bottom:20px"><div class="panel-head"><h2>Your drafts</h2></div><div class="list">' +
          drafts.map((d, i) =>
            `<div class="list-row"><div class="date-tile">${i + 1}</div><div><h4>${escapeHtml(d.name || 'Untitled draft')}</h4>` +
            `<div class="muted">Draft</div></div><button class="btn btn-soft btn-small" type="button" data-er-open="${escapeAttribute(d.event_id)}">Open</button></div>`
          ).join('') + '</div></section>'
        : '';
      box.querySelectorAll('[data-er-open]').forEach((b) =>
        b.addEventListener('click', () => openDraft(b.dataset.erOpen)));
    } catch (error) { /* the drafts list is optional; the form still works */ }
  }

  async function openDraft(eventId) {
    try {
      const { ok, data } = await request('/' + encodeURIComponent(eventId), 'GET');
      if (!ok) { document.getElementById('erError').textContent = data.error || 'Unable to open the draft.'; return; }
      fillForm(data.event);
      toast('Draft opened. You can edit it, save it or submit it.');
      window.scrollTo(0, document.body.scrollHeight);
    } catch (error) { document.getElementById('erError').textContent = error.message; }
  }

  // ---------- actions ----------
  async function run(path, onSuccess, buttons) {
    clearErrors();
    const problems = scheduleProblems();
    const keys = Object.keys(problems);
    if (keys.length) {
      keys.forEach((k) => flag(k, problems[k]));
      document.getElementById('erError').textContent = 'Some fields have invalid values.';
      return;
    }
    buttons.forEach((b) => { b.disabled = true; });
    try {
      const { ok, data } = await request(path, 'POST', collect());
      if (ok) await onSuccess(data); else showServerErrors(data);
    } catch (error) {
      document.getElementById('erError').textContent = error.message;
    } finally {
      buttons.forEach((b) => { b.disabled = false; });
    }
  }

  function bindEventRequestPage() {
    const submitBtn = document.getElementById('erSubmit');
    if (!submitBtn) return;
    const draftBtn = document.getElementById('erSaveDraft');
    const buttons = [draftBtn, submitBtn];

    draftBtn.addEventListener('click', () => run('/draft', async (data) => {
      state.eventId = data.event.event_id;
      toast('Draft saved.');
      await loadDrafts();
    }, buttons));

    submitBtn.addEventListener('click', () => run('/submit', async (data) => {
      state.result = data.event;
      try { await loadAuthorisedEvents(); } catch (error) { /* refresh of "My events" is best effort */ }
      renderPage();
      toast('Event request submitted.');
    }, buttons));

    document.getElementById('erNew').addEventListener('click', () => fillForm(null));
    loadDrafts();
  }

  // ---------- hook into the existing app without editing app.js ----------
  if (typeof pages === 'undefined' || typeof renderPage !== 'function') return;
  pages.organiser.create = eventRequestPage;
  const originalRenderPage = window.renderPage;  // keeps any wrapper added by other scripts
  window.renderPage = function () {
    const result = originalRenderPage.apply(this, arguments);
    bindEventRequestPage();  // no-op unless the request form is on screen
    return result;
  };
})();