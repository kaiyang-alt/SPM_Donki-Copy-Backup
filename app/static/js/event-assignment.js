/* ConnectSphere — Event Assignment story.
   Coordinator "Assigned events" list and organiser coordinator-assignment status.
   Load after app.js. Does not modify app.js: it registers its page renderers on
   app.js's `pages` object and loads data when #mainContent is re-rendered.
   Reuses app.js's authenticatedFetch, escapeHtml, escapeAttribute, eventIdentifier,
   authorisedEvents, selectedEventIndex and existing CSS classes. */
(function () {
  'use strict';

  const API_BASE = '/api/event-assignment';

  const STATUS_LABELS = {
    draft: 'Draft',
    requested: 'Requested',
    changes_requested: 'Changes requested',
    planning: 'Planning',
    confirmed: 'Confirmed',
    completed: 'Completed',
    cancelled: 'Cancelled',
    withdrawn: 'Withdrawn',
    rejected: 'Rejected'
  };

  function statusLabel(status) {
    return STATUS_LABELS[status] || 'Unknown';
  }

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatDate(value) {
    const date = parseDate(value);
    return date
      ? date.toLocaleString('en-SG', { dateStyle: 'medium', timeStyle: 'short' })
      : 'Date to be confirmed';
  }

  function dateTile(value, fallback) {
    const date = parseDate(value);
    if (!date) return `<div class="date-tile">${escapeHtml(fallback)}</div>`;
    const month = date.toLocaleString('en-SG', { month: 'short' }).toUpperCase();
    return `<div class="date-tile"><small>${escapeHtml(month)}</small>${date.getDate()}</div>`;
  }

  async function apiGet(path) {
    const response = await authenticatedFetch(API_BASE + path); // adds Bearer token, handles 401
    let data = {};
    try { data = await response.json(); } catch (error) { data = {}; }
    if (!response.ok) throw new Error(data.error || 'Unable to load event assignment information.');
    return data;
  }

  /* ---------- Coordinator: Assigned events ---------- */

  function assignedEventsPanel() {
    return `<section class="panel" id="assignedEventsList"><p class="muted">Loading assigned events…</p></section>`;
  }

  function assignedEventRow(event, index) {
    const attendance = event.expected_attendance != null
      ? `Expected attendance: ${escapeHtml(event.expected_attendance)}`
      : 'Expected attendance not provided';
    return `<div class="list-row">${dateTile(event.start, index + 1)}<div><h4>${escapeHtml(event.name)}</h4><div class="muted">${escapeHtml(formatDate(event.start))} · ${attendance}</div></div><span class="status ${escapeAttribute(event.status)}">${escapeHtml(statusLabel(event.status))}</span></div>`;
  }

  async function loadAssignedEvents() {
    let html;
    try {
      const data = await apiGet('/assigned-events');
      const events = data.events || [];
      html = events.length
        ? events.map(assignedEventRow).join('')
        : `<div class="empty-state"><h3>No assigned events</h3><p class="muted">No events are currently assigned to your account.</p></div>`;
    } catch (error) {
      html = `<div class="empty-state"><h3>Unable to load assigned events</h3><p class="muted">${escapeHtml(error.message)}</p></div>`;
    }
    const target = document.getElementById('assignedEventsList'); // user may have navigated away
    if (target) target.innerHTML = html;
  }

  /* ---------- Organiser: coordinator assignment status ---------- */

  function statusPlaceholder() {
    return `<div class="notice" id="eventAssignmentStatus"><strong>Event Coordinator</strong><span class="muted">Checking coordinator assignment…</span></div>`;
  }

  async function loadAssignmentStatus(eventId) {
    let message;
    try {
        const data = await apiGet('/events/' + encodeURIComponent(eventId));
        if (!data.coordinator_assigned) {
            message = 'Awaiting Event Coordinator assignment.';
        } else if (data.coordinator_name) {
            message = `${data.coordinator_name} has been assigned as the Event Coordinator.`;
        } else {
            message = 'An Event Coordinator has been assigned to this event.';
        }
    } catch (error) {
      message = error.message;
    }
    const target = document.getElementById('eventAssignmentStatus');
    if (target) target.innerHTML = `<strong>Event Coordinator</strong><span class="muted">${escapeHtml(message)}</span>`;
  }

  /* ---------- Hook into app.js rendering without editing app.js ---------- */

  function registerPages() {
    if (typeof pages === 'undefined') return;

    // Coordinator "Assigned events" page.
    pages.coordinator.assignments = () =>
      pageHead('Assigned events', 'Events assigned to your account.') + assignedEventsPanel();

    // Organiser event workspace: insert the status box at the start of the panel.
    // The "event unavailable" view uses `panel empty-state`, so it is left unchanged.
    const originalManage = pages.organiser.manage;
    pages.organiser.manage = function () {
      const html = originalManage();
      const marker = '<section class="panel">';
      const at = html.indexOf(marker);
      if (at === -1) return html;
      const insertAt = at + marker.length;
      return html.slice(0, insertAt) + statusPlaceholder() + html.slice(insertAt);
    };
  }

  function loadForCurrentPage() {
    if (document.getElementById('assignedEventsList')) loadAssignedEvents();

    const statusBox = document.getElementById('eventAssignmentStatus');
    if (statusBox) {
      const event = authorisedEvents[selectedEventIndex];
      const eventId = event && eventIdentifier(event);
      if (eventId) loadAssignmentStatus(eventId);
      else statusBox.remove();
    }
  }

  function watchRenders() {
    const mainContent = document.getElementById('mainContent');
    if (!mainContent) return;
    // renderPage() replaces #mainContent's children; our own updates are deeper, so they don't retrigger this.
    new MutationObserver(loadForCurrentPage).observe(mainContent, { childList: true });
  }

  registerPages();
  watchRenders();
})();