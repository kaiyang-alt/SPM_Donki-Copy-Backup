function formatDateTime(value) {
  if (!value) return '';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);

  return new Intl.DateTimeFormat('en-SG', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Singapore'
  }).format(parsed);
}

function coordinatorEventRows() {
  if (!bookingContext.events.length) {
    return `<div class="empty-state">
      <h3>No planning events</h3>
      <p class="muted">No assigned events are currently eligible for venue booking.</p>
    </div>`;
  }

  return bookingContext.events.map(event => `
    <div class="list-row">
      <div class="date-tile">▣</div>
      <div>
        <h4>${escapeHtml(eventName(event))}</h4>
        <div class="muted">
          Expected attendance: ${escapeHtml(event.expected_attendance ?? 'Not specified')}
          · ${escapeHtml(event.status)}
        </div>
      </div>
      <button class="btn btn-soft btn-small" onclick="go('venuebooking')">
        Venue booking
      </button>
    </div>
  `).join('');
}

function bookingDisplayStatus(status) {
  const labels = {
    requested: 'Pending Venue Approval',
    tentative: 'Pending Venue Approval',
    confirmed: 'Confirmed',
    rejected: 'Rejected',
    cancelled: 'Cancelled'
  };
  return labels[status] || status;
}

function bookingStatusClass(status) {
  if (status === 'confirmed') return 'confirmed';
  if (status === 'rejected' || status === 'cancelled') return 'issue';
  return 'pending';
}

function coordinatorBookingRows() {
  if (!bookingContext.bookings.length) {
    return `<div class="empty-state">
      <h3>No venue requests</h3>
      <p class="muted">Submit a venue request for an assigned planning event.</p>
    </div>`;
  }

  return bookingContext.bookings.map(booking => {
    const event = bookingContext.events.find(
      item => item.event_id === booking.event_id
    );
    const venue = booking.venue || bookingContext.venues.find(
      item => item.venue_id === booking.venue_id
    ) || {};

    return `
      <div class="list-row">
        <div class="date-tile">⌖</div>
        <div>
          <h4>${escapeHtml(event ? eventName(event) : booking.event_id)}</h4>
          <div class="muted">
            ${escapeHtml(venue.name || booking.venue_id)}
            · ${escapeHtml(formatDateTime(booking.requested_start))}
            – ${escapeHtml(formatDateTime(booking.requested_end))}
            <br>Layout: ${escapeHtml(booking.setup_layout || 'Not recorded; review required')}
            ${['requested', 'tentative'].includes(booking.status) ? '<br>Pending alternative — does not reserve this venue.' : ''}
          </div>
        </div>
        <span class="status ${bookingStatusClass(booking.status)}">
          ${escapeHtml(bookingDisplayStatus(booking.status))}
        </span>
      </div>
    `;
  }).join('');
}

function layoutOptions() {
  const layouts = bookingContext.venues.flatMap(venue => (
    Array.isArray(venue.supported_layouts) ? venue.supported_layouts : []
  ));

  return [...new Set(layouts)].map(layout => `
    <option
      value="${escapeAttribute(layout)}"
      ${bookingDraft?.setup_layout === layout ? 'selected' : ''}
    >${escapeHtml(layout)}</option>
  `).join('');
}

function venueBookingPage() {
  const heading = pageHead(
    'Venue booking',
    'Submit non-blocking alternatives. Venue Staff confirms one and the remaining pending alternatives are cancelled.'
  );
  const eventOptions = bookingContext.events.map(event => `
    <option
      value="${escapeAttribute(event.event_id)}"
      ${bookingDraft?.event_id === event.event_id ? 'selected' : ''}
    >${escapeHtml(eventName(event))}</option>
  `).join('');

  if (!eventOptions) {
    return `${heading}<section class="panel empty-state">
      <h3>No eligible events</h3>
      <p class="muted">Only assigned events in planning status can request a venue.</p>
    </section>`;
  }

  const venueOptions = availableVenues.map(venue => `
    <option value="${escapeAttribute(venue.venue_id)}">
      ${escapeHtml(venue.name || venue.venue_id)}
      · Capacity ${escapeHtml(venue.capacity ?? '—')}
    </option>
  `).join('');
  const hasAvailableVenues = availableVenues.length > 0;

  return `${heading}
    <section class="panel">
      <div class="form-grid">
        <div class="field full">
          <label>Assigned event</label>
          <select id="bookingEvent">${eventOptions}</select>
        </div>
        <div class="field">
          <label>Date</label>
          <input id="bookingDate" type="date"
            value="${escapeAttribute(bookingDraft?.booking_date || '')}">
        </div>
        <div class="field">
          <label>Setup layout</label>
          <select id="bookingLayout">
            <option value="">Select layout</option>
            ${layoutOptions()}
          </select>
        </div>
        <div class="field">
          <label>Start time</label>
          <input id="bookingStart" type="time"
            value="${escapeAttribute(bookingDraft?.start_time || '')}">
        </div>
        <div class="field">
          <label>End time</label>
          <input id="bookingEnd" type="time"
            value="${escapeAttribute(bookingDraft?.end_time || '')}">
        </div>
        <div class="field full">
          <label>Available venue</label>
          <select id="bookingVenue" ${hasAvailableVenues ? '' : 'disabled'}>
            <option value="">
              ${hasAvailableVenues ? 'Select an available venue' : 'Check availability first'}
            </option>
            ${venueOptions}
          </select>
        </div>
      </div>
      <p class="form-error" id="bookingError" role="alert" aria-live="polite"></p>
      <div class="form-actions">
        <button class="btn btn-outline" onclick="checkVenueAvailability()">
          Check availability
        </button>
        <button class="btn btn-primary" onclick="submitVenueBooking()"
          ${hasAvailableVenues ? '' : 'disabled'}>
          Submit booking request
        </button>
      </div>
    </section>
    <section class="panel" style="margin-top:20px">
      <div class="panel-head"><h2>Saved venue requests</h2></div>
      ${coordinatorBookingRows()}
    </section>`;
}

function readBookingForm() {
  return {
    event_id: document.getElementById('bookingEvent')?.value || '',
    booking_date: document.getElementById('bookingDate')?.value || '',
    start_time: document.getElementById('bookingStart')?.value || '',
    end_time: document.getElementById('bookingEnd')?.value || '',
    setup_layout: document.getElementById('bookingLayout')?.value || ''
  };
}

async function checkVenueAvailability() {
  bookingDraft = readBookingForm();
  const error = document.getElementById('bookingError');
  error.textContent = '';

  try {
    const response = await authenticatedFetch('/api/venue-bookings/availability', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(bookingDraft)
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to check venue availability.');
    }

    availableVenues = data.venues || [];
    renderPage();
    if (!availableVenues.length) {
      document.getElementById('bookingError').textContent =
        'No venues match the selected capacity, layout, and time slot.';
    }
  } catch (requestError) {
    availableVenues = [];
    error.textContent = requestError.message;
  }
}

async function submitVenueBooking() {
  const error = document.getElementById('bookingError');
  const venueId = document.getElementById('bookingVenue')?.value || '';
  if (!venueId) {
    error.textContent = 'Select an available venue.';
    return;
  }
  const currentDraft = readBookingForm();
  if (!bookingDraft || Object.keys(currentDraft).some(key => currentDraft[key] !== bookingDraft[key])) {
    error.textContent = 'Check availability again after changing the event, period or layout.';
    return;
  }

  error.textContent = '';
  try {
    const response = await authenticatedFetch('/api/venue-bookings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...bookingDraft, venue_id: venueId})
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to submit the venue booking request.');
    }

    await loadVenueBookingContext();
    bookingDraft = null;
    availableVenues = [];
    renderPage();
    toast(
      data.warning
        ? 'Booking saved; notification unavailable.'
        : 'Venue booking request submitted.'
    );
  } catch (requestError) {
    error.textContent = requestError.message;
  }
}

function venueRequestRows() {
  if (!venueRequests.length) {
    return `<div class="empty-state">
      <h3>No booking requests</h3>
      <p class="muted">There are no venue requests visible to this account.</p>
    </div>`;
  }

  return venueRequests.map(booking => {
    const event = booking.event || {};
    const venue = booking.venue || {};
    const isPending = ['requested', 'tentative'].includes(booking.status);
    const decision = booking.decision_reason
      ? `<br>${escapeHtml(booking.decision_reason)}`
      : '';
    const actions = isPending
      ? `<button class="btn btn-outline btn-small"
           onclick="rejectVenueBooking('${escapeAttribute(booking.booking_id)}')">
           Reject
         </button>
         <button class="btn btn-primary btn-small"
           onclick="approveVenueBooking('${escapeAttribute(booking.booking_id)}')">
           Approve
         </button>`
      : `<span class="status ${bookingStatusClass(booking.status)}">
           ${escapeHtml(bookingDisplayStatus(booking.status))}
         </span>`;

    return `<div class="list-row">
      <div class="date-tile">⌖</div>
      <div>
        <h4>${escapeHtml(event.name || booking.event_id)}</h4>
        <div class="muted">
          ${escapeHtml(venue.name || booking.venue_id)}
          · ${escapeHtml(formatDateTime(booking.requested_start))}
          –${escapeHtml(formatDateTime(booking.requested_end))}
          <br>Layout: ${escapeHtml(booking.setup_layout || 'Not recorded; review required')}
          ${isPending ? '<br>Non-blocking alternative; confirmation reserves the venue.' : ''}
          ${decision}
        </div>
      </div>
      <div class="actions">${actions}</div>
    </div>`;
  }).join('');
}

async function decideVenueBooking(bookingId, action, payload) {
  const pastTense = action === 'approve' ? 'approved' : 'rejected';
  const options = {method: 'POST'};
  if (payload) {
    options.headers = {'Content-Type': 'application/json'};
    options.body = JSON.stringify(payload);
  }

  const response = await authenticatedFetch(
    `/api/venue-bookings/${encodeURIComponent(bookingId)}/${action}`,
    options
  );
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Unable to ${action} booking.`);
  }

  await loadVenueStaffData();
  renderPage();
  toast(
    data.warning
      ? `Booking ${pastTense}; notification unavailable.`
      : action === 'approve' ? 'Venue confirmed; remaining pending alternatives cancelled.' : `Booking ${pastTense}.`
  );
}

async function approveVenueBooking(bookingId) {
  try {
    await decideVenueBooking(bookingId, 'approve');
  } catch (error) {
    toast(error.message);
  }
}

async function rejectVenueBooking(bookingId) {
  const reason = window.prompt('Reason for rejection:', '');
  if (reason === null) return;

  const alternativeInput = window.prompt(
    'Suggested alternative venue IDs, separated by commas (optional):',
    ''
  ) || '';
  const alternatives = alternativeInput
    .split(',')
    .map(value => value.trim())
    .filter(Boolean);

  try {
    await decideVenueBooking(bookingId, 'reject', {
      reason,
      alternative_venue_ids: alternatives
    });
  } catch (error) {
    toast(error.message);
  }
}

function scheduleRows() {
  if (!selectedSchedule) return '';

  const items = [
    ...(selectedSchedule.bookings_and_holds || []),
    ...(selectedSchedule.maintenance_blocks || [])
  ];
  if (!items.length) return '<div class="empty-state">No scheduled items.</div>';

  return items.map(item => `
    <div class="list-row">
      <div class="date-tile">⌖</div>
      <div>
        <h4>${escapeHtml(bookingDisplayStatus(item.status) || 'Venue block')}</h4>
        <div class="muted">
          ${escapeHtml(formatDateTime(item.requested_start || item.start_datetime))}
          –${escapeHtml(formatDateTime(item.requested_end || item.end_datetime))}
          ${['requested', 'tentative'].includes(item.status) ? '<br>Non-blocking alternative' : ''}
        </div>
      </div>
    </div>
  `).join('');
}

function venueSchedulePage() {
  const venueOptions = venueStaffVenues.map(venue => `
    <option value="${escapeAttribute(venue.venue_id)}">
      ${escapeHtml(venue.name || venue.venue_id)}
    </option>
  `).join('');

  return `${pageHead(
    'Venue schedule',
    'Review holds and create operational blackout periods.'
  )}
    <section class="panel">
      <div class="form-grid">
        <div class="field full">
          <label>Venue</label>
          <select id="scheduleVenue">${venueOptions}</select>
        </div>
        <div class="field">
          <label>Block date</label>
          <input id="blockDate" type="date">
        </div>
        <div class="field">
          <label>Reason</label>
          <input id="blockReason" placeholder="Maintenance">
        </div>
        <div class="field">
          <label>Start time</label>
          <input id="blockStart" type="time">
        </div>
        <div class="field">
          <label>End time</label>
          <input id="blockEnd" type="time">
        </div>
      </div>
      <p class="form-error" id="scheduleError"></p>
      <div class="form-actions">
        <button class="btn btn-outline" onclick="loadVenueSchedule()">
          Load schedule
        </button>
        <button class="btn btn-primary" onclick="createVenueBlock()">
          Create venue block
        </button>
      </div>
    </section>
    ${selectedSchedule ? `<section class="panel" style="margin-top:20px">
      ${scheduleRows()}
    </section>` : ''}`;
}

async function loadVenueSchedule() {
  const venueId = document.getElementById('scheduleVenue')?.value;
  const error = document.getElementById('scheduleError');

  try {
    const response = await authenticatedFetch(
      `/api/venues/${encodeURIComponent(venueId)}/schedule`
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to load schedule.');
    }

    selectedSchedule = data.schedule;
    renderPage();
  } catch (requestError) {
    error.textContent = requestError.message;
  }
}

async function createVenueBlock() {
  const venueId = document.getElementById('scheduleVenue')?.value;
  const error = document.getElementById('scheduleError');
  const payload = {
    block_date: document.getElementById('blockDate')?.value || '',
    start_time: document.getElementById('blockStart')?.value || '',
    end_time: document.getElementById('blockEnd')?.value || '',
    reason: document.getElementById('blockReason')?.value || ''
  };

  try {
    const response = await authenticatedFetch(
      `/api/venues/${encodeURIComponent(venueId)}/block`,
      {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unable to create venue block.');
    }

    toast('Venue block created.');
    await loadVenueSchedule();
  } catch (requestError) {
    error.textContent = requestError.message;
  }
}
