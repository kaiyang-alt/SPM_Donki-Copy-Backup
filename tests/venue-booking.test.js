const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/js/venue-booking.js', 'utf8');

function fixture() {
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  const elements = Object.fromEntries(Object.entries({
    bookingEvent: 'event-1', bookingVenue: 'venue-1', bookingDate: '2026-11-20',
    bookingStart: '09:00', bookingEnd: '12:00', bookingLayout: 'Theatre', bookingError: ''
  }).map(([id, value]) => [id, {value, textContent: ''}]));
  const calls = [], notices = [];
  const context = {
    escapeHtml: escape, escapeAttribute: escape, eventName: event => event.name,
    pageHead: (title, subtitle) => title + subtitle,
    bookingContext: {events: [{event_id: 'event-1', name: 'Event', layout_requirements: 'Event-wide requirement'}], venues: [], bookings: []},
    bookingDraft: {event_id: 'event-1', booking_date: '2026-11-20', start_time: '09:00', end_time: '12:00', setup_layout: 'Theatre'},
    availableVenues: [{venue_id: 'venue-1'}], venueRequests: [], selectedSchedule: null,
    document: {getElementById: id => elements[id]},
    authenticatedFetch: async (url, options) => { calls.push({url, options}); return {ok: true, json: async () => ({booking: {status: 'confirmed'}})}; },
    loadVenueStaffData: async () => { context.staffReloaded = true; },
    loadVenueBookingContext: async () => { context.coordinatorReloaded = true; },
    renderPage: () => { context.rendered = true; }, toast: value => notices.push(value),
  };
  vm.runInNewContext(source, context);
  return {context, elements, calls, notices};
}

test('saved alternatives show their own layout and full period, including cancelled history', () => {
  const {context} = fixture();
  context.bookingContext.bookings = [
    {booking_id: 'a', event_id: 'event-1', venue_id: 'v1', status: 'requested', setup_layout: 'Theatre', requested_start: '2026-11-20T01:00:00Z', requested_end: '2026-11-20T04:00:00Z'},
    {booking_id: 'b', event_id: 'event-1', venue_id: 'v2', status: 'cancelled', setup_layout: 'Classroom', requested_start: '2026-11-21T05:00:00Z', requested_end: '2026-11-21T08:00:00Z'}
  ];
  const html = context.coordinatorBookingRows();
  assert.match(html, /Theatre/);
  assert.match(html, /Classroom/);
  assert.match(html, /12:00/);
  assert.match(html, /Cancelled/);
  assert.match(html, /does not reserve this venue/);
  assert.doesNotMatch(html, /Event-wide requirement/);
});

test('Venue Staff sees booking-specific layout and escaped metadata', () => {
  const {context} = fixture();
  context.venueRequests = [{booking_id: 'a', status: 'requested', setup_layout: '<img src=x>', event: {name: 'Event', layout_requirements: 'Wrong global layout'}, venue: {name: 'Room'}}];
  const html = context.venueRequestRows();
  assert.match(html, /&lt;img src=x&gt;/);
  assert.match(html, /Non-blocking alternative/);
  assert.doesNotMatch(html, /Wrong global layout|<img/);
});

test('calendar distinguishes pending alternatives from confirmed reservations', () => {
  const {context} = fixture();
  context.selectedSchedule = {bookings_and_holds: [{status: 'tentative'}, {status: 'confirmed'}], maintenance_blocks: []};
  const html = context.scheduleRows();
  assert.match(html, /Pending Venue Approval/);
  assert.match(html, /Non-blocking alternative/);
  assert.match(html, /Confirmed/);
});

test('confirmation calls the existing approval endpoint and reloads saved outcomes', async () => {
  const {context, calls, notices} = fixture();
  await context.decideVenueBooking('booking-1', 'approve');
  assert.equal(calls[0].url, '/api/venue-bookings/booking-1/approve');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(context.staffReloaded, true);
  assert.match(notices[0], /remaining pending alternatives cancelled/);
});

test('failed confirmation cannot show success or reload optimistic state', async () => {
  const {context, notices} = fixture();
  context.authenticatedFetch = async () => ({ok: false, json: async () => ({error: 'Venue is unavailable'})});
  await assert.rejects(context.decideVenueBooking('booking-1', 'approve'), /unavailable/);
  assert.equal(context.staffReloaded, undefined);
  assert.equal(notices.length, 0);
});

test('changing a checked period blocks submission until availability is checked again', async () => {
  const {context, elements, calls} = fixture();
  elements.bookingStart.value = '10:00';
  await context.submitVenueBooking();
  assert.equal(calls.length, 0);
  assert.match(elements.bookingError.textContent, /Check availability again/);
});

test('submission sends the checked alternative period/layout and refreshes the list', async () => {
  const {context, calls} = fixture();
  await context.submitVenueBooking();
  assert.equal(calls[0].url, '/api/venue-bookings');
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    event_id: 'event-1', venue_id: 'venue-1', booking_date: '2026-11-20',
    start_time: '09:00', end_time: '12:00', setup_layout: 'Theatre'
  });
  assert.equal(context.coordinatorReloaded, true);
  assert.equal(context.bookingDraft, null);
});
