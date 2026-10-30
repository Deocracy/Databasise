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
  };
  var CARD_NOTE = {
    lightrag: "enqueued is not a success signal; check the job row status.",
    hipporag: "HippoRAG ingest finished synchronously; its job has no status record.",
  };
  var DELETE_TAIL = {
    lightrag: "This removes it from the v1 corpus and cannot be undone. The query stores are not changed; the deleted document's chunks can stay resolvable.",
    hipporag: "This removes it from the HippoRAG stores and cannot be undone.",
  };
  var STATUS_STATE = { processed: "ok", failed: "fail", processing: "progress", parsing: "progress", analyzing: "progress", pending: "neutral", preprocessed: "neutral", interrupted: "warn" };
  var STATUS_GLYPH = { ok: "✓", fail: "✕", progress: "●", neutral: "■", warn: "▲" };
  var DELETE_STATE = { success: "ok", not_found: "neutral", not_allowed: "fail", fail: "fail" };
  var JOB_FIXTURES = ["j-page1", "j-last", "j-single", "j-empty"];
  var PREVIEW_TEXT_CAP = 300;
  var FLIGHT_MS = 800;
  var LOAD_MS = 300;
  var CONFIRM_MS = 300;

  var root = $id("screen-documents");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var layout = root.querySelector('[data-role="layout"]');
  var panes = { paste: root.querySelector('[data-role="pane-paste"]'), upload: root.querySelector('[data-role="pane-upload"]') };
  var card = ID("result.card");
  var dialog = $id("shell.dialog.delete");
  var confirmButton = $id("shell.dialog.delete-confirm");
  var timers = [];
  var jobTimer = null;
  var jobsShown = "none";
  var sessionJobs = FIX.documents["session-jobs"].slice();
  var picker = null;
  var busy = false;
  var tab = "paste";
  var pending = null;
  var current = null;
  var lastSize = 50;
  var pollTimer = null;

  function ID(name) {
    return $id("documents." + name);
  }

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  function later(fn, ms) {
    timers.push(setTimeout(fn, ms));
  }

  // Ingest and delete timers; the job-load timer is separate so opening a job never cancels a submit in flight.
  function clearTimers() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function clearAll() {
    clearTimers();
    clearTimeout(jobTimer);
  }

  function outcome() {
    return ID("mock.outcome").value;
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

  function showError(status, body) {
    var shape = renderError("documents", status, body);
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

  // The mock outcome select decides which server response the next call gets; "success" (and "unknown job" outside Load job) returns null.
  function failure(op, field, refusalType) {
    var o = outcome();
    if (o === "refusal") {
      if (op === "job") return [422, { refusal_type: "PageSizeExceededError", message: "page size above the limit", requested: 500, limit: 100 }];
      if (op === "delete") return [409, { refusal_type: "StoreBusyError", message: "the store is in use by another process", store_kind: "graph" }];
      return [422, { refusal_type: "DuplicateDocumentIdError", message: "a document with this id already exists; delete it first", document_id: refusalType || "contract-2026-q1" }];
    }
    if (o === "validation") return [422, { detail: [{ loc: field, msg: "Field required", type: "missing" }] }];
    if (o === "server-failure") {
      return [502, { refusal_type: "ForeignEngineRefusalError", message: "operation '" + op + "' failed (CorpusOpSubprocessError)", operation: op, failure_class: "CorpusOpSubprocessError", cause: "the v1 driver exited with status 1" }];
    }
    if (o === "generic") return [500, "Internal Server Error"];
    return null;
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

  function family() {
    return picker && picker.arm() === "hipporag" ? "hipporag" : "lightrag";
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

  function pasteBody() {
    var shown = text.value;
    if (shown.length > PREVIEW_TEXT_CAP) shown = shown.slice(0, PREVIEW_TEXT_CAP) + "... (" + grouped(shown.length - PREVIEW_TEXT_CAP) + " more characters not shown)";
    var doc = { text: shown };
    if (pasteId.value !== "") doc.document_id = pasteId.value;
    var body = { document: doc };
    var selector = picker.value();
    if (selector !== null) body.selector = selector;
    return JSON.stringify(body, null, 2);
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
    ID("selector.family").textContent = "Target: " + (kind === "hipporag" ? "HippoRAG" : "LightRAG");

    var tm = textMessage();
    var im = idMessage(pasteId.value);
    setFieldError(text, tm);
    setFieldError(pasteId, im);
    ID("paste.bytes").textContent = grouped(bytes(text.value)) + " of 26,214,400 bytes";
    ID("paste.request-preview").textContent = pasteBody();
    setDisabled(pasteSubmit, busy || tm !== "" || im !== "" || blockers.length > 0);

    var fm = fileMessage();
    var um = idMessage(uploadId.value);
    setFieldError(file, fm);
    setFieldError(uploadId, um);
    ID("upload.notice").textContent = NOTICE[kind];
    ID("upload.request-preview").textContent = uploadFields();
    setDisabled(uploadSubmit, busy || fm !== "" || um !== "" || blockers.length > 0 || kind === "hipporag");
  }

  function showTab(name) {
    tab = name;
    ["paste", "upload"].forEach(function (n) {
      panes[n].hidden = n !== name;
      ID("tabs." + n).setAttribute("aria-selected", String(n === name));
    });
  }

  // ---- ingest flight and result card ----

  function setBusy(on) {
    busy = on;
    [pasteSubmit, uploadSubmit].forEach(function (button) {
      if (on) button.setAttribute("aria-busy", "true");
      else button.removeAttribute("aria-busy");
    });
    refresh();
  }

  function submitTime() {
    var d = new Date();
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
  }

  function showCard(job) {
    var kind = family();
    card.querySelector('[data-role="job-id"]').textContent = job.job_id;
    card.querySelector('[data-role="enqueued"]').textContent = String(job.enqueued);
    card.querySelector('[data-role="note"]').textContent = CARD_NOTE[kind];
    setDisabled(ID("result.open-job"), kind === "hipporag");
    card.hidden = false;
    sessionJobs = sessionJobs.filter(function (j) {
      return j.job_id !== job.job_id;
    });
    sessionJobs.unshift({ job_id: job.job_id, submitted: submitTime(), enqueued: job.enqueued });
    sessionJobs = sessionJobs.slice(0, 3);
    renderList();
  }

  function finishIngest(field) {
    ID("state.in-flight").hidden = true;
    ID("upload.progress").hidden = true;
    setBusy(false);
    var bad = failure("ingest", field);
    if (bad) return showError(bad[0], bad[1]);
    showCard(FIX.documents["ingest-success"]);
  }

  function submitPaste() {
    if (busy || pasteSubmit.disabled) return;
    clearTimers();
    hideErrors();
    card.hidden = true;
    setBusy(true);
    ID("state.in-flight").hidden = false;
    later(function () {
      finishIngest(["body", "document", "text"]);
    }, FLIGHT_MS);
  }

  function submitUpload() {
    if (busy || uploadSubmit.disabled) return;
    clearTimers();
    hideErrors();
    card.hidden = true;
    setBusy(true);
    var box = ID("upload.progress");
    var bar = box.querySelector("progress");
    var spin = box.querySelector('[data-role="spin"]');
    var label = box.querySelector('[data-role="text"]');
    spin.hidden = true;
    bar.hidden = false;
    box.hidden = false;
    var pct = 0;
    (function step() {
      pct += 20;
      if (pct < 100) {
        bar.value = pct;
        label.textContent = "Uploading " + pct + "%";
        return later(step, 150);
      }
      bar.value = 100;
      bar.hidden = true;
      spin.hidden = false;
      label.textContent = "Processing";
      later(function () {
        finishIngest(["body", "file"]);
      }, FLIGHT_MS);
    })();
  }

  // ---- jobs drawer ----

  function setDrawer(open) {
    ID("jobs.drawer").hidden = !open;
    layout.setAttribute("data-drawer", open ? "open" : "closed");
    ID("jobs.open").setAttribute("aria-expanded", String(open));
  }

  function renderList() {
    var slots = ID("jobs.list").querySelectorAll('[data-role="slot"]');
    Array.prototype.forEach.call(slots, function (slot, i) {
      var job = sessionJobs[i];
      slot.hidden = !job;
      if (!job) return;
      slot.querySelector('[data-role="id"]').textContent = job.job_id;
      slot.querySelector('[data-role="meta"]').textContent = "submitted " + job.submitted + ", enqueued " + job.enqueued;
    });
  }

  function jobView(name) {
    var loading = name === "loading";
    if (!loading) jobsShown = name;
    ID("jobs.loading").hidden = !loading;
    ID("jobs.empty").hidden = name !== "empty";
    root.querySelector('[data-role="no-job"]').hidden = name !== "none";
    root.querySelector('[data-role="table-wrap"]').hidden = name !== "table";
    ID("jobs.documents").setAttribute("aria-busy", String(loading));
    ID("jobs.counts").hidden = name !== "table" && name !== "empty";
    if (loading) {
      setDisabled(ID("jobs.prev"), true);
      setDisabled(ID("jobs.next"), true);
    }
  }

  function fillRows(docs) {
    var rows = ID("jobs.documents").tBodies[0].rows;
    Array.prototype.forEach.call(rows, function (row, i) {
      var doc = docs[i];
      row.hidden = !doc;
      if (!doc) return;
      row.querySelector('[data-role="id"]').textContent = doc.document_id;
      badge(row.querySelector('[data-role="status"]'), STATUS_STATE[doc.status] || "neutral", doc.status);
      row.querySelector('[data-role="updated"]').textContent = doc.updated_at;
      var toggle = ID("jobs.error-toggle-" + (i + 1));
      var reason = row.querySelector('[data-role="error"]');
      toggle.hidden = !doc.error_message;
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Show error";
      reason.textContent = doc.error_message || "";
      reason.hidden = true;
    });
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

  function renderJob(name) {
    var rec = FIX.documents[name];
    current = { name: name, rec: rec };
    setDrawer(true);
    hideErrors();
    ID("jobs.job-id").value = rec.job_id;
    setFieldError(ID("jobs.job-id"), "");
    fillRows(rec.documents);
    fillCounts(rec.counts);
    setDisabled(ID("jobs.prev"), rec.offset <= 0);
    setDisabled(ID("jobs.next"), rec.next_offset === null);
    jobView(rec.documents.length ? "table" : "empty");
  }

  function fixtureFor(id, next) {
    if (id === FIX.documents["j-page1"].job_id) return next === "last" ? "j-last" : "j-page1";
    var found = JOB_FIXTURES.filter(function (n) {
      return FIX.documents[n].job_id === id;
    })[0];
    return found || null;
  }

  function loadJob(id, which) {
    var input = ID("jobs.job-id");
    id = id.trim();
    if (id === "") return setFieldError(input, MSG.noJob);
    setFieldError(input, "");
    clearTimeout(jobTimer);
    hideErrors();
    setDrawer(true);
    jobView("loading");
    jobTimer = setTimeout(function () {
      var bad = failure("job", ["path", "job_id"]);
      var name = fixtureFor(id, which);
      if (bad || outcome() === "unknown-job" || !name) {
        jobView(jobsShown);
        if (bad) return showError(bad[0], bad[1]);
        return showError(FIX.documents["j-unknown"].status, Object.assign({}, FIX.documents["j-unknown"].body, { job_id: id }));
      }
      renderJob(name);
    }, LOAD_MS);
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

  function askDelete(documentId) {
    if (picker.blockers().length) return;
    var kind = family();
    pending = { id: documentId, kind: kind };
    dialog.querySelector('[data-role="doc"]').textContent = documentId;
    dialog.querySelector('[data-role="sel"]').textContent = picker.label();
    dialog.querySelector('[data-role="tail"]').textContent = DELETE_TAIL[kind];
    openDialog("shell.dialog.delete", "shell.dialog.delete-cancel");
  }

  function showDeleteOutcome(rec, kind) {
    var box = ID("delete.outcome");
    badge(box.querySelector('[data-role="status"]'), DELETE_STATE[rec.status], rec.status);
    box.querySelector('[data-role="doc"]').textContent = rec.document_id;
    box.querySelector('[data-role="message"]').textContent = rec.message || "The server returned no message.";
    ID("delete.seam-toggle").textContent = "Seam events, reported by the " + (kind === "hipporag" ? "HippoRAG" : "v1") + " delete node";
    var list = box.querySelector('[data-role="seam-list"]');
    clearNode(list);
    if (!rec.seam_events.length) list.appendChild(h("li", "No seam events."));
    rec.seam_events.forEach(function (event) {
      list.appendChild(h("li", event.component + ": " + event.outcome + ", counted_by " + event.spend.counted_by));
    });
    box.hidden = false;
  }

  function finishDelete(p) {
    var bad = failure("delete", ["path", "document_id"]);
    if (bad) return showError(bad[0], bad[1]);
    showDeleteOutcome(Object.assign({}, FIX.documents["delete-success"], { document_id: p.id }), p.kind);
  }

  // ---- hooks ----

  function setState(name) {
    clearAll();
    setBusy(false);
    ID("state.in-flight").hidden = name !== "in-flight";
    if (name === "in-flight") return setBusy(true);
    if (name === "result") return showCard(FIX.documents["ingest-success"]);
    if (name === "loading") {
      setDrawer(true);
      return jobView("loading");
    }
    if (name === "empty") return renderJob("j-empty");
    if (name !== "idle") throw new Error("unknown documents state " + name);
    card.hidden = true;
    hideErrors();
  }

  function loadFixture(name) {
    clearAll();
    setBusy(false);
    ID("state.in-flight").hidden = true;
    if (JOB_FIXTURES.indexOf(name) >= 0) return renderJob(name);
    if (name === "j-unknown") {
      setDrawer(true);
      jobView("none");
      return showError(FIX.documents[name].status, FIX.documents[name].body);
    }
    if (name === "ingest-success") return showCard(FIX.documents[name]);
    if (/^delete-/.test(name) && FIX.documents[name]) return showDeleteOutcome(FIX.documents[name], family());
    throw new Error("unknown documents fixture " + name);
  }

  function inject(response) {
    clearAll();
    setBusy(false);
    ID("state.in-flight").hidden = true;
    showError(response.status, response.body);
  }

  // ---- wiring ----

  picker = Picker.attach("documents", function (api) {
    picker = api;
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
  ID("jobs.refresh").addEventListener("click", function () {
    loadJob(ID("jobs.job-id").value, current && current.name === "j-last" ? "last" : undefined);
  });
  ID("jobs.prev").addEventListener("click", function () {
    loadJob(ID("jobs.job-id").value);
  });
  ID("jobs.next").addEventListener("click", function () {
    loadJob(ID("jobs.job-id").value, "last");
  });
  ID("jobs.page-size").addEventListener("input", checkSize);
  ID("jobs.poll").addEventListener("change", function () {
    clearInterval(pollTimer);
    pollTimer = null;
    if (this.checked) {
      pollTimer = setInterval(function () {
        if (current) ID("jobs.refresh").click();
      }, 30000);
    }
  });
  [1, 2, 3].forEach(function (n) {
    ID("jobs.select-" + n).addEventListener("click", function () {
      loadJob(sessionJobs[n - 1].job_id);
    });
  });
  [1, 2, 3, 4, 5].forEach(function (n) {
    var toggle = ID("jobs.error-toggle-" + n);
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.parentElement.querySelector('[data-role="error"]').hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      toggle.textContent = open ? "Hide error" : "Show error";
    });
    ID("jobs.delete-" + n).addEventListener("click", function () {
      askDelete(this.closest("tr").querySelector('[data-role="id"]').textContent);
    });
  });
  ID("jobs.all").addEventListener("click", function () {
    var list = ID("jobs.list");
    list.scrollIntoView({ block: "nearest" });
  });
  ID("pipeline.status").textContent = FIX.documents.pipeline.text;
  ID("pipeline.cancel").addEventListener("click", function () {
    ID("pipeline.status").textContent = "Cancel requested (fixture)";
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
  $id("shell.dialog.delete-cancel").addEventListener("click", function () {
    dialog.close();
  });
  dialog.addEventListener("close", function () {
    pending = null;
    confirmButton.removeAttribute("aria-busy");
    confirmButton.querySelector(".spinner").hidden = true;
    setDisabled(confirmButton, false);
  });
  confirmButton.addEventListener("click", function () {
    if (!pending || confirmButton.disabled) return;
    var p = pending;
    setDisabled(confirmButton, true);
    confirmButton.setAttribute("aria-busy", "true");
    confirmButton.querySelector(".spinner").hidden = false;
    later(function () {
      dialog.close();
      finishDelete(p);
    }, CONFIRM_MS);
  });

  wireErrors("documents");
  Console.on("open-ingest", function () {
    Console.show("documents");
    showTab("paste");
  });

  renderList();
  jobView("none");
  checkSize();
  refresh();
  return { setState: setState, inject: inject, loadFixture: loadFixture };
})();
Console.register("documents", DocumentsScreen);
