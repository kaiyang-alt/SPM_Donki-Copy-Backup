// Story-specific venue search UI using the existing ConnectSphere components.
let venueSearchResults = null;
let venueSearchCriteria = {venue_count: 1, setup_minutes: 0, turnaround_minutes: 0, venue_requirements: [{}]};
if (!roles.coordinator.nav.some(item => item[2] === 'venueSearch')) {
  roles.coordinator.nav.splice(2, 0, ['⌖', 'Find Venues', 'venueSearch']);
}
pages.coordinator.venueSearch = venueSearchPage;

function venueSearchPage() {
  const results = venueSearchResults === null ? '' : venueSearchResults.length
    ? `<div class="event-grid" style="margin-top:20px">${venueSearchResults.map(renderVenueSearchResult).join('')}</div>`
    : '<section class="panel empty-state" style="margin-top:20px"><h3>No suitable venues found.</h3><p class="muted">Change the criteria above and search again.</p></section>';
  return pageHead('Find suitable venues', 'Search active venues by time, layout, capacity, and facilities.') +
    `<section class="panel"><form id="venueSearchForm"><div class="form-grid"><div class="field"><label for="venueStart">Event start date and time</label><input id="venueStart" name="start" type="datetime-local" value="${escapeAttribute(venueSearchCriteria.start || '')}" required></div><div class="field"><label for="venueEnd">Event end date and time</label><input id="venueEnd" name="end" type="datetime-local" value="${escapeAttribute(venueSearchCriteria.end || '')}" required></div><div class="field"><label for="venueSetup">Setup time (minutes)</label><input id="venueSetup" name="setup_minutes" type="number" min="0" step="1" value="${escapeAttribute(venueSearchCriteria.setup_minutes ?? 0)}" required></div><div class="field"><label for="venueTurnaround">Turnaround time (minutes)</label><input id="venueTurnaround" name="turnaround_minutes" type="number" min="0" step="1" value="${escapeAttribute(venueSearchCriteria.turnaround_minutes ?? 0)}" required></div><div class="field"><label for="venueCount">Number of venues</label><input id="venueCount" name="venue_count" type="number" min="1" step="1" value="${escapeAttribute(venueSearchCriteria.venue_count || 1)}" required></div></div><div id="venueRequirementFields">${venueRequirementFields(venueSearchCriteria.venue_count || 1, venueSearchCriteria.venue_requirements)}</div><p class="form-error" id="venueSearchError" role="alert" aria-live="polite"></p><div class="form-actions"><button class="btn btn-primary" type="submit">Search availability</button></div></form></section>${results}`;
}

function formatVenuePeriod(start, end) {
  return `${new Date(start).toLocaleString()} to ${new Date(end).toLocaleString()}`;
}

function venueRequirementFields(count, requirements = []) {
  return Array.from({length: count}, (_, index) => {
    const requirement = requirements[index] || {};
    return `<fieldset class="panel venue-requirement" data-venue-requirement style="margin-top:16px"><legend><strong>Venue ${index + 1} requirements</strong></legend><div class="form-grid"><div class="field"><label>Guest count</label><input name="requirement_guest_count" type="number" min="1" step="1" value="${escapeAttribute(requirement.guest_count ?? '')}" required></div><div class="field"><label>Room layout</label><input name="requirement_layout" value="${escapeAttribute(requirement.layout || '')}" placeholder="e.g. Theatre" required></div><div class="field full"><label>Required facilities</label><input name="requirement_facilities" value="${escapeAttribute((requirement.facilities || []).join(', '))}" placeholder="e.g. Projector, Sound system" required><span class="muted">Separate multiple facilities with commas.</span></div></div></fieldset>`;
  }).join('');
}

function venueTiming(venue) {
  return `<div class="equipment"><span>Setup time</span><strong>${escapeHtml(venue.setup_minutes)} minutes</strong></div><div class="equipment"><span>Event period</span><strong>${escapeHtml(formatVenuePeriod(venue.event_start, venue.event_end))}</strong></div><div class="equipment"><span>Turnaround time</span><strong>${escapeHtml(venue.turnaround_minutes)} minutes</strong></div><div class="equipment"><span>Complete occupied period</span><strong>${escapeHtml(formatVenuePeriod(venue.occupied_start, venue.occupied_end))}</strong></div><div class="equipment"><span>Temporary unavailability</span><strong>${venue.temporary_unavailability?.length ? escapeHtml(venue.temporary_unavailability.join(', ')) : 'None during occupied period'}</strong></div>`;
}

function venueCard(venue) {
  return `<div><h3>${escapeHtml(venue.name || 'Unnamed venue')}</h3><p class="muted">${escapeHtml(venue.location || '')}</p><div class="equipment"><span>${escapeHtml(venue.layout)} capacity</span><strong>${escapeHtml(venue.layout_capacity)}</strong></div><div class="equipment"><span>Facilities</span><strong>${escapeHtml(venue.facilities.join(', '))}</strong></div>${venueTiming(venue)}</div>`;
}

function renderVenueSearchResult(result) {
  if (Array.isArray(result.venues)) return `<article class="event-card"><span class="status confirmed">Suitable venue combination</span>${result.venues.map((venue, index) => `<section><p class="muted">Venue ${index + 1}</p>${venueCard(venue)}</section>`).join('')}</article>`;
  return `<article class="event-card"><span class="status confirmed">Available for complete occupied period</span>${venueCard(result)}</article>`;
}

document.getElementById('mainContent').addEventListener('change', event => {
  if (event.target.id !== 'venueCount') return;
  const count = Math.max(1, Number(event.target.value) || 1);
  document.getElementById('venueRequirementFields').innerHTML = venueRequirementFields(count);
});

document.getElementById('mainContent').addEventListener('submit', async event => {
  if (event.target.id !== 'venueSearchForm') return;
  event.preventDefault();
  const form = event.target;
  const error = document.getElementById('venueSearchError');
  const button = form.querySelector('button[type="submit"]');
  const requirements = [...form.querySelectorAll('[data-venue-requirement]')].map(section => ({
    guest_count: Number(section.querySelector('[name="requirement_guest_count"]').value),
    layout: section.querySelector('[name="requirement_layout"]').value,
    facilities: section.querySelector('[name="requirement_facilities"]').value.split(',').map(item => item.trim()).filter(Boolean)
  }));
  const criteria = {
    start: new Date(form.elements.start.value).toISOString(),
    end: new Date(form.elements.end.value).toISOString(),
    setup_minutes: Number(form.elements.setup_minutes.value),
    turnaround_minutes: Number(form.elements.turnaround_minutes.value),
    venue_count: Number(form.elements.venue_count.value),
    venue_requirements: requirements
  };
  error.textContent = ''; button.disabled = true;
  try {
    const response = await fetch('/api/venues/search', {method: 'POST', headers: {
      'Content-Type': 'application/json', Authorization: `Bearer ${authSession.access_token}`}, body: JSON.stringify(criteria)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to search venues.');
    venueSearchResults = data.venues;
    venueSearchCriteria = {...criteria, start: form.elements.start.value, end: form.elements.end.value};
    renderPage();
  } catch (requestError) { error.textContent = requestError.message; button.disabled = false; }
});
