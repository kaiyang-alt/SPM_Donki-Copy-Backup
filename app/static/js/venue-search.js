// Story-specific venue search UI using the existing ConnectSphere components.
let venueSearchResults = null;
let venueSearchLimitations = [];
if (!roles.coordinator.nav.some(item => item[2] === 'venueSearch')) {
  roles.coordinator.nav.splice(2, 0, ['⌖', 'Find Venues', 'venueSearch']);
}
pages.coordinator.venueSearch = venueSearchPage;

function venueSearchPage() {
  const results = venueSearchResults === null ? '' : venueSearchResults.length
    ? `<div class="event-grid" style="margin-top:20px">${venueSearchResults.map(venue => `<article class="event-card"><span class="status confirmed">Available for full period</span><h3>${escapeHtml(venue.name || 'Unnamed venue')}</h3><p class="muted">${escapeHtml(venue.location || '')}</p><div class="equipment"><span>${escapeHtml(venue.layout)} capacity</span><strong>${escapeHtml(venue.layout_capacity)}</strong></div><div class="equipment"><span>Facilities</span><strong>${escapeHtml(venue.facilities.join(', '))}</strong></div><p class="muted">${escapeHtml(venueDurationText(venue))}</p><div class="muted">Scheduled: ${escapeHtml(formatVenuePeriod(venue.available_start, venue.available_end))}</div><div class="muted">Occupied: ${escapeHtml(formatVenuePeriod(venue.occupied_start, venue.occupied_end))}</div></article>`).join('')}</div>`
    : '<section class="panel empty-state" style="margin-top:20px"><h3>No suitable venues found.</h3><p class="muted">Change the criteria above and search again.</p></section>';
  return pageHead('Find suitable venues', 'Search active venues by time, layout, capacity, and facilities.') +
    `<section class="panel"><form id="venueSearchForm"><div class="form-grid"><div class="field"><label for="venueStart">Start date and time</label><input id="venueStart" name="start" type="datetime-local" required></div><div class="field"><label for="venueEnd">End date and time</label><input id="venueEnd" name="end" type="datetime-local" required></div><div class="field"><label for="venueGuests">Guest count</label><input id="venueGuests" name="guest_count" type="number" min="1" step="1" required></div><div class="field"><label for="venueLayout">Room layout</label><input id="venueLayout" name="layout" placeholder="e.g. Theatre" required></div><div class="field full"><label for="venueFacilities">Required facilities</label><input id="venueFacilities" name="facilities" placeholder="e.g. Projector, Sound system" required><span class="muted">Separate multiple facilities with commas.</span></div></div><p class="form-error" id="venueSearchError" role="alert" aria-live="polite"></p><div class="form-actions"><button class="btn btn-primary" type="submit">Search availability</button></div></form></section>${venueSearchLimitations.length ? '<section class="panel notice"><strong>Availability assessment is incomplete</strong><p>Some venues require configuration, authoritative booking visibility or B2 hold validity. These venues are not offered as free.</p></section>' : ''}${results}`;
}

function formatVenuePeriod(start, end) {
  return `${new Date(start).toLocaleString()} to ${new Date(end).toLocaleString()}`;
}

document.getElementById('mainContent').addEventListener('submit', async event => {
  if (event.target.id !== 'venueSearchForm') return;
  event.preventDefault();
  const form = event.target;
  const error = document.getElementById('venueSearchError');
  const button = form.querySelector('button[type="submit"]');
  const facilities = form.elements.facilities.value.split(',').map(item => item.trim()).filter(Boolean);
  error.textContent = ''; button.disabled = true;
  try {
    const response = await fetch('/api/venues/search', {method: 'POST', headers: {
      'Content-Type': 'application/json', Authorization: `Bearer ${authSession.access_token}`}, body: JSON.stringify({
      start: new Date(form.elements.start.value).toISOString(),
      end: new Date(form.elements.end.value).toISOString(),
      guest_count: Number(form.elements.guest_count.value),
      layout: form.elements.layout.value, facilities
    })});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to search venues.');
    venueSearchResults = data.venues;
    venueSearchLimitations = data.assessment_limitations || [];
    const criteria = Object.fromEntries(new FormData(form));
    renderPage();
    const next = document.getElementById('venueSearchForm');
    Object.entries(criteria).forEach(([name, value]) => { if (next.elements[name]) next.elements[name].value = value; });
  } catch (requestError) { error.textContent = requestError.message; button.disabled = false; }
});
