WIRED["ledger GET /ledger/aliases"] = true;
WIRED["ledger GET /traces"] = true;
WIRED["ledger POST /promote/preview"] = true;
WIRED["ledger POST /ledger/history"] = true;
WIRED["ledger GET /log"] = true;

var LedgerScreen = (function () {
  var HISTORY_KEY = "databasise.console.history";
  var LOG_KEY = "databasise.console.ledger-log";
  var MSG = {
    noTrace: "Select at least one trace.",
    noOrigin: "Choose a change origin.",
    noAlias: "Enter an alias.",
    hashAlias: "This alias looks like a hash (64 hex characters, optional sha256: prefix) and cannot be used.",
    pageSize: "Page size must be between 1 and 100.",
  };
  var TIP = {
    active: "The active generation cannot be retired.",
    target: "This version is the target of the active rollback. roll back first.",
    tombstoned: "This version is already retired.",
  };
  var STATUS_TEXT = { active: "active", target: "target of active rollback", tombstoned: "tombstoned", none: "—" };
  var KIND_STATE = { promotion: "ok", rollback: "warn", tombstone: "neutral" };
  var KIND_GLYPH = { ok: "✓", warn: "▲", neutral: "■" };
  var SERVER_TRACES = "Recent runs (server)";

  var root = $id("screen-ledger");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var rollBackWrap = root.querySelector('[data-role="roll-back-wrap"]');
  var ledgerLog = SessionLog(LOG_KEY, 50);
  var writing = false; // a promote, rollback or retire is in flight; it is never aborted
  var previewing = false; // Preview promotion is waiting for its answer
  var previewSeq = 0; // a form edit moves it on, so an older Preview answer is dropped
  var checked = {}; // trace token -> true; the choice survives a repaint of the list
  var pinned = null; // a token sent here from another screen that the run history does not hold
  var shown = []; // the entries the trace list shows now
  var source = "history"; // "history" (this browser) or "recent" (GET /traces)
  var recent = []; // the items of the last GET /traces answer
  var recentCtl = null; // the abort handle of the GET /traces read in flight
  var promoted = null; // the alias of the result card
  var timeline = null; // the last good history page: {alias, offset, limit, body}
  var serverHistory = false; // that page came from POST /ledger/history
  var historyCtl = null; // the abort handle of the history read in flight

  function ID(name) {
    return $id("ledger." + name);
  }

  function ok(result) {
    return result.status >= 200 && result.status < 300;
  }

  function spin(button, on) {
    button.querySelector(".spinner").hidden = !on;
    if (on) button.setAttribute("aria-busy", "true");
    else button.removeAttribute("aria-busy");
  }

  function short(token) {
    return token.slice(0, 8);
  }

  function chip(text, state, cls) {
    var c = h("span", text, "chip" + (cls ? " " + cls : ""));
    if (state) c.setAttribute("data-state", state);
    return c;
  }

  // ---- errors ----

  function checkSize() {
    var input = ID("timeline.page-size");
    var raw = input.value.trim();
    var n = Number(raw);
    var valid = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100;
    setFieldError(input, valid ? "" : MSG.pageSize);
  }

  // renderError clears every field message, so the page-size check is run again after it (IN-JSC-08).
  function showError(status, body, opts) {
    var shape = renderError("ledger", status, body, opts);
    errorsBox.hidden = shape === "result";
    rollBackWrap.hidden = !(body && body.refusal_type === "ActiveGenerationRetirementError");
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
    checkSize();
    return shape;
  }

  function hideErrors() {
    renderError("ledger", 200, null);
    errorsBox.hidden = true;
    rollBackWrap.hidden = true;
    checkSize();
  }

  // ---- promote form ----

  var alias = ID("promote.alias");
  var datalist = document.getElementById("ledger-alias-list");
  var form = ID("promote.form");
  var traceBox = ID("promote.traces");
  var submit = ID("promote.submit");
  var preview = ID("promote.preview");

  function addAliasOption(name) {
    var known = Array.prototype.some.call(datalist.options, function (o) {
      return o.value === name;
    });
    if (known) return;
    var option = document.createElement("option");
    option.value = name;
    datalist.appendChild(option);
  }

  // The run history of this browser, newest first, one entry per trace token. The log is read again on every call, because
  // Query and Compare write it from their own SessionLog.
  function historyEntries() {
    var seen = {};
    var out = [];
    SessionLog(HISTORY_KEY, 50)
      .all()
      .forEach(function (e) {
        var token = e.trace_token;
        if (typeof token !== "string" || token === "" || seen[token]) return;
        seen[token] = true;
        out.push({ token: token, time: String(e.timestamp || "").slice(0, 19).replace("T", " "), selector: selectorLabel(e.selector), known: true, partial: !!e.partial, degraded: !!e.degraded });
      });
    if (pinned && !seen[pinned]) out.push({ token: pinned, time: "", selector: "Added from another screen", known: false, partial: false, degraded: false });
    return out;
  }

  // The Recent runs source: the server's traces, newest first. A trace this browser ran keeps its selector label.
  function recentEntries() {
    var mine = {};
    historyEntries().forEach(function (e) {
      mine[e.token] = e;
    });
    return recent.map(function (item) {
      var own = mine[item.trace_reference];
      return {
        token: item.trace_reference,
        time: String(item.created_at || "").slice(0, 19).replace("T", " "),
        selector: own && own.known ? own.selector : SERVER_TRACES,
        known: !!(own && own.known),
        partial: !!item.partial,
        degraded: !!item.degraded,
      };
    });
  }

  function renderTraces() {
    var list = source === "recent" ? recentEntries() : historyEntries();
    shown = list;
    root.querySelector('[data-role="traces-empty"]').hidden = list.length > 0;
    ensureRows(traceBox, list.length).forEach(function (slot, i) {
      var t = list[i];
      slot.title = t.token;
      slot.setAttribute("data-token", t.token);
      var box = slot.querySelector("input");
      box.checked = !!checked[t.token];
      setDisabled(box, previewing);
      slot.querySelector('[data-role="token"]').textContent = short(t.token);
      slot.querySelector('[data-role="time"]').textContent = t.time;
      var selector = slot.querySelector('[data-role="selector"]');
      selector.textContent = t.selector;
      selector.hidden = false;
      var chips = slot.querySelector('[data-role="chips"]');
      clearNode(chips);
      if (t.partial) chips.appendChild(chip("partial", "warn"));
      if (t.degraded) chips.appendChild(chip("degraded", "warn"));
    });
  }

  function selectedTraces() {
    return shown.filter(function (t) {
      return checked[t.token] === true;
    });
  }

  function origin() {
    if (ID("promote.origin-human").checked) return "human_edit";
    return ID("promote.origin-machine").checked ? "machine_mutation" : null;
  }

  function problem(list, state, text) {
    var li = document.createElement("li");
    li.setAttribute("data-state", state);
    li.appendChild(h("span", state === "fail" ? "✕ " : "▲ "));
    li.appendChild(document.createTextNode(text));
    list.appendChild(li);
  }

  function refreshPreflight() {
    var chosen = selectedTraces();
    var blockers = [];
    var warnings = [];
    if (!chosen.length) blockers.push(MSG.noTrace);
    chosen.forEach(function (t) {
      if (t.partial) blockers.push("Trace " + short(t.token) + " is a partial run and cannot be promoted.");
    });
    if (!origin()) blockers.push(MSG.noOrigin);
    if (alias.value === "") blockers.push(MSG.noAlias);
    else if (HASH_SHAPED.test(alias.value)) blockers.push(MSG.hashAlias);
    var labels = [];
    chosen.forEach(function (t) {
      if (t.known && labels.indexOf(t.selector) < 0) labels.push(t.selector);
    });
    if (labels.length > 1) {
      warnings.push("Selected traces came from different selectors: " + labels.join(", ") + ". The server refuses traces that resolve to different arms.");
    }
    var box = ID("promote.preflight");
    clearNode(box);
    if (blockers.length || warnings.length) {
      var list = document.createElement("ul");
      blockers.forEach(function (text) {
        problem(list, "fail", text);
      });
      warnings.forEach(function (text) {
        problem(list, "warn", text);
      });
      box.appendChild(list);
    } else {
      box.appendChild(h("p", "No pre-flight problems.", "muted"));
    }
    setDisabled(submit, writing || blockers.length > 0);
    setDisabled(preview, writing || previewing || blockers.length > 0);
    spin(submit, writing);
    spin(preview, previewing);
    ID("promote.preview-result").hidden = true;
    return blockers;
  }

  // A form edit moves previewSeq on, so a Preview answer for the earlier form is dropped.
  function formEdited() {
    previewSeq += 1;
    refreshPreflight();
  }

  function setBoxes(disabled) {
    Array.prototype.forEach.call(traceBox.querySelectorAll("input"), function (box) {
      setDisabled(box, disabled);
    });
  }

  // Preview promotion (WR-JSC-02): the trace boxes are locked while it waits; the answer is read against the traces checked
  // when it arrives, and dropped when none are checked then or the form was edited meanwhile.
  function showPreview() {
    if (writing || previewing || preview.disabled) return;
    hideErrors();
    var req = { alias: alias.value, trace_ids: selectedTraces().map(function (t) { return t.token; }), change_origin: origin() };
    var seq = (previewSeq += 1);
    previewing = true;
    setBoxes(true);
    refreshPreflight();
    api("POST", "/promote/preview", req).then(function (result) {
      previewing = false;
      setBoxes(false);
      refreshPreflight();
      if (seq !== previewSeq || !selectedTraces().length) return;
      var rec = result.body;
      if (!ok(result) || rec === null || typeof rec !== "object") {
        if (showError(result.status, rec) === "result") showError(0, null, { text: "The server answered without a preview." });
        return;
      }
      var list = ID("promote.preview-result").querySelector('[data-role="attrs"]');
      clearNode(list);
      ["arm", "mutation_class", "next_version", "promotable", "reason"].forEach(function (key) {
        appendAttribute(list, key, rec[key]);
      });
      ID("promote.preview-result").hidden = false;
    });
  }

  function showResult(rec) {
    var card = ID("promote.result");
    card.querySelector('[data-role="alias"]').textContent = rec.alias;
    card.querySelector('[data-role="version"]').textContent = rec.version;
    card.querySelector('[data-role="kind"]').textContent = rec.record_kind;
    card.querySelector('[data-role="provenance"]').textContent = rec.provenance;
    card.querySelector('[data-role="ordinal"]').textContent = String(rec.generation_ordinal);
    promoted = rec.alias;
    ID("live.query-alias").hidden = false;
    card.hidden = false;
    addAliasOption(rec.alias);
  }

  // ---- confirm dialogs ----

  // A confirm dialog whose write is in flight keeps both buttons disabled, ignores Escape and closes only when the answer arrives
  // (IN-JSC-04, D-14). Cancel and Escape before Confirm close it and send nothing.
  function makeDialog(kind) {
    var d = {
      el: $id("shell.dialog." + kind),
      confirm: $id("shell.dialog." + kind + "-confirm"),
      cancel: $id("shell.dialog." + kind + "-cancel"),
      pending: null,
      sending: false,
      ok: function () {
        return !!d.pending;
      },
    };
    d.note = d.el.querySelector('[data-role="sending"]');
    d.sync = function () {
      setDisabled(d.confirm, d.sending || !d.ok());
      setDisabled(d.cancel, d.sending);
      d.note.hidden = !d.sending;
      spin(d.confirm, d.sending);
    };
    d.cancel.addEventListener("click", function () {
      if (!d.sending) d.el.close();
    });
    d.el.addEventListener("cancel", function (event) {
      if (d.sending) event.preventDefault();
    });
    d.el.addEventListener("close", function () {
      // Chromium lets a repeated Escape through even when it was prevented; the dialog goes back up until the answer arrives.
      if (d.sending) return d.el.showModal();
      d.pending = null;
      d.sync();
    });
    return d;
  }

  // Sends the write the dialog confirmed and resolves with the answer once the dialog has closed.
  function write(d, path, body) {
    d.sending = true;
    writing = true;
    d.sync();
    refreshPreflight();
    return api("POST", path, body, { kind: "ledger" }).then(function (result) {
      d.sending = false;
      writing = false;
      d.el.close();
      d.sync();
      refreshPreflight();
      return result;
    });
  }

  var promoteDialog = makeDialog("promote");

  function logEntry(rec, extra) {
    var entry = { alias: rec.alias, version: rec.version, record_kind: rec.record_kind, generation_ordinal: rec.generation_ordinal, created_at: new Date().toISOString() };
    Object.keys(extra).forEach(function (key) {
      entry[key] = extra[key];
    });
    ledgerLog.add(entry);
  }

  function askPromote() {
    if (submit.disabled) return;
    var chosen = selectedTraces();
    var body = { alias: alias.value, trace_ids: chosen.map(function (t) { return t.token; }), change_origin: origin() };
    var verb = ID("promote.verb").value;
    if (verb && verb !== "operator-asserted") body.verb = verb;
    promoteDialog.pending = body;
    var d = promoteDialog.el;
    d.querySelector('[data-role="alias"]').textContent = body.alias;
    d.querySelector('[data-role="count"]').textContent = String(body.trace_ids.length);
    promoteDialog.sync();
    openDialog("shell.dialog.promote", "shell.dialog.promote-cancel");
  }

  function confirmPromote() {
    if (!promoteDialog.pending || promoteDialog.sending || promoteDialog.confirm.disabled) return;
    var body = promoteDialog.pending;
    hideErrors();
    ID("promote.result").hidden = true;
    write(promoteDialog, "/promote", body).then(function (result) {
      var rec = result.body;
      if (ok(result) && rec !== null && typeof rec === "object" && typeof rec.version === "string") {
        showResult(rec);
        logEntry(rec, { trace_ids: body.trace_ids, change_origin: body.change_origin });
        AliasCatalog.load();
        return;
      }
      if (showError(result.status, rec) === "result") showError(0, null, { text: "The server answered without a promotion record." });
    });
  }

  promoteDialog.confirm.addEventListener("click", confirmPromote);

  // ---- timeline ----

  var table = ID("timeline.table");
  var rollbackDialog = makeDialog("rollback");
  var retireDialog = makeDialog("retire");
  var retireVersion = $id("shell.dialog.retire-version");

  [rollbackDialog, retireDialog].forEach(function (d) {
    var kind = d === rollbackDialog ? "rollback" : "retire";
    d.traces = $id("shell.dialog." + kind + "-traces");
    d.human = $id("shell.dialog." + kind + "-origin-human");
    d.machine = $id("shell.dialog." + kind + "-origin-machine");
    d.chosen = function () {
      return Array.prototype.filter
        .call(d.traces.options, function (o) {
          return o.selected;
        })
        .map(function (o) {
          return o.value;
        });
    };
    d.origin = function () {
      return d.human.checked ? "human_edit" : d.machine.checked ? "machine_mutation" : null;
    };
    d.ok = function () {
      return !!d.pending && d.chosen().length > 0 && d.origin() !== null && (kind === "rollback" || retireVersion.value === d.pending.version);
    };
    [d.traces, d.human, d.machine].forEach(function (el) {
      el.addEventListener("change", d.sync);
    });
  });
  retireVersion.addEventListener("input", retireDialog.sync);

  function limitValue() {
    var raw = ID("timeline.page-size").value.trim();
    var n = Number(raw);
    return raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100 ? n : null;
  }

  function setLoading(on) {
    ID("timeline.loading").hidden = !on;
    table.setAttribute("aria-busy", String(on));
    if (on) {
      setDisabled(ID("timeline.prev"), true);
      setDisabled(ID("timeline.next"), true);
    }
  }

  // The head is the version GET /ledger/aliases names for the alias, so a paged timeline still finds it; without that row it is
  // the active record with the highest ordinal on the page.
  function headOrdinal(name) {
    var row = AliasCatalog.source === "server" ? AliasCatalog.byAlias(name) : null;
    if (row) return row.generation_ordinal;
    var top = -1;
    timeline.body.records.forEach(function (r) {
      if (r.active && r.generation_ordinal > top) top = r.generation_ordinal;
    });
    return top;
  }

  function statusOf(r, head) {
    if (r.record_kind === "tombstone") return "none";
    if (r.tombstoned) return "tombstoned";
    if (r.active) return r.generation_ordinal === head ? "active" : "target";
    return "none";
  }

  // The version the shown alias is active at, or null when the server history does not say.
  function activeVersion() {
    if (!timeline || !serverHistory) return null;
    var head = headOrdinal(timeline.alias);
    var rec = timeline.body.records.filter(function (r) {
      return r.active && r.generation_ordinal === head;
    })[0];
    if (rec) return rec.minted_version;
    var row = AliasCatalog.source === "server" ? AliasCatalog.byAlias(timeline.alias) : null;
    return row ? row.active_version : null;
  }

  function fillTraces(cell, ids) {
    clearNode(cell);
    (ids || []).forEach(function (id) {
      cell.appendChild(chip(short(id), null, "mono"));
    });
  }

  function renderTimeline() {
    var records = timeline ? timeline.body.records : [];
    var wrap = root.querySelector('[data-role="table-wrap"]');
    ID("timeline.empty").hidden = records.length > 0;
    wrap.hidden = records.length === 0;
    var range = root.querySelector('[data-role="range"]');
    range.hidden = records.length === 0;
    if (!timeline) {
      setDisabled(ID("timeline.prev"), true);
      setDisabled(ID("timeline.next"), true);
      return;
    }
    var head = headOrdinal(timeline.alias);
    ensureRows(table.tBodies[0], records.length).forEach(function (row, i) {
      var r = records[i];
      var status = statusOf(r, head);
      var tombstone = r.record_kind === "tombstone";
      row.setAttribute("data-status", status);
      if (status === "active") row.setAttribute("tabindex", "-1");
      else row.removeAttribute("tabindex");
      var cell = function (role) {
        return row.querySelector('[data-role="' + role + '"]');
      };
      cell("ordinal").textContent = String(r.generation_ordinal);
      cell("created").textContent = r.created_at;
      var state = KIND_STATE[r.record_kind] || "neutral";
      cell("kind").setAttribute("data-state", state);
      cell("kind").textContent = KIND_GLYPH[state] + " " + r.record_kind;
      cell("minted").textContent = r.minted_version || "—";
      cell("targets").textContent = r.targets_version || "—";
      cell("origin").textContent = r.change_origin || "—";
      fillTraces(cell("traces"), r.promotion_trace_ids);
      cell("status").textContent = STATUS_TEXT[status];
      var buttons = row.querySelectorAll("button");
      var wrapRetire = cell("retire-wrap");
      buttons[0].hidden = tombstone;
      wrapRetire.hidden = tombstone;
      setDisabled(buttons[0], status === "active" || status === "tombstoned");
      var blocked = status !== "none";
      setDisabled(buttons[1], blocked);
      if (blocked) wrapRetire.setAttribute("title", TIP[status]);
      else wrapRetire.removeAttribute("title");
    });
    ID("timeline.alias").value = timeline.alias;
    range.textContent = "Showing " + (timeline.offset + 1) + " to " + (timeline.offset + records.length) + " of " + timeline.body.total;
    setDisabled(ID("timeline.prev"), timeline.offset <= 0);
    setDisabled(ID("timeline.next"), timeline.body.next_offset === null);
  }

  // Reads one page of the alias history. The previous page stays on screen while it loads and after a failure (WR-JSB-03 style);
  // an answer for a read that was replaced is dropped.
  function loadTimeline(name, offset) {
    if (historyCtl) historyCtl.abort();
    historyCtl = null;
    if (name === "") {
      timeline = null;
      serverHistory = false;
      setLoading(false);
      return renderTimeline();
    }
    var limit = limitValue();
    if (limit === null) return checkSize();
    var mine = (historyCtl = new AbortController());
    ID("timeline.alias").value = name;
    setLoading(true);
    return api("POST", "/ledger/history", { alias: name, limit: limit, offset: offset }, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== historyCtl) return;
      historyCtl = null;
      setLoading(false);
      var body = result.body;
      if (ok(result) && body !== null && typeof body === "object" && Array.isArray(body.records)) {
        timeline = { alias: name, offset: offset, limit: limit, body: body };
        serverHistory = true;
        return renderTimeline();
      }
      serverHistory = false;
      renderTimeline();
      if (showError(result.status, body) === "result") showError(0, null, { text: "The server answered without a history page." });
    });
  }

  function chooseAlias(name) {
    root.querySelector('[data-role="outcome"]').hidden = true;
    ID("timeline.notice").hidden = true;
    loadTimeline(name, 0);
  }

  // The options of a Roll back or Retire dialog: the traces of the version the row names, then this browser's run history.
  function fillTraceOptions(select, own) {
    clearNode(select);
    var seen = {};
    own.forEach(function (token) {
      seen[token] = true;
      var option = h("option", short(token) + "  (this version)");
      option.value = token;
      select.appendChild(option);
    });
    historyEntries().forEach(function (t) {
      if (seen[t.token]) return;
      var option = h("option", short(t.token) + "  " + t.selector + (t.partial ? "  (partial run)" : ""));
      option.value = t.token;
      select.appendChild(option);
    });
  }

  function openChange(d, kind, i) {
    var r = timeline.body.records[i];
    var active = activeVersion();
    d.pending = { alias: timeline.alias, version: r.minted_version, offset: timeline.offset };
    fillTraceOptions(d.traces, r.promotion_trace_ids || []);
    d.human.checked = false;
    d.machine.checked = false;
    d.el.querySelector('[data-role="alias"]').textContent = timeline.alias;
    if (kind === "rollback") {
      d.el.querySelector('[data-role="target"]').textContent = r.minted_version;
      d.el.querySelector('[data-role="active"]').textContent = active === null ? "" : active;
      d.el.querySelector('[data-role="active-known"]').hidden = active === null;
      d.el.querySelector('[data-role="active-unknown"]').hidden = active !== null;
    } else {
      d.el.querySelector('[data-role="version"]').textContent = r.minted_version;
      d.el.querySelector('[data-role="hint"]').textContent = r.minted_version;
      retireVersion.value = "";
    }
    d.sync();
    openDialog("shell.dialog." + kind, "shell.dialog." + kind + "-cancel");
  }

  // The request is built here and nowhere else: Cancel and Escape never reach it (T-18-24).
  function confirmChange(d, kind) {
    if (!d.pending || d.sending || d.confirm.disabled) return;
    var p = d.pending;
    var body = { alias: p.alias, version: p.version, trace_ids: d.chosen(), change_origin: d.origin() };
    hideErrors();
    root.querySelector('[data-role="outcome"]').hidden = true;
    write(d, "/" + kind, body).then(function (result) {
      var rec = result.body;
      if (!(ok(result) && rec !== null && typeof rec === "object" && typeof rec.record_kind === "string")) {
        if (showError(result.status, rec) === "result") showError(0, null, { text: "The server answered without a ledger record." });
        return;
      }
      var outcome = root.querySelector('[data-role="outcome"]');
      if (kind === "retire") {
        outcome.textContent = "Retired version " + p.version + " of alias " + p.alias + ". Nothing un-retires it.";
      } else {
        logEntry(rec, { targets_version: p.version, trace_ids: body.trace_ids, change_origin: body.change_origin });
        outcome.textContent = "Rolled back " + p.alias + " to " + p.version + ". Version " + rec.version + " minted as generation " + rec.generation_ordinal + ".";
      }
      outcome.hidden = false;
      loadTimeline(p.alias, p.offset);
      AliasCatalog.load();
    });
  }

  rollbackDialog.confirm.addEventListener("click", function () {
    confirmChange(rollbackDialog, "rollback");
  });
  retireDialog.confirm.addEventListener("click", function () {
    confirmChange(retireDialog, "retire");
  });

  // One delegated listener serves the literal rows and every cloned row of the timeline.
  table.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button || button.disabled || !timeline) return;
    var row = button.closest("tr");
    var i = Array.prototype.indexOf.call(row.parentNode.children, row);
    var id = button.getAttribute("data-mock-id") || "";
    if (id.indexOf("ledger.timeline.rollback-") === 0) openChange(rollbackDialog, "rollback", i);
    else if (id.indexOf("ledger.timeline.retire-") === 0) openChange(retireDialog, "retire", i);
  });

  // ---- aliases ----

  // The datalist and the Aliases table follow the catalogue (the server rows, or this browser's log without GET /ledger/aliases).
  function renderAliases() {
    AliasCatalog.rows.forEach(function (a) {
      addAliasOption(a.alias);
    });
    var wrap = alias.closest("label").parentNode;
    var note = wrap.querySelector('[data-role="alias-source"]');
    if (!note) {
      note = h("p", LOG_NOTE, "muted");
      note.setAttribute("data-role", "alias-source");
      wrap.appendChild(note);
    }
    note.hidden = AliasCatalog.source !== "log";
    fillAliasPicker(ID("timeline.alias"));
    var panel = ID("aliases.panel");
    var panelNote = panel.querySelector('[data-role="alias-source"]');
    if (!panelNote) {
      panelNote = h("p", LOG_NOTE, "muted");
      panelNote.setAttribute("data-role", "alias-source");
      panel.appendChild(panelNote);
    }
    panelNote.hidden = AliasCatalog.source !== "log";
    ensureRows(ID("aliases.table").tBodies[0], AliasCatalog.rows.length).forEach(function (row, i) {
      var a = AliasCatalog.rows[i];
      row.querySelector('[data-role="alias"]').textContent = a.alias;
      row.querySelector('[data-role="version"]').textContent = a.active_version;
      row.querySelector('[data-role="kind"]').textContent = a.record_kind;
      row.querySelector('[data-role="ordinal"]').textContent = String(a.generation_ordinal);
      row.querySelector('[data-role="created"]').textContent = a.created_at;
    });
    if (timeline) renderTimeline(); // the head may have moved
  }

  // ---- trace source ----

  function loadRecent() {
    if (recentCtl) recentCtl.abort();
    var mine = (recentCtl = new AbortController());
    api("GET", "/traces?limit=50&offset=0", null, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== recentCtl) return;
      recentCtl = null;
      var body = result.body;
      if (ok(result) && body !== null && typeof body === "object" && Array.isArray(body.items)) {
        recent = body.items;
      } else {
        // The history list stays: the source goes back to it and the failure shows as a banner.
        source = "history";
        ID("promote.source-history").checked = true;
        if (showError(result.status, body) === "result") showError(0, null, { text: "The server answered without a trace list." });
      }
      renderTraces();
      refreshPreflight();
    });
  }

  function setSource(next) {
    if (next === source) return;
    source = next;
    if (recentCtl) recentCtl.abort();
    recentCtl = null;
    if (source === "recent" && Live.has("GET", "/traces")) loadRecent();
    else source = "history";
    renderTraces();
    refreshPreflight();
  }

  // ---- wiring ----

  form.addEventListener("input", formEdited);
  form.addEventListener("change", formEdited);
  traceBox.addEventListener("change", function (event) {
    var slot = event.target.closest("label");
    if (slot) checked[slot.getAttribute("data-token")] = event.target.checked;
  });
  ID("promote.source-history").addEventListener("change", function () {
    setSource("history");
  });
  ID("promote.source-recent").addEventListener("change", function () {
    setSource("recent");
  });
  submit.addEventListener("click", askPromote);
  preview.addEventListener("click", showPreview);
  ID("timeline.alias").addEventListener("change", function () {
    chooseAlias(this.value);
  });
  ID("timeline.prev").addEventListener("click", function () {
    if (timeline) loadTimeline(timeline.alias, Math.max(0, timeline.offset - timeline.limit));
  });
  ID("timeline.next").addEventListener("click", function () {
    if (timeline && typeof timeline.body.next_offset === "number") loadTimeline(timeline.alias, timeline.body.next_offset);
  });
  // One delegated listener serves the literal rows and every cloned row of the alias table.
  ID("aliases.table").addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    var row = button.closest("tr");
    var a = AliasCatalog.rows[Array.prototype.indexOf.call(row.parentNode.children, row)];
    if (!a) return;
    chooseAlias(a.alias);
    ID("timeline.region").scrollIntoView({ block: "nearest" });
  });
  ID("timeline.page-size").addEventListener("input", checkSize);
  ID("live.query-alias").addEventListener("click", function (event) {
    event.preventDefault();
    if (promoted === null) return;
    Console.show("query");
    Console.emit("query-alias", promoted);
  });
  ID("error.roll-back-first").addEventListener("click", function (event) {
    event.preventDefault();
    var row = root.querySelector('tr[data-status="active"]:not([hidden])');
    if (row) {
      row.focus();
      row.scrollIntoView({ block: "nearest" });
    }
  });

  wireErrors("ledger");
  Console.on("aliases", renderAliases);
  Console.on("show", function (name) {
    if (name !== "ledger") return;
    renderTraces();
    refreshPreflight();
  });
  // Promote from a Query, Compare or Evidence result: the sent trace becomes the only choice (IN-JSA-07).
  Console.on("promote", function (event) {
    var token = event && event.trace;
    checked = {};
    pinned = typeof token === "string" && token !== "" ? token : null;
    if (pinned) checked[pinned] = true;
    renderTraces();
    refreshPreflight();
    form.scrollIntoView({ block: "nearest" });
  });

  setLoading(false);
  renderTimeline();
  renderAliases();
  renderTraces();
  checkSize();
  refreshPreflight();
  return {};
})();
Console.register("ledger", LedgerScreen);
