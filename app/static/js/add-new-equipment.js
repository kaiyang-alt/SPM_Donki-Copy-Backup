/* add-new-equipment: Technical Support catalogue entry, using the shared UI and session. */
(function () {
  if (!pages.technical || typeof roles === 'undefined' || !roles.technical) return;
  const API = '/api/equipment-catalogue';
  const QUANTITY_ERROR = 'Total quantity must be a whole number greater than 0.';
  let token = null, items = null, busy = false, error = '', notice = '', draft = {};
  const active = () => currentRole === 'technical' && currentPage === 'catalogue';
  const same = requestToken => requestToken === authSession?.access_token && requestToken === token;
  const render = () => { if (active()) renderPage(); };

  const textField = (name, label) => `<div class="field"><label for="equipment-${name}">${label}</label>` +
    `<input id="equipment-${name}" name="${name}" value="${escapeAttribute(draft[name] || '')}" required></div>`;

  function catalogueRow(item) {
    return `<div class="equipment"><div><h4>${escapeHtml(item.name)}</h4>` +
      `<span class="capacity">${escapeHtml(item.type)} · ${escapeHtml(item.location)}</span>` +
      `<div class="muted">${escapeHtml(item.description)}</div></div>` +
      `<span class="status ready">${escapeHtml(item.total_quantity)} units</span></div>`;
  }

  function page() {
    if (token !== authSession?.access_token) { token = authSession?.access_token; items = null; busy = false; error = ''; notice = ''; draft = {}; }
    const list = items === null ? '<p class="muted">Loading the equipment catalogue…</p>' :
      !items.length ? '<p class="muted">No active equipment is in the catalogue yet.</p>' : items.map(catalogueRow).join('');
    return pageHead('Equipment catalogue', 'Register newly acquired equipment so it is available for event planning.',
      `<button class="btn btn-soft" id="catalogueRefresh" ${busy ? 'disabled' : ''}>Refresh</button>`) +
      // novalidate: the server's error messages are shown instead of browser pop-ups.
      `<section class="panel" style="margin-bottom:20px"><h2>Add new equipment</h2><form id="addEquipmentForm" novalidate><div class="form-grid">` +
      textField('name', 'Name') + textField('type', 'Category') + textField('location', 'Location') +
      `<div class="field"><label for="equipment-total_quantity">Total quantity</label><input id="equipment-total_quantity" name="total_quantity" type="number" min="1" step="1" value="${escapeAttribute(draft.total_quantity || '')}" required></div>` +
      `<div class="field full"><label for="equipment-description">Description</label><textarea id="equipment-description" name="description" required>${escapeHtml(draft.description || '')}</textarea></div>` +
      `</div><p class="form-error" role="alert" aria-live="polite">${escapeHtml(error)}</p><p role="status">${escapeHtml(notice)}</p>` +
      `<div class="form-actions"><button class="btn btn-primary" type="submit" ${busy ? 'disabled' : ''}>Save equipment</button></div></form></section>` +
      `<section class="panel"><h2>Active catalogue</h2>${list}</section>`;
  }

  async function call(options) {
    const response = await authenticatedFetch(API, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to complete the equipment catalogue operation.');
    return data;
  }

  async function load() {
    if (busy) return;
    const requestToken = token;
    busy = true; error = ''; notice = ''; render();
    try { const data = await call({}); if (same(requestToken)) items = data.equipment; }
    catch (err) { if (same(requestToken)) { error = err.message; items = items || []; } }
    finally { if (same(requestToken)) { busy = false; render(); } }
  }

  async function save(form) {
    if (busy) return;
    const fields = form.elements;
    draft = {name: fields.name.value, type: fields.type.value, description: fields.description.value,
      location: fields.location.value, total_quantity: fields.total_quantity.value};
    // A non-numeric entry in a number input reads as '', so report it here rather than as "required".
    if (fields.total_quantity.validity.badInput) { error = QUANTITY_ERROR; notice = ''; render(); return; }
    const requestToken = token;
    busy = true; error = ''; notice = ''; render();
    try {
      const data = await call({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft)});
      if (!same(requestToken)) return;
      // Show the row the server saved, not the local draft.
      items = (items || []).concat([data.equipment]).sort((a, b) => String(a.name).localeCompare(String(b.name)));
      draft = {}; notice = `${data.equipment.name} was added to the catalogue.`;
    } catch (err) { if (same(requestToken)) error = err.message; }
    finally { if (same(requestToken)) { busy = false; render(); } }
  }

  if (!roles.technical.nav.some(item => item[2] === 'catalogue')) roles.technical.nav.push(['＋', 'Equipment Catalogue', 'catalogue']);
  pages.technical.catalogue = page;
  const original = window.renderPage;
  window.renderPage = function () {
    const result = original.apply(this, arguments);
    if (!active()) return result;
    document.getElementById('catalogueRefresh').onclick = load;
    const form = document.getElementById('addEquipmentForm');
    form.onsubmit = event => { event.preventDefault(); save(form); };
    if (items === null && !busy && !error) load();
    return result;
  };
})();