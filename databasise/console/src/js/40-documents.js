WIRED["documents GET /log"] = true;
WIRED["documents GET /ledger/aliases"] = true;

var DocumentsScreen = (function () {
  var LIMIT = 26214400;
  var ID_RE = /^[A-Za-z0-9_-]+$/;
  var MSG = {
    noText: "Enter document text.",
    bigText: "Text is larger than 26,214,400 bytes.",
    badId: "Document id may contain only letters, digits, underscore and hyphen.",
    emptyFile: "The file is empty. Choose a file with content.",
    bigFile: "The file is larger than 26,214,400 bytes.",
    noFile: "Choose a file.",
    noJob: "Enter a job id.",
    pageSize: "Page size must be between 1 and 100.",
  };
  var NOTICE = {
    lightrag: "File upload does not index the file for LightRAG today; the file is not parsed.",
    hipporag: "Raw upload is refused for HippoRAG selectors. Use Paste text.",
    unknown: "The server resolves this selector's store at run time; it may refuse a raw upload. Paste text works for every store.",
  };
  var CARD_NOTE = {
    lightrag: "enqueued is not a success signal; check the job row status.",
    hipporag: "HippoRAG ingest finished synchronously; its job has no status record.",
    unknown: "enqueued is not a success signal; the job may have no status record, depending on the store the selector resolves to.",
  };
  var DELETE_TAIL = {
    lightrag: "This removes it from the v1 corpus and cannot be undone. The query stores are not changed; the deleted document's chunks can stay resolvable.",
    hipporag: "This removes it from the HippoRAG stores and cannot be undone.",
    unknown: "This removes it from the store the selector resolves to and cannot be undone.",
  };
  var TARGET = { lightrag: "LightRAG", hipporag: "HippoRAG", unknown: "resolved by the server at run time" };
  var SEAM_NODE = { lightrag: "the v1 delete node", hipporag: "the HippoRAG delete node", unknown: "the delete node" };
  var STATUS_STATE = { processed: "ok", failed: "fail", processing: "progress", parsing: "progress", analyzing: "progress", pending: "neutral", preprocessed: "neutral", interrupted: "warn" };
  var STATUS_GLYPH = { ok: "✓", fail: "✕", progress: "●", neutral: "■", warn: "▲" };
  var DELETE_STATE = { success: "ok", not_found: "neutral", not_allowed: "fail", fail: "fail" };
  var NON_TERMINAL = ["pending", "parsing", "analyzing", "processing", "preprocessed"];
  var UPLOADING = "Uploading and processing. A LightRAG ingest waits for the model and can take minutes.";
  var POLL_RUNNING = "Refreshing every 30 seconds.";
  var POLL_STOPPED = "Stopped: every document has a final status.";
  var PREVIEW_TEXT_CAP = 300;

  var root = $id("screen-documents");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var layout = root.querySelector('[data-role="layout"]');
  var panes = { paste: root.querySelector('[data-role="pane-paste"]'), upload: root.querySelector('[data-role="pane-upload"]') };
  var card = ID("result.card");
  var dialog = $id("shell.dialog.delete");
  var confirmButton = $id("shell.dialog.delete-confirm");
  var cancelButton = $id("shell.dialog.delete-cancel");
  var jobs = SessionLog("databasise.console.jobs", 50);
  var picker = null;
  var invalid = { paste: true, upload: true }; // a client-side check fails; the write gate is added in syncWrites
  var pending = null; // the delete the open dialog asks about: {id, selector, kind, label, from}
  var sending = false; // the confirmed delete is in flight; it is never aborted
  var job = null; // the last page that loaded: {id, offset, limit, body}
  var readCtl = null; // the abort handle of the job read in flight
  var jobsShown = "none";
  var lastSize = 50;
  var pollTimer = null;

  function ID(name) {
    return $id("documents." + name);
  }

  function bytes(text) {
    return new TextEncoder().encode(text).length;
  }

  function grouped(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function badge(el, state, text) {
    el.setAttribute("data-state", state);
    el.textContent = STATUS_GLYPH[state] + " " + text;
  }

  // ---- errors ----

  function showError(status, body, opts) {
    var shape = renderError("documents", status, body, opts);
    errorsBox.hidden = shape === "result";
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
    return shape;
  }

  // renderError clears every field message, so the client-side checks are rerun afterwards.
  function hideErrors() {
    renderError("documents", 200, null);
    errorsBox.hidden = true;
    refresh();
  }

  // ---- ingest checks and previews ----

  var text = ID("paste.text");
  var pasteId = ID("paste.document-id");
  var file = ID("upload.file");
  var uploadId = ID("upload.document-id");
  var pasteSubmit = ID("paste.submit");
  var uploadSubmit = ID("upload.submit");

  function idMessage(value) {
    return value !== "" && !ID_RE.test(value) ? MSG.badId : "";
  }

  // An alias (or an unresolved selector) has no arm client-side; only the server knows its store type (R18-05).
  function family() {
    var arm = picker && picker.arm();
    if (!arm) return "unknown";
    return arm === "hipporag" ? "hipporag" : "lightrag";
  }

  function textMessage() {
    if (text.value.trim() === "") return MSG.noText;
    return bytes(text.value) > LIMIT ? MSG.bigText : "";
  }

  function fileMessage() {
    var f = file.files[0];
    if (!f) return MSG.noFile;
    if (f.size === 0) return MSG.emptyFile;
    return f.size > LIMIT ? MSG.bigFile : "";
  }

  // The body POST /documents receives. The Default selector is sent as null.
  function pasteRequest() {
    var doc = { text: text.value };
    if (pasteId.value !== "") doc.document_id = pasteId.value;
    return { document: doc, selector: picker.value() };
  }

  // The same body, with a long text cut for display.
  function pastePreview() {
    var req = pasteRequest();
    var shown = req.document.text;
    if (shown.length > PREVIEW_TEXT_CAP) shown = shown.slice(0, PREVIEW_TEXT_CAP) + "... (" + grouped(shown.length - PREVIEW_TEXT_CAP) + " more characters not shown)";
    req.document.text = shown;
    return JSON.stringify(req, null, 2);
  }

  // The selector field is omitted for the Default selector; it never reads null or [].
  function uploadFields() {
    var f = file.files[0];
    var lines = ["POST /documents/upload (multipart/form-data)", "file: " + (f ? f.name + " (" + grouped(f.size) + " bytes)" : "(none chosen)")];
    if (uploadId.value !== "") lines.push("document_id: " + uploadId.value);
    var selector = picker.value();
    if (selector !== null) lines.push("selector: " + JSON.stringify(selector));
    return lines.join("\n");
  }

  function refresh() {
    if (!picker) return;
    var kind = family();
    var blockers = picker.blockers();
    setFieldError(ID("selector.group"), blockers[0] || "");
    ID("selector.family").textContent = "Target: " + TARGET[kind];

    var tm = textMessage();
    var im = idMessage(pasteId.value);
    setFieldError(text, tm);
    setFieldError(pasteId, im);
    ID("paste.bytes").textContent = grouped(bytes(text.value)) + " of 26,214,400 bytes";
    ID("paste.request-preview").textContent = pastePreview();
    invalid.paste = tm !== "" || im !== "" || blockers.length > 0;

    var fm = fileMessage();
    var um = idMessage(uploadId.value);
    setFieldError(file, fm);
    setFieldError(uploadId, um);
    ID("upload.notice").textContent = NOTICE[kind];
    ID("upload.request-preview").textContent = uploadFields();
    invalid.upload = fm !== "" || um !== "" || blockers.length > 0 || kind === "hipporag";
    syncWrites();
  }

  // D-13 / LIVE-05: while any ingest, upload or delete is in flight, every control that starts a write is disabled with a visible
  // reason. This leaves field messages alone, so it can run on every InFlight change.
  function syncWrites() {
    var writing = InFlight.writing();
    setDisabled(pasteSubmit, writing || invalid.paste);
    setDisabled(uploadSubmit, writing || invalid.upload);
    setDisabled(ID("delete.submit"), writing);
    Array.prototype.forEach.call(ID("jobs.documents").querySelectorAll('[data-mock-id^="documents.jobs.delete-"]'), function (button) {
      setDisabled(button, writing);
    });
    Array.prototype.forEach.call(root.querySelectorAll('[data-role="write-note"]'), function (note) {
      note.hidden = !writing;
    });
    syncDialog();
  }

  // The dialog's Confirm waits for any write; once its own delete is sent both buttons wait for the answer (D-14).
  function syncDialog() {
    var writing = InFlight.writing();
    setDisabled(confirmButton, writing || sending);
    setDisabled(cancelButton, sending);
    if (sending) confirmButton.setAttribute("aria-busy", "true");
    else confirmButton.removeAttribute("aria-busy");
    confirmButton.querySelector(".spinner").hidden = !sending;
    dialog.querySelector('[data-role="sending"]').hidden = !sending;
    dialog.querySelector('[data-role="write-note"]').hidden = !writing || sending;
  }

  function showTab(name) {
    ["paste", "upload"].forEach(function (n) {
      panes[n].hidden = n !== name;
      ID("tabs." + n).setAttribute("aria-selected", String(n === name));
    });
  }

  // ---- ingest flight and result card ----

  function setBusy(on) {
    [pasteSubmit, uploadSubmit].forEach(function (button) {
      if (on) button.setAttribute("aria-busy", "true");
      else button.removeAttribute("aria-busy");
    });
  }

  function submitTime() {
    var d = new Date();
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
  }

  function showCard(sent, kind) {
    card.querySelector('[data-role="job-id"]').textContent = sent.job.job_id;
    card.querySelector('[data-role="enqueued"]').textContent = String(sent.job.enqueued);
    card.querySelector('[data-role="note"]').textContent = CARD_NOTE[kind];
    setDisabled(ID("result.open-job"), kind === "hipporag");
    card.hidden = false;
    jobs.add({ job_id: sent.job.job_id, document_id: sent.documentId, selector: sent.label, timestamp: submitTime(), enqueued: sent.job.enqueued });
    renderList();
  }

  // A write is never aborted once sent: no signal is passed.
  function finishIngest(result, sent, kind) {
    ID("state.in-flight").hidden = true;
    ID("upload.progress").hidden = true;
    setBusy(false);
    var body = result.body;
    if (result.status >= 200 && result.status < 300 && body !== null && typeof body === "object" && typeof body.job_id === "string") {
      sent.job = body;
      showCard(sent, kind);
      // Only LightRAG documents are listed by Corpus & Health, which then reloads its table and counts; an unknown store may be LightRAG.
      if (kind !== "hipporag") Console.emit("corpus-changed");
      return;
    }
    if (showError(result.status, body) === "result") showError(0, null, { text: "The server answered without a job id." });
  }

  function submitPaste() {
    if (pasteSubmit.disabled) return;
    hideErrors();
    card.hidden = true;
    var sent = { documentId: pasteId.value, label: picker.label() };
    var kind = family();
    var request = pasteRequest();
    setBusy(true);
    ID("state.in-flight").hidden = false;
    api("POST", "/documents", request, { kind: "ingest" }).then(function (result) {
      finishIngest(result, sent, kind);
    });
  }

  // fetch reports no upload progress, so the line is indeterminate: the <progress> has no value attribute (18-RESEARCH Pitfall 7).
  // The body is a FormData with no hand-set Content-Type, so the browser adds the multipart boundary.
  function submitUpload() {
    if (uploadSubmit.disabled) return;
    hideErrors();
    card.hidden = true;
    var sent = { documentId: uploadId.value, label: picker.label() };
    var kind = family();
    var form = new FormData();
    form.append("file", file.files[0]);
    if (uploadId.value !== "") form.append("document_id", uploadId.value);
    var selector = picker.value();
    if (selector !== null) form.append("selector", JSON.stringify(selector));
    setBusy(true);
    var box = ID("upload.progress");
    box.querySelector("progress").removeAttribute("value");
    box.querySelector('[data-role="spin"]').hidden = true;
    box.querySelector('[data-role="text"]').textContent = UPLOADING;
    box.hidden = false;
    api("POST", "/documents/upload", form, { kind: "ingest" }).then(function (result) {
      finishIngest(result, sent, kind);
    });
  }

  // ---- jobs drawer ----

  // Closing the drawer stops the poll and drops a read in flight; it never reopens by itself (IN-JSB-05).
  function setDrawer(open) {
    ID("jobs.drawer").hidden = !open;
    layout.setAttribute("data-drawer", open ? "open" : "closed");
    ID("jobs.open").setAttribute("aria-expanded", String(open));
    if (!open) leaveJobs();
  }

  function leaveJobs() {
    ID("jobs.poll").checked = false;
    syncPoll();
    if (!readCtl) return;
    readCtl.abort();
    readCtl = null;
    jobView(jobsShown);
  }

  function isFinal(doc) {
    return NON_TERMINAL.indexOf(doc.status) < 0; // a status the console does not know counts as final
  }

  // The poll runs only while its box is checked (the box is in the open drawer). It stops by itself on a page whose documents all have a
  // final status, and starts again if a later load shows one that has not. Each load restarts the 30 s interval.
  function syncPoll() {
    clearInterval(pollTimer);
    pollTimer = null;
    var note = ID("live.jobs-polled");
    if (!ID("jobs.poll").checked) {
      note.textContent = "";
      return;
    }
    if (job && job.body.documents.every(isFinal)) {
      note.textContent = POLL_STOPPED;
      return;
    }
    note.textContent = POLL_RUNNING;
    pollTimer = setInterval(function () {
      if (job) loadJob(job.id, job.offset);
    }, 30000);
  }

  // The client-side job list, newest first (D-07). A row's id and meta are filled here; its Open button reads the id at press time.
  function renderList() {
    var entries = jobs.all();
    ensureRows(ID("jobs.list"), entries.length).forEach(function (slot, i) {
      slot.querySelector('[data-role="id"]').textContent = entries[i].job_id;
      slot.querySelector('[data-role="meta"]').textContent = "submitted " + entries[i].timestamp + ", enqueued " + entries[i].enqueued + ", selector " + entries[i].selector;
    });
  }

  // Previous and Next follow the last page that loaded, so a failed read leaves them as they were.
  function pagerState() {
    var next = job ? job.body.next_offset : null;
    setDisabled(ID("jobs.prev"), !job || job.offset <= 0);
    setDisabled(ID("jobs.next"), next === null || next === undefined);
  }

  // The count line has no total: GET /jobs/{job_id} returns none (18-RESEARCH Pitfall 4).
  function paintRange(name) {
    var range = root.querySelector('[data-role="range"]');
    range.hidden = name !== "table" || !job;
    if (!range.hidden) range.textContent = "Showing " + (job.offset + 1) + " to " + (job.offset + job.body.documents.length);
  }

  // "loading" keeps the previous rows on screen (Request States); every other name replaces the view.
  function jobView(name) {
    var loading = name === "loading";
    ID("jobs.loading").hidden = !loading;
    ID("jobs.documents").setAttribute("aria-busy", String(loading));
    setDisabled(ID("jobs.refresh"), loading);
    if (loading) {
      root.querySelector('[data-role="no-job"]').hidden = true;
      setDisabled(ID("jobs.prev"), true);
      setDisabled(ID("jobs.next"), true);
      return;
    }
    jobsShown = name;
    ID("jobs.empty").hidden = name !== "empty";
    root.querySelector('[data-role="no-job"]').hidden = name !== "none";
    root.querySelector('[data-role="table-wrap"]').hidden = name !== "table";
    ID("jobs.counts").hidden = name !== "table" && name !== "empty";
    paintRange(name);
    pagerState();
  }

  function fillRows(docs) {
    ensureRows(ID("jobs.documents").tBodies[0], docs.length).forEach(function (row, i) {
      var doc = docs[i];
      row.querySelector('[data-role="id"]').textContent = doc.document_id;
      badge(row.querySelector('[data-role="status"]'), STATUS_STATE[doc.status] || "neutral", doc.status);
      row.querySelector('[data-role="updated"]').textContent = doc.updated_at;
      var toggle = row.querySelector('[data-mock-id^="documents.jobs.error-toggle-"]');
      var reason = row.querySelector('[data-role="error"]');
      toggle.hidden = !doc.error_message;
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Show error";
      reason.textContent = doc.error_message || "";
      reason.hidden = true;
    });
    syncWrites(); // a cloned row's Delete follows the write gate too
  }

  function fillCounts(counts) {
    var bar = ID("jobs.counts").querySelector('[data-role="bar"]');
    var chips = ID("jobs.counts").querySelector('[data-role="chips"]');
    clearNode(bar);
    clearNode(chips);
    var keys = Object.keys(counts);
    var total = keys.reduce(function (sum, key) {
      return sum + counts[key];
    }, 0);
    keys.forEach(function (key) {
      var state = STATUS_STATE[key] || "neutral";
      var segment = h("span");
      segment.setAttribute("data-state", state);
      segment.title = key + " " + counts[key];
      segment.style.setProperty("--w", (total ? (counts[key] / total) * 100 : 0) + "%");
      bar.appendChild(segment);
      var chip = h("span", key + " " + counts[key], "chip");
      chip.setAttribute("data-state", state);
      chips.appendChild(chip);
    });
  }

  function paintJob() {
    var docs = job.body.documents;
    ID("jobs.job-id").value = job.id;
    setFieldError(ID("jobs.job-id"), "");
    fillRows(docs);
    fillCounts(job.body.counts || {});
    jobView(docs.length ? "table" : "empty");
    syncPoll();
  }

  // WR-JSB-03: a read that failed leaves the last page that loaded on screen, with its pager state and its job id in the input.
  function restoreJob() {
    if (job) paintJob();
    else jobView("none");
  }

  // Reads one page of a job. A newer read supersedes the one in flight.
  function loadJob(id, offset) {
    var input = ID("jobs.job-id");
    id = id.trim();
    if (id === "") return setFieldError(input, MSG.noJob);
    offset = offset || 0;
    if (readCtl) readCtl.abort();
    var mine = (readCtl = new AbortController());
    hideErrors();
    setFieldError(input, "");
    setDrawer(true);
    jobView("loading");
    api("GET", "/jobs/" + encodeURIComponent(id) + "?limit=" + lastSize + "&offset=" + offset, null, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== readCtl) return;
      readCtl = null;
      var body = result.body;
      if (result.status >= 200 && result.status < 300 && body !== null && typeof body === "object" && Array.isArray(body.documents)) {
        job = { id: id, offset: offset, limit: lastSize, body: body };
        return paintJob();
      }
      restoreJob();
      if (showError(result.status, body) === "result") showError(0, null, { text: "The server answered without a document list." });
    });
  }

  function checkSize() {
    var input = ID("jobs.page-size");
    var raw = input.value.trim();
    var n = Number(raw);
    var ok = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100;
    setFieldError(input, ok ? "" : MSG.pageSize);
    if (ok) lastSize = n;
  }

  // ---- delete ----

  // Opens the dialog for one delete. The request is built and sent only in the Confirm handler; a dismiss or Escape before it sends
  // nothing (WR-JSB-02, T-18-20). The id and selector are captured here, never read from the page at confirm time.
  function openDelete(p) {
    if (sending) return;
    pending = p;
    dialog.querySelector('[data-role="doc"]').textContent = p.id;
    dialog.querySelector('[data-role="sel"]').textContent = p.label;
    dialog.querySelector('[data-role="tail"]').textContent = DELETE_TAIL[p.kind];
    syncDialog();
    openDialog("shell.dialog.delete", "shell.dialog.delete-cancel");
  }

  function askDelete(documentId) {
    if (picker.blockers().length) return;
    openDelete({ id: documentId, selector: picker.value(), kind: family(), label: picker.label() });
  }

  function showDeleteOutcome(rec, kind) {
    var box = ID("delete.outcome");
    badge(box.querySelector('[data-role="status"]'), DELETE_STATE[rec.status] || "neutral", rec.status);
    box.querySelector('[data-role="doc"]').textContent = rec.document_id;
    box.querySelector('[data-role="message"]').textContent = rec.message || "The server returned no message.";
    ID("delete.seam-toggle").textContent = "Seam events, reported by " + SEAM_NODE[kind];
    var list = box.querySelector('[data-role="seam-list"]');
    clearNode(list);
    var events = Array.isArray(rec.seam_events) ? rec.seam_events : [];
    if (!events.length) list.appendChild(h("li", "No seam events."));
    events.forEach(function (event) {
      list.appendChild(h("li", event.component + ": " + event.outcome + (event.spend ? ", counted_by " + event.spend.counted_by : "")));
    });
    box.hidden = false;
  }

  function finishDelete(p, result) {
    if (p.from === "corpus") Console.show("documents");
    var body = result.body;
    if (result.status >= 200 && result.status < 300 && body !== null && typeof body === "object" && typeof body.status === "string") {
      showDeleteOutcome(body, p.kind);
      if (body.status === "success") Console.emit("corpus-changed");
      return;
    }
    ID("delete.outcome").hidden = true;
    if (showError(result.status, body) === "result") showError(0, null, { text: "The server answered without a deletion outcome." });
  }

  // Confirm sends the delete and keeps the dialog open, both buttons disabled and Escape ignored, until the answer arrives (D-14).
  // The request has no abort signal: a request that has been sent cannot be cancelled.
  function confirmDelete() {
    if (!pending || sending || confirmButton.disabled) return;
    var p = pending;
    sending = true;
    hideErrors();
    ID("delete.outcome").hidden = true;
    syncDialog();
    api("DELETE", "/documents/" + encodeURIComponent(p.id), { selector: p.selector }, { kind: "delete" }).then(function (result) {
      sending = false;
      dialog.close();
      syncWrites();
      finishDelete(p, result);
    });
  }

  // ---- wiring ----

  picker = Picker.attach("documents", function (p) {
    picker = p;
    refresh();
  });

  ID("tabs.paste").addEventListener("click", function () {
    showTab("paste");
  });
  ID("tabs.upload").addEventListener("click", function () {
    showTab("upload");
  });
  [text, pasteId, file, uploadId].forEach(function (input) {
    input.addEventListener("input", refresh);
    input.addEventListener("change", refresh);
  });
  pasteSubmit.addEventListener("click", submitPaste);
  uploadSubmit.addEventListener("click", submitUpload);
  ID("result.copy-job-id").addEventListener("click", function () {
    copyText(card.querySelector('[data-role="job-id"]').textContent, card.querySelector('[data-role="copied"]'));
  });
  ID("result.open-job").addEventListener("click", function () {
    loadJob(card.querySelector('[data-role="job-id"]').textContent);
  });

  ID("jobs.open").addEventListener("click", function () {
    setDrawer(true);
  });
  ID("jobs.close").addEventListener("click", function () {
    setDrawer(false);
    ID("jobs.open").focus();
  });
  ID("jobs.load").addEventListener("click", function () {
    loadJob(ID("jobs.job-id").value);
  });
  ID("jobs.job-id").addEventListener("keydown", function (event) {
    if (event.key === "Enter") loadJob(this.value);
  });
  // Refresh keeps the page being viewed when the job id is unchanged.
  ID("jobs.refresh").addEventListener("click", function () {
    var id = ID("jobs.job-id").value.trim();
    loadJob(id, job && job.id === id ? job.offset : 0);
  });
  ID("jobs.prev").addEventListener("click", function () {
    if (job) loadJob(job.id, Math.max(0, job.offset - job.limit));
  });
  ID("jobs.next").addEventListener("click", function () {
    if (job && typeof job.body.next_offset === "number") loadJob(job.id, job.body.next_offset);
  });
  ID("jobs.page-size").addEventListener("input", checkSize);
  ID("jobs.poll").addEventListener("change", syncPoll);
  // One delegated listener serves the literal slots and every cloned entry of the job list.
  ID("jobs.list").addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    loadJob(button.closest("li").querySelector('[data-role="id"]').textContent);
  });
  // One delegated listener serves the literal rows and every cloned row of the job table.
  ID("jobs.documents").addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    var mock = button.getAttribute("data-mock-id") || "";
    var row = button.closest("tr");
    if (mock.indexOf("documents.jobs.error-toggle-") === 0) {
      var open = button.getAttribute("aria-expanded") !== "true";
      row.querySelector('[data-role="error"]').hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      button.textContent = open ? "Hide error" : "Show error";
    } else if (mock.indexOf("documents.jobs.delete-") === 0) {
      askDelete(row.querySelector('[data-role="id"]').textContent);
    }
  });

  ID("delete.document-id").addEventListener("input", function () {
    setFieldError(this, idMessage(this.value));
  });
  ID("delete.submit").addEventListener("click", function () {
    var input = ID("delete.document-id");
    var value = input.value;
    if (value === "" || !ID_RE.test(value)) return setFieldError(input, MSG.badId);
    setFieldError(input, "");
    askDelete(value);
  });
  cancelButton.addEventListener("click", function () {
    if (!sending) dialog.close();
  });
  // Escape asks the dialog to cancel; it is ignored while the delete is in flight.
  dialog.addEventListener("cancel", function (event) {
    if (sending) event.preventDefault();
  });
  dialog.addEventListener("close", function () {
    // Chromium lets a repeated Escape through even when it was prevented; the dialog goes back up until the answer arrives.
    if (sending) return dialog.showModal();
    pending = null;
    syncDialog();
  });
  confirmButton.addEventListener("click", confirmDelete);

  wireErrors("documents");
  // Delete from Corpus & Health: that screen lists the default store, so the Default selector label applies.
  Console.on("delete-document", function (event) {
    openDelete({ id: event.document_id, selector: null, kind: "lightrag", label: "Default", from: "corpus" });
  });
  Console.on("inflight", syncWrites);
  Console.on("open-ingest", function () {
    Console.show("documents");
    showTab("paste");
  });
  // The pipeline status is a span, not a control, so the shared badge pass adds no reason line to it (D-09).
  Console.on("show", function (name) {
    if (name !== "documents") return leaveJobs();
    var wrap = ID("pipeline.status").closest("[data-needs-backend]");
    if (wrap && wrap.hasAttribute("data-route-absent")) ID("pipeline.status").textContent = "Needs " + wrap.getAttribute("data-needs-backend") + ".";
  });
  window.addEventListener("pagehide", function () {
    clearInterval(pollTimer);
  });

  renderList();
  jobView("none");
  checkSize();
  refresh();
  return {};
})();
Console.register("documents", DocumentsScreen);
