// Story-specific review UI, using the shared panel, form and navigation patterns.
let reviewData = null;
const reviewLabels = {changes_requested: 'Clarification Required', planning: 'Planning', requested: 'Pending review'};
const reviewFields = [
  ['name', 'Event name'], ['purpose', 'Purpose'], ['description', 'Event requirements / description'],
  ['preferred_start_datetime', 'Preferred start'], ['preferred_end_datetime', 'Preferred end'],
  ['expected_attendance', 'Expected attendance'], ['venue_requirements', 'Venue requirements'],
  ['accessibility_needs', 'Accessibility needs'], ['layout_requirements', 'Layout requirements'],
  ['technical_requirements', 'Requested equipment / technical requirements']
];

async function reviewApi(path, payload) {
  if (!authSession) throw new Error('Please log in first.');
  const response = await fetch('/api/event-reviews' + path, {
    method: payload ? 'POST' : 'GET',
    headers: {Authorization: `Bearer ${authSession.access_token}`, 'Content-Type': 'application/json'},
    ...(payload ? {body: JSON.stringify(payload)} : {})
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to load the request.');
  return data;
}

const baselineSetRole = setRole;
setRole = function(role) {
  const sessionRoles = authSession?.roles || (authSession?.role ? [authSession.role] : []);
  if (role === 'coordinator' && !sessionRoles.includes('event_coordinator')) {
    showLogin();
    return;
  }
  if (role === 'organiser' && !sessionRoles.includes('event_organiser')) {
    showLogin();
    return;
  }
  reviewData = null;
  if (role === 'coordinator') authorisedEvents = [];
  baselineSetRole(role);
  if (role === 'coordinator') {
    document.getElementById('userName').textContent = authSession.email;
    document.getElementById('userInitial').textContent = initials(authSession.email);
    document.getElementById('logoutButton').classList.remove('hidden');
    refreshReviewList();
  }
};

async function refreshReviewList() {
  try {
    const data = await reviewApi('');
    if (currentRole !== 'coordinator') return;
    authorisedEvents = data.events;
    renderPage();
  } catch (error) { toast(error.message); }
}

function reviewList() {
  return pageHead('Assigned event requests', 'Review requirements and request clarification.') +
    `<section class="panel"><button class="btn btn-soft" onclick="refreshReviewList()">Refresh requests</button>${authorisedEvents.length ? authorisedEvents.map(event =>
      `<div class="list-row"><div><h4>${escapeHtml(eventName(event))}</h4><span class="muted">${escapeHtml(reviewLabels[event.status] || event.status)}</span></div><button class="btn btn-soft" data-review-id="${escapeAttribute(eventIdentifier(event))}">Review request</button></div>`
    ).join('') : '<p class="muted">No assigned requests available.</p>'}</section>`;
}
pages.coordinator.dashboard = reviewList;
pages.coordinator.assignments = reviewList;
pages.coordinator.review = reviewPage;
pages.organiser.review = reviewPage;

const baselineGo = go;
go = function(page) {
  baselineGo(page);
  if (currentRole === 'organiser' && page === 'events' && authSession) {
    loadAuthorisedEvents().then(() => {
      if (currentRole === 'organiser' && currentPage === 'events') renderPage();
    }).catch(error => toast(error.message));
  }
};

document.querySelector('#roleSelect option[value="coordinator"]').textContent = 'Event Coordinator';

const baselineOpenManagedEvent = openManagedEvent;
openManagedEvent = function(index) {
  const event = authorisedEvents[index];
  if (event?.status === 'changes_requested') { openReview(eventIdentifier(event)); return; }
  baselineOpenManagedEvent(index);
};

async function openReview(id) {
  try {
    const role = currentRole;
    const data = await reviewApi('/' + encodeURIComponent(id));
    if (role !== currentRole || !authSession) return;
    reviewData = data;
    currentPage = 'review';
    renderNav(); renderPage();
  } catch (error) { toast(error.message); }
}

function reviewPage() {
  if (!reviewData) return pageHead('Request unavailable', 'Refresh your events and try again.');
  const {event, coordinator_name: coordinatorName, actions, equipment} = reviewData;
  const coordinator = currentRole === 'coordinator';
  const editable = coordinator ? ['requested', 'changes_requested'].includes(event.status) : event.status === 'changes_requested';
  const history = actions.filter(action => ['clarification_requested', 'clarification_provided', 'review_completed'].includes(action.action_type));
  return pageHead('Review event request', reviewLabels[event.status] || event.status) +
    `<section class="panel"><h2>${escapeHtml(event.name)}</h2><div class="equipment"><span>Assigned Event Coordinator</span><strong>${escapeHtml(coordinatorName || 'Not assigned')}</strong></div>${reviewFields.map(([key,label]) => `<div class="equipment"><span>${label}</span><strong>${escapeHtml(event[key] ?? 'Not provided')}</strong></div>`).join('')}
    <div class="equipment"><span>Technical support required</span><strong>${event.technical_support_required == null ? 'Not provided' : event.technical_support_required ? 'Yes' : 'No'}</strong></div>
    <h3>Equipment requests</h3>${equipment.length ? equipment.map(item => `<div class="equipment"><span>${escapeHtml(item.equipment?.name || 'Equipment')} · ${escapeHtml(item.status)}</span><strong>${escapeHtml(item.quantity_requested)} · ${escapeHtml(item.technical_requirements || '')}</strong></div>`).join('') : '<p class="muted">No equipment reservations recorded. Review the technical requirements above.</p>'}
    <h3>Clarification history</h3>${history.length ? history.map(action => `<div class="notice"><strong>${escapeHtml(action.action_type.replaceAll('_',' '))} · ${escapeHtml(action.created_at || '')}</strong><span>${escapeHtml(action.details)}</span></div>`).join('') : '<p class="muted">No clarification messages.</p>'}
    ${editable ? `<form id="reviewForm"><div class="form-grid">${coordinator ? `<div class="field full"><label for="reviewStatus">Review decision</label><select id="reviewStatus" name="status"><option value="changes_requested">Require clarification</option><option value="planning">Reviewed — move to Planning</option></select></div>` : reviewFields.map(([key,label]) => `<div class="field full"><label for="amend-${key}">${label}</label><input id="amend-${key}" name="${key}" ${key === 'expected_attendance' ? 'type="number" step="1"' : ''} value="${escapeAttribute(event[key] ?? '')}"></div>`).join('')}
    <div class="field full"><label for="reviewMessage">${coordinator ? 'Clarification message (required when requesting clarification)' : 'Clarification response'}</label><textarea id="reviewMessage" name="message" ${coordinator ? '' : 'required'}></textarea></div></div><p id="reviewError" class="form-error" role="alert"></p><div class="form-actions"><button class="btn btn-primary" type="submit">${coordinator ? 'Save review decision' : 'Submit clarification / amendments'}</button></div></form>` : '<p class="muted">This request is read-only in its current status.</p>'}
    <div class="form-actions"><button class="btn btn-soft" onclick="go(currentRole==='coordinator'?'assignments':'events')">Back to events</button></div></section>`;
}

document.getElementById('mainContent').addEventListener('click', event => {
  const button = event.target.closest('[data-review-id]');
  if (button) openReview(button.dataset.reviewId);
});
document.getElementById('mainContent').addEventListener('submit', async event => {
  if (event.target.id !== 'reviewForm') return;
  event.preventDefault();
  const form = event.target;
  const error = document.getElementById('reviewError');
  const button = form.querySelector('button[type="submit"]');
  const coordinator = currentRole === 'coordinator';
  const payload = {message: form.elements.message.value};
  if (coordinator) payload.status = form.elements.status.value;
  else {
    payload.amendments = {};
    for (const [key] of reviewFields) {
      const value = form.elements.namedItem(key).value;
      const next = key === 'expected_attendance' ? (value === '' ? null : Number(value)) : value;
      if (next !== (reviewData.event[key] ?? (key === 'expected_attendance' ? null : ''))) payload.amendments[key] = next;
    }
  }
  button.disabled = true; error.textContent = '';
  try {
    const id = eventIdentifier(reviewData.event);
    const result = await reviewApi('/' + encodeURIComponent(id) + (coordinator ? '/decision' : '/response'), payload);
    const index = authorisedEvents.findIndex(item => eventIdentifier(item) === id);
    if (index >= 0) authorisedEvents[index] = result.event;
    await openReview(id);
    toast(coordinator ? 'Review decision saved.' : 'Clarification submitted for coordinator review.');
  } catch (requestError) { error.textContent = requestError.message; button.disabled = false; }
});
