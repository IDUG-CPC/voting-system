function _getCsrfToken() {
  const raw = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="));
  if (raw) {
    const v = raw.slice("csrftoken=".length);
    try {
      return decodeURIComponent(v);
    } catch (e) {
      return v;
    }
  }
  const inp = document.querySelector("input[name=csrfmiddlewaretoken]");
  return inp?.value || "";
}
const CSRF_TOKEN = _getCsrfToken();
const CSV_PREVIEW_URL = window.PLANNER_API?.csvPreview || "/planner/api/csv-preview/";
const CSV_IMPORT_URL = window.PLANNER_API?.csvImport || "/planner/api/csv-import/";
const EXPORT_EXCEL_URL = window.PLANNER_API?.exportExcel || "/planner/export-excel/";
let dragged = null, draggedFromCell = null;
/** Persists drag data across day-tab switches (calendar DOM is rebuilt on loadDay). */
let dragPayload = null;
let dayTabHoverTimer = null;
let dayTabHoverDayId = null;
let dayTabsDragBound = false;
const DAY_TAB_SWITCH_DELAY_MS = 400;
const READ_ONLY = typeof window.READ_ONLY !== "undefined" && window.READ_ONLY;
function formatSessionRating(rating) {
  const n = Number(rating);
  if (Number.isNaN(n)) return "0.00";
  return n.toFixed(2);
}

function formatSpeakerDisplay(s) {
  const name = s.speaker_full || "";
  return s.is_first_time_presenter ? `⭐ ${name}` : name;
}

function appendRegularSessionDecorations(wrap, s) {
  const ratingEl = document.createElement("span");
  ratingEl.className = "session-rating";
  ratingEl.textContent = formatSessionRating(s.rating);
  wrap.appendChild(ratingEl);
}

let allSessions = [];
let currentUsedSessions = [];
let activeSessionType = "all";
let itemListDropBound = false;

// Session filter state (for "All" tab)
let filterMode = "AND";
let selectedTypeIds = [];
let selectedSubjectIds = [];
let selectedSessionTexts = [];
let selectedTopicIds = [];

function renderSessionTypeLegend(sessionTypes) {
  const container = document.querySelector(".session-type-legend");
  if (!container) return;
  container.innerHTML = "";

  (sessionTypes || []).forEach(t => {
      // IBM: show two counters — IBM-z/OS and IBM-LUW (by subject)
      if (t.name && t.name.toUpperCase() === "IBM") {
        ["ibm_zos", "ibm_luw"].forEach((countKey, i) => {
          const label = i === 0 ? "IBM-z/OS" : "IBM-LUW";
          const el = document.createElement("div");
          el.className = "session-type-item";
          el.dataset.typeId = t.id;
          el.dataset.countKey = countKey;
          el.innerHTML = `
            <div class="session-type-color" style="background-color:${t.color}; background:${t.color};"></div>
            <span>${label}</span>
            <span class="session-type-count">(0)</span>
          `;
          container.appendChild(el);
        });
        return;
      }

      const el = document.createElement("div");
      el.className = "session-type-item";
      el.dataset.typeId = t.id;

      el.innerHTML = `
          <div class="session-type-color"
               style="background-color:${t.color}; background:${t.color};"></div>
          <span>${t.name}</span>
          <span class="session-type-count">(0)</span>
      `;

      container.appendChild(el);
    });
}

async function updateSessionTypeCounters() {
  const res = await fetch("/planner/api/session-type-counts/");
  const data = await res.json();
  const counts = (data && data.counts) || {};

  document.querySelectorAll(".session-type-item").forEach(item => {
    const countKey = item.dataset.countKey;
    const typeId = item.dataset.typeId;
    const count = countKey != null
      ? (counts[countKey] ?? 0)
      : (counts[String(typeId)] ?? counts[Number(typeId)] ?? 0);
    const total = countKey != null
      ? (counts[String(typeId)] ?? counts[Number(typeId)] ?? 0)
      : null;
    const span = item.querySelector(".session-type-count");
    if (span) {
      span.textContent = (total != null && total > 0)
        ? `(${count}/${total})`
        : `(${count})`;
    }
  });
}

function newTransactionId() {
  return crypto.randomUUID();
}


async function loadDays() {
  const res = await fetch("/planner/api/days/");
  const data = await res.json();
  buildDayTabs(data.days);
}

function buildDayTabs(days) {
  const tabs = document.getElementById("dayTabs");
  tabs.innerHTML = "";

  days.forEach((day, index) => {
    const li = document.createElement("li");
    li.className = "nav-item";

    const btn = document.createElement("button");
    btn.className = "nav-link" + (index === 0 ? " active" : "");
    btn.dataset.day = day.id;
    btn.textContent = day.day;

    btn.addEventListener("click", () => {
      activateDayTab(day.id);
      loadDay(day.id);
    });

    attachDayTabDragHandlers(btn);

    li.appendChild(btn);
    tabs.appendChild(li);
  });

  if (!READ_ONLY && !dayTabsDragBound) {
    tabs.addEventListener("dragleave", (e) => {
      if (!tabs.contains(e.relatedTarget)) {
        clearDayTabHoverTimer();
        clearDayTabDragHighlight();
      }
    });
    dayTabsDragBound = true;
  }

  // auto-load first day
  if (days.length) {
    loadDay(days[0].id);
  }
}

function activateDayTab(dayId) {
  document.querySelectorAll("#dayTabs .nav-link").forEach(b => {
    b.classList.toggle("active", String(b.dataset.day) === String(dayId));
  });
}

function clearDayTabHoverTimer() {
  if (dayTabHoverTimer) {
    clearTimeout(dayTabHoverTimer);
    dayTabHoverTimer = null;
  }
  dayTabHoverDayId = null;
}

function clearDayTabDragHighlight() {
  document.querySelectorAll("#dayTabs .nav-link.drag-over-tab").forEach(b => {
    b.classList.remove("drag-over-tab");
  });
}

function clearDragPayload() {
  dragPayload = null;
  clearDayTabHoverTimer();
  clearDayTabDragHighlight();
}

function attachDayTabDragHandlers(btn) {
  if (READ_ONLY) return;

  btn.addEventListener("dragenter", (e) => {
    if (!dragPayload?.assignParams) return;
    e.preventDefault();
    clearDayTabDragHighlight();
    btn.classList.add("drag-over-tab");
  });

  btn.addEventListener("dragover", (e) => {
    if (!dragPayload?.assignParams) return;
    e.preventDefault();
    const dayId = btn.dataset.day;
    const activeBtn = document.querySelector("#dayTabs .nav-link.active");
    if (activeBtn && String(activeBtn.dataset.day) === String(dayId)) return;
    if (dayTabHoverDayId === dayId && dayTabHoverTimer) return;

    clearDayTabHoverTimer();
    dayTabHoverDayId = dayId;
    dayTabHoverTimer = setTimeout(() => {
      dayTabHoverTimer = null;
      activateDayTab(dayId);
      loadDay(parseInt(dayId, 10));
    }, DAY_TAB_SWITCH_DELAY_MS);
  });

  btn.addEventListener("dragleave", () => {
    btn.classList.remove("drag-over-tab");
  });
}

function refreshCurrentDay() {
  const activeBtn = document.querySelector("#dayTabs .nav-link.active");
  if (!activeBtn) return;
  const day = parseInt(activeBtn.dataset.day);
  loadDay(day);
}



function showToast(message, type="info", delay=2500) {
  const toastEl = document.getElementById("undoToast");
  const toastBody = document.getElementById("undoToastBody");
  toastEl.className = "toast align-items-center border-0 shadow-sm text-bg-" + type;
  toastBody.textContent = message;
  new bootstrap.Toast(toastEl, { delay }).show();
}

function filenameFromContentDisposition(headerVal) {
  if (!headerVal || typeof headerVal !== "string") return null;
  const utf8Match = headerVal.match(/filename\*=(?:UTF-8'')?([^;]+)/i);
  if (utf8Match) {
    let raw = utf8Match[1].trim().replace(/^"(.*)"$/, "$1");
    try {
      return decodeURIComponent(raw);
    } catch (e) {
      return raw;
    }
  }
  const quoted = headerVal.match(/filename="((?:\\.|[^"\\])*)"/i);
  if (quoted) return quoted[1].replace(/\\"/g, '"');
  const plain = headerVal.match(/filename=([^;\s]+)/i);
  return plain ? plain[1].replace(/^"(.*)"$/, "$1") : null;
}

function setPlannerBusyVisible(visible, message) {
  const overlay = document.getElementById("plannerBusyOverlay");
  const msgEl = document.getElementById("plannerBusyMessage");
  if (!overlay) return;
  if (msgEl) {
    if (visible) {
      msgEl.textContent = message != null && message !== "" ? message : "Please wait…";
    } else {
      msgEl.textContent = "Please wait…";
    }
  }
  overlay.classList.toggle("d-none", !visible);
  overlay.setAttribute("aria-hidden", visible ? "false" : "true");
  document.body.classList.toggle("planner-busy", visible);
}

function enableAutoScroll() {
  let scrollInterval=null;
  window.addEventListener("dragover", e=>{
    const y=e.clientY, h=window.innerHeight, threshold=80, speed=25;
    clearInterval(scrollInterval);
    if (y<threshold) scrollInterval=setInterval(()=>window.scrollBy(0,-speed),16);
    else if (y>h-threshold) scrollInterval=setInterval(()=>window.scrollBy(0,speed),16);
  });
  ["dragleave","drop"].forEach(evt=>window.addEventListener(evt,()=>clearInterval(scrollInterval)));
}

function attachDrag(el, fromCell=false){
  if (READ_ONLY) {
    el.draggable = false;
    el.classList.add("read-only-item");
    return;
  }
  if (el.draggable === false) return;
  el.addEventListener("dragstart",()=>{
    dragged=el;
    draggedFromCell=fromCell?el.dataset.layoutId:null;
    dragPayload = {
      sourceLayoutId: draggedFromCell ? String(draggedFromCell) : null,
      assignParams: captureAssignParams(el),
    };
    el.classList.add("opacity-50");
  });
  el.addEventListener("dragend",()=>{
    el.classList.remove("opacity-50");
    dragged=null;
    draggedFromCell=null;
    clearDragPayload();
  });
}

function makeDraggableSession(cellLabel, s, layoutId) {
  const wrap = document.createElement("div");
  wrap.className = "cell-session-wrap";
  wrap.style.backgroundColor = s.color || "#e7f1ff";

  const div = document.createElement("div");
  div.className = "item";
  div.draggable = !READ_ONLY;
  div.dataset.layoutId = layoutId;
  attachDrag(div, true);

  if (s.is_special) {
    div.dataset.specialTypeId = s.special_type_id;
    div.dataset.name = s.special_type_name;
    div.dataset.color = s.color;
    const desc = (s.description || "").trim();
    const rightPart = desc ? (desc.length > 120 ? desc.slice(0, 117) + "…" : desc) : s.special_type_name;
    const strong = document.createElement("strong");
    strong.textContent = `${cellLabel} – ${rightPart}`;
    div.appendChild(strong);
    wrap.appendChild(div);
    if (!READ_ONLY) {
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "session-edit-btn";
      editBtn.title = "Edit description";
      editBtn.innerHTML = "<i class=\"bi bi-pencil\"></i>";
      editBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        openSessionEditModal(s.layout_id, s.description || "", cellLabel, s.special_type_name);
      });
      wrap.appendChild(editBtn);
    }
  } else {
    div.dataset.id = s.id;
    div.dataset.sessionType = s.session_type_id;
    div.innerHTML = `<strong>${cellLabel} (${s.code})</strong> - ${s.title}<br>${formatSpeakerDisplay(s)} - ${s.speaker_company || ""}${s.subject ? ` (${s.subject})` : ""}`;
    wrap.appendChild(div);
    appendRegularSessionDecorations(wrap, s);
  }
  return wrap;
}

function renderAvailability(used) {
  const usedSet = new Set(used);
  // Only hide normal sessions when assigned; special sessions stay visible in their list
  document.querySelectorAll("#itemList .item").forEach(it => {
    it.style.display = usedSet.has(parseInt(it.dataset.id)) ? "none" : "";
  });
}

async function loadDay(day=1){
  const r=await fetch(`/planner/api/day/${day}/`);
  const data=await r.json();
  currentUsedSessions = data.used_sessions;
  renderSessionList();

  const headerDiv=document.getElementById("calendar-headers");
  headerDiv.innerHTML="<div></div>";
  data.headers.forEach(h=>{
    const cell=document.createElement("div");
    cell.className="border bg-light p-2";
    cell.innerHTML=`<strong>${h.subject}</strong><br><small>${h.room_name}</small>`;
    headerDiv.appendChild(cell);
  });

  const cal=document.getElementById("calendar");
  cal.innerHTML="";
  let currentRow="";
  let currentTimeSlotId = null;
  const skipTracks = new Set();

  data.layout.forEach(l=>{
    if (skipTracks.has(l.track + "-" + l.time_slot_id)) return;

    // Skip later tracks that are merged under a colspan
    if (l.colspan && parseInt(l.colspan) > 1) {
      const startIndex = ["A","B","C","D","E","F"].indexOf(l.track);
      for (let i = 1; i < l.colspan; i++) {
        const nextTrack = String.fromCharCode("A".charCodeAt(0) + startIndex + i);
        skipTracks.add(nextTrack + "-" + l.time_slot_id);
      }
    }

    if (l.type === "break") {
      const rh = document.createElement("div");
      rh.className = "row-header";
      const timeRange = (l.time_start || l.time_end) ? `${l.time_start || ""}–${l.time_end || ""}` : "";
      rh.innerHTML = timeRange
        ? `<span class="label">${l.time_label}</span><span class="time">${timeRange}</span>`
        : `<span class="label">${l.time_label}</span>`;
      cal.appendChild(rh);

      const sep = document.createElement("div");
      sep.className = "separator-row";
      sep.style.gridColumn = "2 / span 6";
      cal.appendChild(sep);
      currentRow = l.time_label;
      currentTimeSlotId = l.time_slot_id;
      return;
    }

    if (l.type === "lock") {
      if (l.time_slot_id !== currentTimeSlotId || (l.time_label && l.time_label !== currentRow)) {
        const rh = document.createElement("div");
        rh.className = "row-header";
        const timeRange = (l.time_start || l.time_end) ? `${l.time_start || ""}–${l.time_end || ""}` : "";
        rh.innerHTML = timeRange
          ? `<span class="label">${l.time_label}</span><span class="time">${timeRange}</span>`
          : `<span class="label">${l.time_label}</span>`;
        cal.appendChild(rh);
        currentRow = l.time_label;
        currentTimeSlotId = l.time_slot_id;
      }

      const div = document.createElement("div");
      div.className = "cell cell-lock";
      div.dataset.id = l.id;

      // apply colspan if needed
      if (l.colspan && parseInt(l.colspan) > 1) {
        const colIndex = ["A","B","C","D","E","F"].indexOf(l.track) + 2;
        div.style.gridColumn = `${colIndex} / span ${l.colspan}`;
      }

      // NO dragover / drop handlers
      cal.appendChild(div);
      return;
    }


    // Normal slot rows: one row header per time slot (so Alternate shows 5 lines when there are 5 time slots)
    if (l.time_slot_id !== currentTimeSlotId) {
      const rh = document.createElement("div");
      rh.className = "row-header";
      const timeRange = (l.time_start || l.time_end) ? `${l.time_start || ""}–${l.time_end || ""}` : "";
      rh.innerHTML = timeRange
        ? `<span class="label">${l.time_label || ""}</span><span class="time">${timeRange}</span>`
        : `<span class="label">${l.time_label || ""}</span>`;
      cal.appendChild(rh);
      currentRow = l.time_label;
      currentTimeSlotId = l.time_slot_id;
    }

    const div=document.createElement("div");
    div.className="cell"; div.dataset.id=l.id; div.dataset.day=day;

    // Apply colspan if specified (for A3 + B3)
    if (l.colspan && parseInt(l.colspan) > 1) {
      const colIndex = ["A","B","C","D","E","F"].indexOf(l.track) + 2;
      div.style.gridColumn = `${colIndex} / span ${l.colspan}`;
    }

    const slot = data.slots[l.id];
    if (slot && (slot.title || slot.is_special)) {
      const wrap = makeDraggableSession(l.label || "", slot, l.id);
      div.appendChild(wrap);
      div.classList.add("slot-filled");
      if (!READ_ONLY) {
        wrap.addEventListener("dragover", e => { e.preventDefault(); });
        wrap.addEventListener("drop", e => {
          e.preventDefault();
          e.stopPropagation();
          div.classList.remove("drag-over");
          handleDrop(e, l, day);
        });
        wrap.addEventListener("dragenter", e => { e.preventDefault(); div.classList.add("drag-over"); });
        wrap.addEventListener("dragleave", e => { div.classList.remove("drag-over"); });
      }
    } else {
      div.textContent = l.label || "";
    }

    if (!READ_ONLY) {
      ["dragover","dragenter","dragleave"].forEach(ev=>{
        div.addEventListener(ev,e=>{
          if(ev==="dragover")e.preventDefault();
          if(ev==="dragenter"){e.preventDefault();div.classList.add("drag-over");}
          if(ev==="dragleave")div.classList.remove("drag-over");
        });
      });
      div.addEventListener("drop",e=>handleDrop(e,l,day));
    }
    cal.appendChild(div);
  });


  // Drop back to list (works on both normal and special list area)
  const listContainer = document.getElementById("sessionListContainer");
  if (!itemListDropBound && listContainer && !READ_ONLY) {
    listContainer.addEventListener("dragover", e => e.preventDefault());
    listContainer.addEventListener("drop", async e => {
      e.preventDefault();
      const sourceLayoutId = dragPayload?.sourceLayoutId ?? draggedFromCell;
      if (sourceLayoutId) {
        const res = await fetch("/planner/api/unassign/", {
          method: "POST",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          body: JSON.stringify({ layout_id: sourceLayoutId, transaction_id: newTransactionId() })
        });
        const d = await res.json();
        appendLogs(d.logs);
        currentUsedSessions = d.used_sessions;
        if (activeSessionType !== "special") renderSessionList();
        else document.querySelectorAll("#specialList .item").forEach(el => attachDrag(el));
        refreshCurrentDay();
        updateSessionTypeCounters();
      }
    });
    itemListDropBound = true;
  }
}

/** Capture assign params from drag element once – dragend can clear dragged before async code runs. */
function captureAssignParams(dragEl) {
  if (!dragEl || !dragEl.dataset) return null;
  const specialTypeId = dragEl.dataset.specialTypeId;
  if (specialTypeId) {
    return { special_session_type_id: parseInt(specialTypeId, 10) };
  }
  const sessionId = dragEl.dataset.id;
  if (sessionId) {
    return { session_id: parseInt(sessionId, 10) };
  }
  return null;
}

function buildAssignBody(params, layoutId, transactionId) {
  if (!params) return null;
  return { layout_id: layoutId, transaction_id: transactionId, ...params };
}

async function handleDrop(e, l, day) {
  e.preventDefault();
  if (READ_ONLY) return;
  const cell = e.target.closest ? e.target.closest(".cell") : e.currentTarget;
  if (cell) cell.classList.remove("drag-over");

  const assignParams = dragPayload?.assignParams ?? captureAssignParams(dragged);
  if (!assignParams) return;

  const sourceLayoutId = dragPayload?.sourceLayoutId
    ?? (draggedFromCell ? String(draggedFromCell) : null);

  const targetLayoutId = String(l.id);
  if (sourceLayoutId === targetLayoutId) return;

  const originalLayout = sourceLayoutId;
  let allLogs = [];

  if (sourceLayoutId && sourceLayoutId !== targetLayoutId) {
    const tx = newTransactionId();
    const moveBody = {
      source_layout_id: parseInt(sourceLayoutId, 10),
      target_layout_id: parseInt(targetLayoutId, 10),
      transaction_id: tx,
      ...assignParams,
    };
    const res = await fetch("/planner/api/move/", {
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      body: JSON.stringify(moveBody),
    });
    const a = await res.json();

    if (!a.ok) {
      showToast(a.message, "danger");
      const restoreBody = buildAssignBody(assignParams, parseInt(originalLayout, 10), newTransactionId());
      if (restoreBody) {
        await fetch("/planner/api/assign/", {
          method: "POST",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          body: JSON.stringify(restoreBody),
        });
      }
      await fetch("/planner/api/undo/", { method: "POST", headers: { "X-CSRFToken": CSRF_TOKEN } });
      await fetch("/planner/api/undo/", { method: "POST", headers: { "X-CSRFToken": CSRF_TOKEN } });
      return;
    }

    currentUsedSessions = a.used_sessions;
    appendLogs(a.logs || []);
    if (activeSessionType !== "special") renderSessionList();
    refreshCurrentDay();
    updateSessionTypeCounters();
    return;
  }

  if (!sourceLayoutId) {
    const res = await fetch("/planner/api/assign/", {
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      body: JSON.stringify(buildAssignBody(assignParams, l.id, newTransactionId()))
    });
    const d = await res.json();

    if (!d.ok) {
      showToast(d.message, "danger");
      return;
    }

    appendLogs(d.logs);
    currentUsedSessions = d.used_sessions;
    if (activeSessionType !== "special") renderSessionList();
    refreshCurrentDay();
    updateSessionTypeCounters();
  }
}

function truncateText(s, n = 120) {
  s = (s || "").trim();
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function buildLogLine(l) {
  const line = document.createElement("div");
  line.className = "log-line";
  line.dataset.logId = l.id || "";              // requires API to return id
  line.dataset.comment = (l.comment || "");  // requires API to return comment
  line.dataset.timestamp = l.time || "";

  const d = new Date(l.time);
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const timeSpan = document.createElement("span");
  timeSpan.className = "log-time";
  timeSpan.textContent = time;

  const msgDiv = document.createElement("div");
  msgDiv.className = "log-message";
  msgDiv.textContent = l.message;

  const preview = document.createElement("div");
  preview.className = "log-comment-preview";

  if (l.comment && l.comment.trim()) {
    preview.textContent = truncateText(l.comment, 120);
  } else {
    preview.textContent = "";   // keep column width
  }

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "log-comment-btn" + ((l.comment && l.comment.trim()) ? "" : " comment-hidden");
  btn.title = "Comment";
  btn.textContent = "💬";
  btn.dataset.logId = l.id || "";

  if (!l.id) {
    btn.style.visibility = "hidden"; // keep column width, but no click
  }
  if (READ_ONLY) {
    btn.style.display = "none";
  }

  line.appendChild(timeSpan);
  line.appendChild(msgDiv);    // column 2
  line.appendChild(preview);   // column 3
  line.appendChild(btn);       // column 4

  return line;
}

function appendLogs(logs) {
  const logDiv = document.getElementById("log");
  logs.forEach(l => logDiv.appendChild(buildLogLine(l)));
  logDiv.scrollTop = logDiv.scrollHeight;
}

function appendLogsback(logs){
  const logDiv = document.getElementById("log");

  logs.forEach(l => {
    const line = document.createElement("div");

    const d = new Date(l.time);
    const time = d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });

    const timeSpan = document.createElement("span");
    timeSpan.className = "log-time";
    timeSpan.textContent = time;

    const msgSpan = document.createElement("span");
    msgSpan.className = "log-message";
    msgSpan.textContent = l.message;

    line.className = "log-line";
    line.appendChild(timeSpan);
    line.appendChild(msgSpan);
    logDiv.appendChild(line);
  });

  logDiv.scrollTop = logDiv.scrollHeight;
}

async function loadLogHistory() {
  const r = await fetch("/planner/api/logs/");
  const data = await r.json();
  const logDiv = document.getElementById("log");
  logDiv.innerHTML = "";
  data.logs.forEach(l => logDiv.appendChild(buildLogLine(l)));
  logDiv.scrollTop = logDiv.scrollHeight;
}

async function loadLogHistoryback(){
  const r = await fetch("/planner/api/logs/");
  const data = await r.json();
  const logDiv = document.getElementById("log");
  logDiv.innerHTML = "";

  data.logs.forEach(l => {
    const line = document.createElement("div");

    const d = new Date(l.time); // ISO UTC → browser local
    const time = d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });

    const timeSpan = document.createElement("span");
    timeSpan.className = "log-time";
    timeSpan.textContent = time;

    const msgSpan = document.createElement("span");
    msgSpan.className = "log-message";
    msgSpan.textContent = l.message;

    line.className = "log-line";
    line.appendChild(timeSpan);
    line.appendChild(msgSpan);
    logDiv.appendChild(line);
  });

  logDiv.scrollTop = logDiv.scrollHeight;
}

function sessionStatusIsDeclined(status) {
  return String(status == null ? "" : status).trim().toLowerCase() === "declined";
}

function sessionStatusIsSchedulable(status) {
  return !sessionStatusIsDeclined(status);
}

function initAllSessions() {
  allSessions = [];
  document.querySelectorAll("#itemList .item").forEach(el => {
    const topicIdsStr = (el.dataset.topicIds || "").trim();
    const topicIds = topicIdsStr ? topicIdsStr.split(",").map((x) => parseInt(x.trim(), 10)).filter((n) => !isNaN(n)) : [];
    const st = (el.dataset.sessionText || "").trim();
    const statusRaw = (el.dataset.status || "").trim();
    allSessions.push({
      id: parseInt(el.dataset.id, 10),
      type: el.dataset.type,
      typeId: el.dataset.typeId != null ? parseInt(el.dataset.typeId, 10) : null,
      subjectId: el.dataset.subjectId != null && el.dataset.subjectId !== "" ? parseInt(el.dataset.subjectId, 10) : null,
      sessionText: st !== "" ? st : null,
      status: statusRaw || "Pending",
      topicIds,
      html: el.outerHTML
    });
  });
}

function getJsonFromPage(id) {
  const el = document.getElementById(id);
  if (!el || !el.textContent) return null;
  try {
    return JSON.parse(el.textContent);
  } catch (_) {
    return null;
  }
}

function getSessionTypesFromPage() {
  const parsed = getJsonFromPage("session-types-data");
  if (parsed == null) return null;
  return Array.isArray(parsed) ? parsed : null;
}

function passesSessionFilter(s) {
  if (filterMode === "AND") {
    const hasType = selectedTypeIds.length === 0 || (s.typeId != null && selectedTypeIds.includes(s.typeId));
    const hasSubject = selectedSubjectIds.length === 0 || (s.subjectId != null && selectedSubjectIds.includes(s.subjectId));
    const hasSessionText =
      selectedSessionTexts.length === 0 ||
      (s.sessionText != null && selectedSessionTexts.includes(s.sessionText));
    const hasTopic = selectedTopicIds.length === 0 || (s.topicIds && s.topicIds.some((tid) => selectedTopicIds.includes(tid)));
    return hasType && hasSubject && hasSessionText && hasTopic;
  }
  // OR: only dimensions with at least one selection count; session passes if it matches any of those
  const anyType = selectedTypeIds.length > 0 && s.typeId != null && selectedTypeIds.includes(s.typeId);
  const anySubject = selectedSubjectIds.length > 0 && s.subjectId != null && selectedSubjectIds.includes(s.subjectId);
  const anySessionText =
    selectedSessionTexts.length > 0 && s.sessionText != null && selectedSessionTexts.includes(s.sessionText);
  const anyTopic = selectedTopicIds.length > 0 && s.topicIds && s.topicIds.some((tid) => selectedTopicIds.includes(tid));
  const hasAnySelection =
    selectedTypeIds.length > 0 ||
    selectedSubjectIds.length > 0 ||
    selectedSessionTexts.length > 0 ||
    selectedTopicIds.length > 0;
  return !hasAnySelection || anyType || anySubject || anySessionText || anyTopic;
}

function getFilteredSessions() {
  return allSessions.filter(passesSessionFilter);
}

function updateSessionFilterResults() {
  const el = document.getElementById("sessionFilterResults");
  if (!el) return;
  const usedSet = new Set(currentUsedSessions);
  const schedulable = (s) => sessionStatusIsSchedulable(s.status);
  const totalAvailable = allSessions.filter((s) => schedulable(s) && !usedSet.has(s.id)).length;
  const filtered = getFilteredSessions().filter(schedulable);
  const matchingAvailable = filtered.filter((s) => !usedSet.has(s.id)).length;
  el.textContent = `Results: ${matchingAvailable} / ${totalAvailable}`;
  updateSessionFilterBtnActive();
}

function updateSessionFilterBtnActive() {
  const filterBtn = document.getElementById("sessionFilterBtn");
  if (!filterBtn) return;
  const icon = filterBtn.querySelector(".bi");
  const active =
    selectedTypeIds.length > 0 ||
    selectedSubjectIds.length > 0 ||
    selectedSessionTexts.length > 0 ||
    selectedTopicIds.length > 0;
  filterBtn.classList.toggle("text-primary", active);
  filterBtn.classList.toggle("text-secondary", !active);
  if (icon) {
    icon.classList.toggle("bi-funnel-fill", active);
    icon.classList.toggle("bi-funnel", !active);
  }
}

async function buildSessionTabs() {
  let types = getSessionTypesFromPage();
  if (!types || types.length === 0) {
    const res = await fetch("/planner/api/session-types/");
    const data = await res.json();
    types = Array.isArray(data.types) ? data.types : [];
  }

  renderSessionTypeLegend(types);
  await updateSessionTypeCounters();

  const tabs = document.getElementById("sessionTabs");
  tabs.innerHTML = "";

  function addTab(label, key, active = false) {
    const li = document.createElement("li");
    li.className = "nav-item";

    const btn = document.createElement("button");
    btn.className = "nav-link" + (active ? " active" : "");
    btn.textContent = label;
    btn.dataset.type = key;

    btn.addEventListener("click", () => {
      document.querySelectorAll("#sessionTabs .nav-link")
        .forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeSessionType = key;
      setSessionFilterButtonVisibility(key === "all");
      if (key === "special") {
        document.getElementById("itemList").style.display = "none";
        document.getElementById("specialList").style.display = "block";
        document.querySelectorAll("#specialList .item").forEach(el => attachDrag(el));
      } else {
        document.getElementById("itemList").style.display = "block";
        document.getElementById("specialList").style.display = "none";
        renderSessionList();
      }
    });

    li.appendChild(btn);
    tabs.appendChild(li);
  }

  addTab("All", "all", true);
  types.forEach(t => addTab(t.name, t.name));
  addTab("Special", "special");
  addTab("Declined", "declined");

  setupSessionFilterUI(types);
}

function setupSessionFilterUI(types) {
  const filterBtn = document.getElementById("sessionFilterBtn");
  const filterPanel = document.getElementById("sessionFilterPanel");
  const filterType = document.getElementById("filterType");
  const filterSubject = document.getElementById("filterSubject");
  const filterSessionText = document.getElementById("filterSessionText");
  const filterTopic = document.getElementById("filterTopic");
  const filterClear = document.getElementById("sessionFilterClear");
  const modeAll = document.getElementById("filterModeAll");
  const modeAny = document.getElementById("filterModeAny");

  if (!filterBtn || !filterPanel) return;

  const topics = getJsonFromPage("filter-topics-data") || [];
  const subjects = getJsonFromPage("filter-subjects-data") || [];
  const sessionTexts = getJsonFromPage("filter-session-type-strings-data") || [];

  [filterType, filterSubject, filterSessionText, filterTopic].forEach((sel) => {
    if (sel) sel.innerHTML = "";
  });
  (Array.isArray(types) ? types : []).forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    if (filterType) filterType.appendChild(opt);
  });
  (Array.isArray(subjects) ? subjects : []).forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.subject_id;
    opt.textContent = s.subject_code || s.subject_desc || String(s.subject_id);
    if (filterSubject) filterSubject.appendChild(opt);
  });
  (Array.isArray(sessionTexts) ? sessionTexts : []).forEach((txt) => {
    const opt = document.createElement("option");
    opt.value = txt;
    opt.textContent = txt;
    if (filterSessionText) filterSessionText.appendChild(opt);
  });
  (Array.isArray(topics) ? topics : []).forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.code || String(t.id);
    if (filterTopic) filterTopic.appendChild(opt);
  });

  filterBtn.style.display = activeSessionType === "all" ? "" : "none";

  filterBtn.addEventListener("click", () => {
    filterPanel.classList.toggle("show");
  });

  document.addEventListener("click", (e) => {
    if (!filterPanel.classList.contains("show")) return;
    if (filterPanel.contains(e.target) || filterBtn.contains(e.target)) return;
    filterPanel.classList.remove("show");
  });

  if (filterClear) {
    filterClear.addEventListener("click", () => {
      [filterType, filterSubject, filterSessionText, filterTopic].forEach((sel) => {
        if (sel) Array.from(sel.options).forEach((o) => o.selected = false);
      });
      if (modeAll) modeAll.checked = true;
      filterMode = "AND";
      selectedTypeIds = [];
      selectedSubjectIds = [];
      selectedSessionTexts = [];
      selectedTopicIds = [];
      updateSessionFilterBtnActive();
      renderSessionList();
    });
  }

  function syncFilterState() {
    selectedTypeIds = filterType ? Array.from(filterType.selectedOptions).map((o) => parseInt(o.value, 10)) : [];
    selectedSubjectIds = filterSubject ? Array.from(filterSubject.selectedOptions).map((o) => parseInt(o.value, 10)) : [];
    selectedSessionTexts = filterSessionText
      ? Array.from(filterSessionText.selectedOptions).map((o) => o.value)
      : [];
    selectedTopicIds = filterTopic ? Array.from(filterTopic.selectedOptions).map((o) => parseInt(o.value, 10)) : [];
    filterMode = modeAny && modeAny.checked ? "OR" : "AND";
  }

  [filterType, filterSubject, filterSessionText, filterTopic].forEach((el) => {
    if (el) el.addEventListener("change", () => { syncFilterState(); renderSessionList(); });
  });
  if (modeAll) modeAll.addEventListener("change", () => { syncFilterState(); renderSessionList(); });
  if (modeAny) modeAny.addEventListener("change", () => { syncFilterState(); renderSessionList(); });

  updateSessionFilterResults();
}

function setSessionFilterButtonVisibility(visible) {
  const filterBtn = document.getElementById("sessionFilterBtn");
  const filterPanel = document.getElementById("sessionFilterPanel");
  if (filterBtn) filterBtn.style.display = visible ? "" : "none";
  if (filterPanel && !visible) filterPanel.classList.remove("show");
}

function renderSessionList() {
  const list = document.getElementById("itemList");
  list.innerHTML = "";

  let toShow;
  if (activeSessionType === "declined") {
    toShow = allSessions.filter((s) => sessionStatusIsDeclined(s.status));
  } else if (activeSessionType === "all") {
    toShow = getFilteredSessions().filter((s) => sessionStatusIsSchedulable(s.status));
  } else {
    toShow = allSessions.filter(
      (s) => s.type === activeSessionType && sessionStatusIsSchedulable(s.status)
    );
  }

  toShow.forEach((s) => list.insertAdjacentHTML("beforeend", s.html));

  document.querySelectorAll("#itemList .item").forEach(el => {
    el.draggable = !sessionStatusIsDeclined(el.dataset.status);
    attachDrag(el);
  });
  document.querySelectorAll("#specialList .item").forEach(el => attachDrag(el));
  renderAvailability(currentUsedSessions);

  if (activeSessionType === "all") updateSessionFilterResults();
}

function openSessionEditModal(layoutId, description, cellLabel, specialTypeName) {
  const modal = document.getElementById("sessionEditModal");
  const textarea = document.getElementById("modalSessionDescription");
  const titleEl = document.getElementById("sessionEditModalLabel");
  if (modal && textarea) {
    modal.dataset.layoutId = layoutId;
    textarea.value = description || "";
    if (titleEl) titleEl.textContent = (cellLabel && specialTypeName) ? `${cellLabel} – ${specialTypeName}` : "Edit description";
    new bootstrap.Modal(modal).show();
    setTimeout(() => textarea.focus(), 150);
  }
}

async function saveSessionDetails() {
  const modal = document.getElementById("sessionEditModal");
  const textarea = document.getElementById("modalSessionDescription");
  const layoutId = modal && modal.dataset.layoutId;
  if (!layoutId) return;

  const res = await fetch("/planner/api/save-slot-description/", {
    method: "POST",
    headers: { "X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json" },
    body: JSON.stringify({ layout_id: parseInt(layoutId, 10), description: (textarea && textarea.value) || "" }),
  });
  const data = await res.json();
  if (data.ok) {
    showToast("Description saved", "success", 1500);
    bootstrap.Modal.getInstance(modal).hide();
    refreshCurrentDay();
  } else {
    showToast(data.message || "Failed to save", "danger");
  }
}



document.addEventListener("DOMContentLoaded", async () => {
  try {
    var msg = sessionStorage.getItem("importMessage");
    var nullCount = parseInt(sessionStorage.getItem("importNullCount") || "0", 10);
    sessionStorage.removeItem("importMessage");
    sessionStorage.removeItem("importNullCount");
    if (msg) {
      if (nullCount > 0) {
        showToast(msg + " " + nullCount + " session(s) have no session type (null). Please review.", "warning", 4500);
      } else {
        showToast(msg, "success", 3000);
      }
    }
  } catch (e) {}

  enableAutoScroll();

  if (READ_ONLY) {
    const undoBtn = document.getElementById("undoBtn");
    if (undoBtn) undoBtn.style.display = "none";
  }

  initAllSessions();
  await buildSessionTabs();
  renderSessionList();

  loadDays();
  loadLogHistory();

  document.getElementById("sessionEditSaveBtn")?.addEventListener("click", saveSessionDetails);

  // Splash: login form (AJAX); login required, no guest access
  const splashForm = document.getElementById("splash-login-form");

  if (splashForm) {
    splashForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = document.getElementById("splash-login-error");
      const btn = document.getElementById("splash-login-btn");
      const username = (document.getElementById("splash-username")?.value || "").trim();
      const password = document.getElementById("splash-password")?.value || "";
      errEl.style.display = "none";
      errEl.textContent = "";
      if (!username) {
        errEl.textContent = "Username required.";
        errEl.style.display = "block";
        return;
      }
      btn.disabled = true;
      try {
        const res = await fetch("/planner/login/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": CSRF_TOKEN,
          },
          body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (data.ok) {
          window.location.reload();
          return;
        }
        errEl.textContent = data.message || "Invalid username or password.";
        errEl.style.display = "block";
      } finally {
        btn.disabled = false;
      }
    });
  }

  const logDiv  = document.getElementById("log");
  const modalEl = document.getElementById("logCommentModal");
  const modal   = new bootstrap.Modal(modalEl);
  const txt     = document.getElementById("logCommentText");
  const hid     = document.getElementById("logCommentId");
  const saveBtn = document.getElementById("logCommentSaveBtn");
  const ctx = document.getElementById("logCommentContext");

  modalEl.addEventListener("hidden.bs.modal", () => {
    //document.body.focus();
    ctx.textContent = "";
  });

  modalEl.addEventListener("shown.bs.modal", () => {

    txt.focus();  // Focus on the text area when the modal is shown
  });

  function truncateText(s, n = 120) {
    s = (s || "").trim();
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  let activeLogRow = null;

  logDiv.addEventListener("click", (e) => {
    const btn = e.target.closest(".log-comment-btn");
    if (!btn) return;

    activeLogRow = btn.closest(".log-line");
    hid.value = activeLogRow.dataset.logId || "";
    txt.value = (activeLogRow.dataset.comment || "").trim();

    // ---
    const iso = activeLogRow.dataset.timestamp || "";
    let tsDb = "";

    if (iso) {
        const d = new Date(iso);
        tsDb = d.toLocaleString();

        const dateParts = tsDb.split(",")[0].split("/"); // Split by comma and then slash (for MM/DD/YYYY)
        const timeParts = tsDb.split(",")[1].trim().split(":"); // Get time part, then split by colon

        // Assuming locale (MM/DD/YYYY, HH:MM:SS AM/PM)
        if (dateParts.length === 3 && timeParts.length === 3) {
            const mm = dateParts[0];
            const dd = dateParts[1];
            const yyyy = dateParts[2];
            const hh = timeParts[0];
            const min = timeParts[1];
            const ss = timeParts[2];

            // Reformat to YYYY-MM-DD HH:mm:ss
            tsDb = `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')} ${hh.padStart(2, '0')}:${min.padStart(2, '0')}:${ss.padStart(2, '0')}`;
        }
    }
    const msg  = activeLogRow.querySelector(".log-message")?.textContent?.trim() || "";
    ctx.innerHTML = `
      <div style="display:flex; gap:12px;">
          <div style="min-width:165px; font-weight:500;">${tsDb}</div>
          <div>${msg}</div>
      </div>
    `;
    // ------------------------

    modal.show();
    setTimeout(() => txt.focus(), 150);
  });

    saveBtn.addEventListener("click", async () => {
      const comment = (txt.value || "").trim();
      if (!activeLogRow) return;

      const logId = activeLogRow.dataset.logId;
      if (!logId) {
        showToast("Missing log id (API must return 'id').", "danger");
        return;
      }

      const res = await fetch(`/planner/api/logs/${logId}/comment/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": CSRF_TOKEN,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comment }),
      });

      const data = await res.json();
      if (!data.ok) {
        showToast(data.message || "Unable to save comment", "danger");
        return;
      }

      // update UI with saved value from server
      const saved = (data.comment || "").trim();
      activeLogRow.dataset.comment = saved;

      const preview = activeLogRow.querySelector(".log-comment-preview");
      const btn = activeLogRow.querySelector(".log-comment-btn");

      if (saved) {
        preview.textContent = truncateText(saved, 120);
        btn.classList.remove("comment-hidden");
      } else {
        preview.textContent = "";
        btn.classList.add("comment-hidden");
      }

      showToast("Comment saved", "success", 1500);
      modal.hide();
    });




  document.getElementById("undoBtn").addEventListener("click",async()=>{
    const r=await fetch("/planner/api/undo/",{method:"POST",headers:{"X-CSRFToken":CSRF_TOKEN}});
    const data=await r.json();
    if(data.ok){
      appendLogs(data.logs);
      currentUsedSessions = data.used_sessions;
      renderSessionList();
      refreshCurrentDay();
      updateSessionTypeCounters();
      loadLogHistory();
    } else showToast("Nothing to undo","danger");
  });

  // CSV Import (Sessionboard) modal: open icon -> file selection -> preview stats + sample
  const openIcon = document.querySelector(".open-icon");
  const csvImportModalEl = document.getElementById("csvImportModal");
  const csvImportFile = document.getElementById("csvImportFile");
  const csvImportStep1 = document.getElementById("csvImportStep1");
  const csvImportStep2 = document.getElementById("csvImportStep2");
  const csvImportStep1Error = document.getElementById("csvImportStep1Error");
  const csvImportRowCount = document.getElementById("csvImportRowCount");
  const csvImportColCount = document.getElementById("csvImportColCount");
  const csvImportThead = document.getElementById("csvImportThead");
  const csvImportTbody = document.getElementById("csvImportTbody");
  const csvImportChooseAnother = document.getElementById("csvImportChooseAnother");
  const csvImportRunBtn = document.getElementById("csvImportRunBtn");
  const csvImportStep2Error = document.getElementById("csvImportStep2Error");
  const csvImportReplaceAll = document.getElementById("csvImportReplaceAll");
  const csvImportStats = document.getElementById("csvImportStats");
  let csvPreviewStats = null;

  function updateCsvImportStats() {
    if (!csvImportStats || !csvPreviewStats) return;
    const y = csvPreviewStats.row_count;
    const x = csvPreviewStats.current_session_count;
    const a = csvPreviewStats.new_count;
    const b = csvPreviewStats.existing_count;
    const d = csvPreviewStats.dummy_count;
    const dummyNote = d > 0 ? ` · ${d} dummy ignored` : "";
    if (csvImportReplaceAll?.checked) {
      csvImportStats.innerHTML =
        `<i class="bi bi-exclamation-triangle-fill text-warning me-1" aria-hidden="true"></i>` +
        `Replace all: Will replace all ${x} existing sessions with ${y} rows from file${dummyNote}`;
    } else {
      csvImportStats.textContent =
        `Merge: Will add ${a} new · skip ${b} already existing${dummyNote} · ${y} rows in file`;
    }
  }

  if (openIcon && csvImportModalEl) {
    openIcon.style.cursor = "pointer";
    openIcon.setAttribute("title", "Import from SessionBoard");
    openIcon.addEventListener("click", () => {
      csvImportStep1.style.display = "block";
      csvImportStep2.style.display = "none";
      csvImportStep1Error.style.display = "none";
      csvImportStep1Error.textContent = "";
      csvImportFile.value = "";
      csvPreviewStats = null;
      if (csvImportReplaceAll) csvImportReplaceAll.checked = true;
      if (csvImportStats) csvImportStats.textContent = "";
      new bootstrap.Modal(csvImportModalEl).show();
    });
  }

  if (csvImportReplaceAll) {
    csvImportReplaceAll.addEventListener("change", updateCsvImportStats);
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }
  function escapeHtmlAttr(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/\r?\n/g, " ");
  }
  function truncateCell(s, maxLen) {
    const str = s == null ? "" : String(s);
    if (str.length <= maxLen) return str;
    return str.slice(0, maxLen) + "\u2026";
  }
  const CSV_PREVIEW_CELL_MAX_LEN = 50;

  if (csvImportFile) {
    csvImportFile.addEventListener("change", async () => {
      const file = csvImportFile.files && csvImportFile.files[0];
      csvImportStep1Error.style.display = "none";
      csvImportStep1Error.textContent = "";
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".csv")) {
        csvImportStep1Error.textContent = "Please select a .csv file.";
        csvImportStep1Error.style.display = "block";
        return;
      }
      const formData = new FormData();
      formData.append("file", file);
      setPlannerBusyVisible(true, "Loading preview…");
      try {
        const res = await fetch(CSV_PREVIEW_URL, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          body: formData,
        });
        const text = await res.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (parseErr) {
          csvImportStep1Error.textContent =
            `Server error (HTTP ${res.status}). Response was not JSON — check server logs.`;
          csvImportStep1Error.style.display = "block";
          return;
        }
        if (!res.ok) {
          csvImportStep1Error.textContent = data.error || "Preview failed.";
          csvImportStep1Error.style.display = "block";
          return;
        }
        csvImportRowCount.textContent = data.row_count ?? 0;
        csvImportColCount.textContent = data.col_count ?? 0;
        csvPreviewStats = {
          row_count: data.row_count ?? 0,
          current_session_count: data.current_session_count ?? 0,
          new_count: data.new_count ?? 0,
          existing_count: data.existing_count ?? 0,
          dummy_count: data.dummy_count ?? 0,
        };
        if (csvImportReplaceAll) csvImportReplaceAll.checked = true;
        updateCsvImportStats();
        const headers = data.headers || [];
        const rows = data.rows || [];
        const colCount = headers.length;
        csvImportThead.innerHTML = headers.map(h => `<th scope="col" title="${escapeHtmlAttr(h)}">${escapeHtml(truncateCell(h, CSV_PREVIEW_CELL_MAX_LEN))}</th>`).join("");
        csvImportTbody.innerHTML = rows.map(row => {
          const arr = Array.isArray(row) ? row : [];
          const cells = [];
          for (let c = 0; c < colCount; c++) {
            const raw = arr[c] ?? "";
            const truncated = truncateCell(raw, CSV_PREVIEW_CELL_MAX_LEN);
            cells.push(`<td title="${escapeHtmlAttr(raw)}">${escapeHtml(truncated)}</td>`);
          }
          return "<tr>" + cells.join("") + "</tr>";
        }).join("");
        const tableEl = csvImportThead?.closest("table");
        if (tableEl) tableEl.style.width = Math.max(colCount * 130, 800) + "px";
        csvImportStep1.style.display = "none";
        csvImportStep2.style.display = "block";
      } catch (err) {
        csvImportStep1Error.textContent =
          "Network error: " +
          (err.message || "Could not reach server.") +
          " (Check that the app is running, URL is correct, and browser is not blocking the request.)";
        csvImportStep1Error.style.display = "block";
      } finally {
        setPlannerBusyVisible(false);
      }
    });
  }

  if (csvImportChooseAnother) {
    csvImportChooseAnother.addEventListener("click", () => {
      csvImportStep2.style.display = "none";
      csvImportStep1.style.display = "block";
      csvImportStep1Error.style.display = "none";
      csvImportFile.value = "";
      csvPreviewStats = null;
      if (csvImportReplaceAll) csvImportReplaceAll.checked = true;
      if (csvImportStats) csvImportStats.textContent = "";
    });
  }

  if (csvImportRunBtn && csvImportFile) {
    csvImportRunBtn.addEventListener("click", async () => {
      const file = csvImportFile.files && csvImportFile.files[0];
      if (csvImportStep2Error) {
        csvImportStep2Error.style.display = "none";
        csvImportStep2Error.textContent = "";
      }
      if (!file || !file.name.toLowerCase().endsWith(".csv")) {
        if (csvImportStep2Error) {
          csvImportStep2Error.textContent = "Please choose a CSV file first.";
          csvImportStep2Error.style.display = "block";
        }
        return;
      }
      csvImportRunBtn.disabled = true;
      setPlannerBusyVisible(true, "Importing…");
      const formData = new FormData();
      formData.append("file", file);
      formData.append("replace_all", csvImportReplaceAll?.checked ? "1" : "0");
      try {
        const res = await fetch(CSV_IMPORT_URL, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          body: formData,
        });
        const text = await res.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (parseErr) {
          setPlannerBusyVisible(false);
          if (csvImportStep2Error) {
            csvImportStep2Error.textContent =
              `Server error (HTTP ${res.status}). Response was not JSON — check server logs.`;
            csvImportStep2Error.style.display = "block";
          }
          csvImportRunBtn.disabled = false;
          return;
        }
        if (!res.ok) {
          setPlannerBusyVisible(false);
          if (csvImportStep2Error) {
            csvImportStep2Error.textContent = data.error || "Import failed.";
            csvImportStep2Error.style.display = "block";
          }
          csvImportRunBtn.disabled = false;
          return;
        }
        bootstrap.Modal.getInstance(csvImportModalEl)?.hide();
        csvImportStep2.style.display = "none";
        csvImportStep1.style.display = "block";
        csvImportFile.value = "";
        try {
          sessionStorage.setItem("importMessage", data.message || "Import completed.");
          sessionStorage.setItem("importNullCount", String(data.session_type_null_count || 0));
        } catch (e) {}
        window.location.reload();
        return;
      } catch (err) {
        setPlannerBusyVisible(false);
        if (csvImportStep2Error) {
          csvImportStep2Error.textContent =
            "Network error: " +
            (err.message || "Could not reach server.") +
            " (Check server/proxy timeout for large imports.)";
          csvImportStep2Error.style.display = "block";
        }
      }
      csvImportRunBtn.disabled = false;
    });
  }

  const exportLink = document.querySelector(".export-link");
  if (exportLink) {
    exportLink.addEventListener("click", async (e) => {
      e.preventDefault();
      const url = exportLink.getAttribute("href") || EXPORT_EXCEL_URL;
      setPlannerBusyVisible(true, "Building Excel…");
      try {
        const res = await fetch(url, { method: "GET", credentials: "same-origin" });
        if (!res.ok) {
          const errText = await res.text();
          let detail = `Export failed (HTTP ${res.status}).`;
          try {
            const j = JSON.parse(errText);
            if (j.detail || j.error) detail = String(j.detail || j.error);
          } catch (x) {
            if (errText && errText.length < 240 && errText.indexOf("<") === -1) detail = errText;
          }
          showToast(detail, "danger", 4500);
          return;
        }
        const blob = await res.blob();
        const cd = res.headers.get("Content-Disposition");
        const name = filenameFromContentDisposition(cd) || "grid-export.xlsx";
        const objUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objUrl;
        a.download = name;
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(objUrl);
      } catch (err) {
        showToast("Network error: " + (err.message || "Could not export."), "danger", 4500);
      } finally {
        setPlannerBusyVisible(false);
      }
    });
  }
});