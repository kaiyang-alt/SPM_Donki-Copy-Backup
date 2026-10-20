// B1 uses the shared ConnectSphere UI and caller-authenticated requests.
let bufferSession = null, bufferVenueId = null, bufferOutcome = null, bufferIntent = null;
let bufferNotices = null;
roles.venue.nav.splice(4, 0, ['◷', 'Venue durations', 'venueBuffers']);
pages.venue.venueBuffers = venueBuffersPage;
const previousCoordinatorNotificationsPage = pages.coordinator.notifications;
pages.coordinator.notifications = () => {
  resetBufferSession();
  const original = previousCoordinatorNotificationsPage ? previousCoordinatorNotificationsPage() : pageHead('Notifications', 'Venue duration conflict notices.');
  return original + `<section class="panel" style="margin-top:20px"><div class="panel-head"><h2>Venue duration conflicts</h2><button class="btn btn-outline" onclick="loadBufferNotices()">Refresh venue notices</button></div><p id="bufferNoticesError" class="form-error" role="alert"></p>${bufferNotices === null ? '<p>Refresh to load your persisted venue notices.</p>' : bufferNotices.length ? bufferNotices.map(item => `<div class="notice"><strong>${escapeHtml(item.message)}</strong><span>Event: ${escapeHtml(item.event_id)}</span><span>${escapeHtml(formatDateTime(item.created_at))}</span></div>`).join('') : '<p>No venue duration notices.</p>'}</section>`;
};

async function loadBufferNotices() {
  const requestSession = authSession;
  try {
    const response = await authenticatedFetch('/api/venue-buffer-notifications');
    const data = await response.json();
    if (requestSession !== authSession) return;
    if (!response.ok) throw new Error(data.error || 'Unable to read venue notices.');
    bufferNotices = data.notifications || [];
    renderPage();
  } catch (failure) {
    const error = document.getElementById('bufferNoticesError');
    if (error && requestSession === authSession) error.textContent = failure.message;
  }
}

function resetBufferSession() {
  if (bufferSession !== authSession) {
    bufferSession = authSession;
    bufferVenueId = bufferOutcome = bufferIntent = null;
    bufferNotices = null;
  }
}

function venueDurationText(venue) {
  if (venue.setup_minutes == null || venue.turnaround_minutes == null) return 'Unconfigured — occupied availability cannot be calculated.';
  return `Setup ${venue.setup_minutes} min · Turnaround ${venue.turnaround_minutes} min`;
}

function b1ReasonText(item) {
  const reasons = {
    old_configuration_unconfigured: 'The previous configuration was unconfigured.',
    hold_validity_unavailable: 'Hold validity requires B2 assessment.',
    hold_schedule_unassessable_pending_owner: 'The hold schedule requires review by its owner.',
    authoritative_booking_visibility_unavailable: 'Authoritative venue booking visibility is unavailable.',
    occupancy_read_truncated_or_unverified: 'The available booking information is incomplete.',
    configuration_required: 'Venue setup and turnaround are unconfigured.',
    configuration_decision_or_repair_required: 'Venue durations require a decision or repair.',
    booking_lifecycle_classification_required: 'Booking lifecycle classification requires owner review.',
    block_lifecycle_classification_required: 'Block lifecycle classification requires owner review.',
    confirmed_or_expanded_schedule_unassessable: 'Scheduled or occupied times require owner review.',
    active_block_interval_unresolved_under_bounded_scope: 'The active block needs an assessable bounded interval or an owner decision.',
    missing_assigned_coordinator: 'No assigned Coordinator could be found.',
    missing_event: 'The associated event could not be found.',
    assigned_coordinator_role_missing: 'The assigned person does not have the Coordinator role.'
  };
  return reasons[item.reason] || 'This arrangement requires owner review.';
}

function b1IssueList(items) {
  return `<ul>${items.map(item => `<li>${escapeHtml(b1ReasonText(item))} ${escapeHtml(item.booking_id || item.booking_ids?.join(', ') || item.event_id || item.venue_block_id || '')}</li>`).join('')}</ul>`;
}

function b1AssessmentDisplay(assessment) {
  if (!assessment) return '';
  const conflicts = assessment.conflicts || [];
  const limitations = [...(assessment.assessment_limitations || []), ...(assessment.assessment_blockers || [])];
  const exceptions = assessment.routing_exceptions || [];
  const incomplete = assessment.assessment_complete === false || assessment.authoritative_assessment_complete === false || (assessment.assessment_blockers || []).length > 0;
  return `<div aria-live="polite">
    ${typeof assessment.assessment_complete === 'boolean' ? `<p>Occupancy assessment: ${assessment.assessment_complete ? 'complete' : 'incomplete'}</p>` : ''}
    ${assessment.configuration_saved ? `<div class="notice"><strong>${assessment.no_op ? 'Values unchanged; no duplicate notices.' : 'Configuration saved.'}</strong><span>Recorded operation revision ${escapeHtml(assessment.configuration_revision)}. Refresh configuration for current values.</span></div>` : ''}
    ${conflicts.length ? `<h3>Occupied-period conflicts</h3>${conflicts.map(item => `<div class="notice"><strong>${escapeHtml(item.booking_id || 'Arrangement')} / ${escapeHtml(item.other_booking_id || item.venue_block_id || 'Arrangement')}</strong><span>${escapeHtml(formatDateTime(item.overlap_start))} – ${escapeHtml(formatDateTime(item.overlap_end))}</span><span>${escapeHtml(item.assessment || 'identified')}</span></div>`).join('')}` : ''}
    ${limitations.length ? `<div class="notice"><strong>${incomplete ? 'Assessment incomplete — availability is not established' : 'Assessment notes'}</strong>${b1IssueList(limitations)}</div>` : ''}
    ${assessment.notification_status === 'incomplete_routing' || exceptions.length ? `<div class="notice"><strong>Configuration saved; Coordinator notification routing is incomplete</strong><p>Follow-up is required. Repeating this operation does not deliver repair notices.</p>${b1IssueList(exceptions)}</div>` : ''}
    ${assessment.notification_status === 'persisted' ? '<p class="muted">Coordinator notices persisted.</p>' : ''}
  </div>`;
}

function venueBuffersPage() {
  resetBufferSession();
  const venue = venueStaffVenues.find(row => row.venue_id === bufferVenueId) || venueStaffVenues[0];
  if (!venue) return pageHead('Venue durations', 'Configure setup and turnaround separately.') + '<section class="panel empty-state">No venues available.</section>';
  bufferVenueId = venue.venue_id;
  return pageHead('Venue durations', 'Maintain whole-minute setup and turnaround for each venue.') + `
    <section class="panel"><form id="venueBuffersForm"><div class="form-grid">
      <div class="field full"><label for="bufferVenue">Venue</label><select id="bufferVenue" onchange="bufferVenueId=this.value;bufferOutcome=null;bufferIntent=null;renderPage()">${venueStaffVenues.map(row => `<option value="${escapeAttribute(row.venue_id)}" ${row.venue_id === bufferVenueId ? 'selected' : ''}>${escapeHtml(row.name || row.venue_id)}</option>`).join('')}</select></div>
      <div class="field full"><strong>${escapeHtml(venueDurationText(venue))}</strong><span class="muted">Revision: ${escapeHtml(venue.buffer_config_revision ?? 'Unavailable')}</span></div>
      <div class="field"><label for="bufferSetup">Setup minutes</label><input id="bufferSetup" name="setup" type="number" min="1" max="2147483647" step="1" value="${escapeAttribute(venue.setup_minutes ?? '')}" required></div>
      <div class="field"><label for="bufferTurnaround">Turnaround minutes</label><input id="bufferTurnaround" name="turnaround" type="number" min="1" max="2147483647" step="1" value="${escapeAttribute(venue.turnaround_minutes ?? '')}" required></div>
    </div><p class="muted">Zero requires a separate business decision. Existing arrangements remain for Coordinator review if a change creates conflicts.</p>
    <p class="form-error" id="bufferError" role="alert" aria-live="polite"></p><div class="form-actions"><button type="button" class="btn btn-outline" onclick="refreshVenueBuffers()">Refresh configuration</button><button type="submit" class="btn btn-primary">Save durations</button></div>
    </form></section><section class="panel" style="margin-top:20px">${b1AssessmentDisplay(bufferOutcome)}</section>`;
}

async function refreshVenueBuffers() {
  const error = document.getElementById('bufferError');
  const targetId = bufferVenueId, requestSession = authSession;
  try {
    const response = await authenticatedFetch(`/api/venues/${encodeURIComponent(targetId)}/buffers`);
    const data = await response.json();
    if (requestSession !== authSession || targetId !== bufferVenueId) return;
    if (!response.ok) throw new Error(data.error || 'Unable to read configuration.');
    Object.assign(venueStaffVenues.find(row => row.venue_id === bufferVenueId), data);
    bufferIntent = bufferOutcome = null;
    renderPage();
  } catch (failure) { error.textContent = failure.message; }
}

document.getElementById('mainContent').addEventListener('submit', async event => {
  if (event.target.id !== 'venueBuffersForm') return;
  event.preventDefault(); resetBufferSession();
  const form = event.target, error = document.getElementById('bufferError');
  const targetId = bufferVenueId, requestSession = authSession;
  const button = form.querySelector('button[type="submit"]');
  error.textContent = ''; button.disabled = true;
  try {
    const values = [form.elements.setup.value, form.elements.turnaround.value];
    if (values.some(value => !/^\d+$/.test(value))) throw new Error('Enter whole integer minutes.');
    const [setup, turnaround] = values.map(Number);
    if (setup === 0 || turnaround === 0) throw new Error('Zero duration requires a separate business decision.');
    if ([setup, turnaround].some(value => !Number.isSafeInteger(value) || value > 2147483647)) throw new Error('Minutes exceed the supported integer representation.');
    const venue = venueStaffVenues.find(row => row.venue_id === bufferVenueId), revision = venue.buffer_config_revision;
    if (!Number.isSafeInteger(revision) || revision < 0) throw new Error('Revision cannot be submitted safely. Refresh configuration or request administrator review.');
    const key = JSON.stringify([bufferVenueId, setup, turnaround, revision]);
    if (!bufferIntent || bufferIntent.key !== key) bufferIntent = {key, payload: {setup_minutes: setup, turnaround_minutes: turnaround, expected_revision: revision, operation_id: crypto.randomUUID()}};
    // Retain the exact token and intent after an unconfirmed/lost response.
    const response = await authenticatedFetch(`/api/venues/${encodeURIComponent(targetId)}/buffers`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(bufferIntent.payload)
    });
    const data = await response.json();
    if (requestSession !== authSession || targetId !== bufferVenueId) return;
    if (!response.ok) throw new Error(data.error || 'Unable to confirm save. Retry unchanged values.');
    bufferOutcome = data;
    Object.assign(venue, {setup_minutes: data.setup_minutes, turnaround_minutes: data.turnaround_minutes, buffer_config_revision: data.configuration_revision});
    // A buffer edit invalidates earlier availability/calendar snapshots.
    if (typeof selectedSchedule !== 'undefined') selectedSchedule = null;
    if (typeof availableVenues !== 'undefined') availableVenues = [];
    if (typeof venueSearchResults !== 'undefined') venueSearchResults = null;
    if (typeof venueSearchLimitations !== 'undefined') venueSearchLimitations = [];
    bufferIntent = null; renderPage();
  } catch (failure) { error.textContent = failure.message; }
  finally { button.disabled = false; }
});
