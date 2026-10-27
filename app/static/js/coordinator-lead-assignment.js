let coordinatorLeadAssignmentContext={events:[],coordinators:[]};
let lastCoordinatorLeadAssignment=null;
let coordinatorLeadReassignmentContext={events:[],coordinators:[]};
let lastCoordinatorLeadReassignment=null;
let coordinatorLeadCurrentAssignments=[];
let coordinatorLeadAssignmentDetails=null;

pages.lead={dashboard:coordinatorLeadAssignmentPage,current:coordinatorLeadCurrentAssignmentsPage};

async function loadCoordinatorLeadAssignmentContext(){
  const [assignmentResponse,reassignmentResponse,currentResponse]=await Promise.all([
    authenticatedFetch('/api/coordinator-lead/assignment-context'),
    authenticatedFetch('/api/coordinator-lead/reassignment-context'),
    authenticatedFetch('/api/coordinator-lead/current-assignments')
  ]);
  const assignmentData=await assignmentResponse.json();
  const reassignmentData=await reassignmentResponse.json();
  const currentData=await currentResponse.json();
  if(!assignmentResponse.ok)throw new Error(assignmentData.error||'Unable to load unassigned event requests.');
  if(!reassignmentResponse.ok)throw new Error(reassignmentData.error||'Unable to load current event assignments.');
  if(!currentResponse.ok)throw new Error(currentData.error||'Unable to load active event assignments.');
  coordinatorLeadAssignmentContext={events:assignmentData.events||[],coordinators:assignmentData.coordinators||[]};
  coordinatorLeadReassignmentContext={events:reassignmentData.events||[],coordinators:reassignmentData.coordinators||[]};
  coordinatorLeadCurrentAssignments=currentData.events||[];
  if(coordinatorLeadAssignmentDetails){
    const refreshed=coordinatorLeadCurrentAssignments.find(event=>event.event_id===coordinatorLeadAssignmentDetails.event_id&&event.assigned);
    coordinatorLeadAssignmentDetails=refreshed?{...coordinatorLeadAssignmentDetails,...refreshed}:null;
  }
}

function coordinatorLeadCurrentAssignmentsPage(){
  const assigned=coordinatorLeadCurrentAssignments.filter(event=>event.assigned);
  const unassigned=coordinatorLeadCurrentAssignments.filter(event=>!event.assigned);
  const assignedContent=assigned.length?assigned.map(coordinatorLeadCurrentAssignmentRow).join(''):'<div class="empty-state"><h3>No active assigned events</h3><p class="muted">There are no active events with a current Event Coordinator.</p></div>';
  const unassignedContent=unassigned.length?unassigned.map(coordinatorLeadCurrentAssignmentRow).join(''):'<div class="empty-state"><h3>No active unassigned requests</h3><p class="muted">All active event requests currently have an Event Coordinator.</p></div>';
  return pageHead('Current Event Coordinator assignments','Oversee active events and identify requests that still need an owner.',`<div class="actions"><button class="btn btn-soft" type="button" onclick="refreshCoordinatorLeadAssignments()">Refresh</button></div>`)+
    coordinatorLeadAssignmentDetailsPanel()+
    `<section class="panel" style="margin-bottom:20px"><div class="panel-head"><h2>Assigned active events</h2></div>${assignedContent}</section>`+
    `<section class="panel"><div class="panel-head"><h2>Unassigned active requests</h2></div>${unassignedContent}</section>`;
}

function coordinatorLeadAssignmentDetailsPanel(){
  const event=coordinatorLeadAssignmentDetails;
  if(!event)return '';
  const detail=(label,value)=>`<div class="equipment"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value??'Not provided')}</strong></div>`;
  const start=event.start_datetime||event.preferred_start_datetime;
  const end=event.end_datetime||event.preferred_end_datetime;
  const technicalSupport=event.technical_support_required===true?'Required':event.technical_support_required===false?'Not required':'Not provided';
  return `<section class="panel" style="margin-bottom:20px"><div class="panel-head"><div><div class="eyebrow">Current assignment</div><h2>${escapeHtml(event.name||'Untitled event')}</h2></div><button class="btn btn-soft btn-small" type="button" onclick="closeCoordinatorLeadAssignmentDetails()">Close</button></div><span class="status ready">Coordinator: ${escapeHtml(event.coordinator_name||'Name unavailable')}</span>${detail('Event ID',event.event_id)}${detail('Status',event.status)}${detail('Purpose',event.purpose)}${detail('Description',event.description)}${detail('Start',start?new Date(start).toLocaleString():'Not provided')}${detail('End',end?new Date(end).toLocaleString():'Not provided')}${detail('Expected attendance',event.expected_attendance)}${detail('Venue requirements',event.venue_requirements)}${detail('Accessibility needs',event.accessibility_needs)}${detail('Layout requirements',event.layout_requirements)}${detail('Technical support',technicalSupport)}${detail('Technical requirements',event.technical_requirements)}</section>`;
}

function coordinatorLeadCurrentAssignmentRow(event){
  const start=event.start_datetime||event.preferred_start_datetime;
  const end=event.end_datetime||event.preferred_end_datetime;
  const period=start?`${new Date(start).toLocaleString()}${end?` to ${new Date(end).toLocaleString()}`:''}`:'Date not provided';
  const owner=event.assigned?`Coordinator: ${escapeHtml(event.coordinator_name||'Name unavailable')}`:'Unassigned';
  const action=event.assigned?`<button class="btn btn-soft btn-small" type="button" onclick="openCoordinatorLeadAssignmentDetails('${escapeAttribute(event.event_id)}')">Open assignment</button>`:'';
  return `<div class="list-row"><div class="date-tile">?</div><div><h4>${escapeHtml(event.name||'Untitled event')}</h4><div class="muted">${escapeHtml(event.event_id)} · ${escapeHtml(period)} · ${escapeHtml(event.status)}</div></div><div class="event-actions"><span class="status ${event.assigned?'ready':'pending'}">${owner}</span>${action}</div></div>`;
}

function coordinatorLeadAssignmentPage(){
  const assigned=lastCoordinatorLeadAssignment
    ?`<section class="panel" style="margin-bottom:20px"><div class="notice"><strong>Assignment completed</strong><span class="muted">${escapeHtml(lastCoordinatorLeadAssignment.name||'Untitled event')} is assigned to ${escapeHtml(lastCoordinatorLeadAssignment.coordinator_name||'the selected coordinator')} and remains requested.</span></div></section>`:'';
  const content=coordinatorLeadAssignmentContext.events.length
    ?coordinatorLeadAssignmentContext.events.map(coordinatorLeadAssignmentRow).join('')
    :'<div class="empty-state"><h3>No unassigned event requests</h3><p class="muted">All requested events currently have an Event Coordinator.</p></div>';
  const reassigned=lastCoordinatorLeadReassignment
    ?`<section class="panel" style="margin-bottom:20px"><div class="notice"><strong>Reassignment completed</strong><span class="muted">${escapeHtml(lastCoordinatorLeadReassignment.name||'Untitled event')} is now assigned to ${escapeHtml(lastCoordinatorLeadReassignment.coordinator_name||'the selected coordinator')}.</span></div></section>`:'';
  const reassignmentContent=coordinatorLeadReassignmentContext.events.length
    ?coordinatorLeadReassignmentContext.events.map(coordinatorLeadReassignmentRow).join('')
    :'<div class="empty-state"><h3>No current assignments</h3><p class="muted">There are no assigned events available for reassignment.</p></div>';
  return pageHead('Coordinator assignments','Assign submitted requests and update event ownership when necessary.')+
    assigned+reassigned+
    `<section class="panel" style="margin-bottom:20px"><div class="panel-head"><h2>Unassigned requests</h2><button class="btn btn-soft btn-small" type="button" onclick="refreshCoordinatorLeadAssignments()">Refresh</button></div>${content}</section>`+
    `<section class="panel"><div class="panel-head"><h2>Current assignments</h2></div>${reassignmentContent}</section>`;
}

function coordinatorLeadAssignmentRow(event){
  const options=coordinatorLeadAssignmentContext.coordinators.map(coordinator=>
    `<option value="${escapeAttribute(coordinator.user_id)}">${escapeHtml(coordinator.name)}</option>`).join('');
  const date=event.preferred_start_datetime?new Date(event.preferred_start_datetime).toLocaleString():'Date not provided';
  return `<form class="list-row coordinator-lead-assignment-form" data-event-id="${escapeAttribute(event.event_id)}"><div class="date-tile">?</div><div><h4>${escapeHtml(event.name||'Untitled event')}</h4><div class="muted">${escapeHtml(date)} · ${escapeHtml(event.expected_attendance??'Attendance not provided')} attendees · ${escapeHtml(event.status)}</div></div><div class="event-actions"><select name="coordinator_id" aria-label="Event Coordinator for ${escapeAttribute(event.name||'event')}" ${options?'':'disabled'}><option value="">Select coordinator</option>${options}</select><button class="btn btn-primary btn-small" type="submit" ${options?'':'disabled'}>Assign</button></div></form>`;
}

function coordinatorLeadReassignmentRow(event){
  const options=coordinatorLeadReassignmentContext.coordinators.filter(coordinator=>coordinator.user_id!==event.coordinator_id).map(coordinator=>
    `<option value="${escapeAttribute(coordinator.user_id)}">${escapeHtml(coordinator.name)}</option>`).join('');
  const date=event.preferred_start_datetime?new Date(event.preferred_start_datetime).toLocaleString():'Date not provided';
  return `<form class="list-row coordinator-lead-reassignment-form" data-event-id="${escapeAttribute(event.event_id)}"><div class="date-tile">?</div><div><h4>${escapeHtml(event.name||'Untitled event')}</h4><div class="muted">${escapeHtml(date)} · Current coordinator: ${escapeHtml(event.coordinator_name||'Name unavailable')} · ${escapeHtml(event.status)}</div></div><div class="event-actions"><select name="coordinator_id" aria-label="Replacement Event Coordinator for ${escapeAttribute(event.name||'event')}" ${options?'':'disabled'}><option value="">Select replacement</option>${options}</select><button class="btn btn-primary btn-small" type="submit" ${options?'':'disabled'}>Reassign</button></div></form>`;
}

async function refreshCoordinatorLeadAssignments(){
  try{await loadCoordinatorLeadAssignmentContext();renderPage()}catch(error){toast(error.message)}
}

async function openCoordinatorLeadAssignmentDetails(eventId){
  try{
    const response=await authenticatedFetch(`/api/coordinator-lead/events/${encodeURIComponent(eventId)}/assignment-details`);
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Unable to open the current assignment.');
    coordinatorLeadAssignmentDetails=data.event;
    renderPage();
  }catch(error){toast(error.message)}
}

function closeCoordinatorLeadAssignmentDetails(){
  coordinatorLeadAssignmentDetails=null;
  renderPage();
}

document.getElementById('mainContent').addEventListener('submit',async event=>{
  const form=event.target.closest('.coordinator-lead-assignment-form');
  if(!form)return;
  event.preventDefault();
  const coordinatorId=form.elements.coordinator_id.value;
  if(!coordinatorId){toast('Select an Event Coordinator.');return}
  const button=form.querySelector('button[type="submit"]');
  button.disabled=true;
  try{
    const response=await authenticatedFetch(`/api/coordinator-lead/events/${encodeURIComponent(form.dataset.eventId)}/assign`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coordinator_id:coordinatorId})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Unable to assign the event request.');
    lastCoordinatorLeadAssignment=data.event;
    await loadCoordinatorLeadAssignmentContext();
    renderPage();
    toast('Event Coordinator assigned.');
  }catch(error){toast(error.message);button.disabled=false}
});

document.getElementById('mainContent').addEventListener('submit',async event=>{
  const form=event.target.closest('.coordinator-lead-reassignment-form');
  if(!form)return;
  event.preventDefault();
  const coordinatorId=form.elements.coordinator_id.value;
  if(!coordinatorId){toast('Select a replacement Event Coordinator.');return}
  const button=form.querySelector('button[type="submit"]');
  button.disabled=true;
  try{
    const response=await authenticatedFetch(`/api/coordinator-lead/events/${encodeURIComponent(form.dataset.eventId)}/reassign`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coordinator_id:coordinatorId})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Unable to reassign the event.');
    lastCoordinatorLeadReassignment=data.event;
    await loadCoordinatorLeadAssignmentContext();
    renderPage();
    toast('Event Coordinator reassigned.');
  }catch(error){toast(error.message);button.disabled=false}
});
