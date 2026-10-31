WIRED["ledger GET /ledger/aliases"] = true;
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

  var root = $id("screen-ledger");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var rollBackWrap = root.querySelector('[data-role="roll-back-wrap"]');
  var ledgerLog = SessionLog(LOG_KEY, 50);
  var writing = false; // a promote, rollback or retire is in flight; it is never aborted
  var checked = {}; // trace token -> true; the choice survives a repaint of the list
  var pinned = null; // a token sent here from another screen that the run history does not hold
  var shown = []; // the entries the trace list shows now
  var promoted = null; // the alias of the result card

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

  function renderTraces() {
    var list = historyEntries();
    shown = list;
    root.querySelector('[data-role="traces-empty"]').hidden = list.length > 0;
    ensureRows(traceBox, list.length).forEach(function (slot, i) {
      var t = list[i];
      slot.title = t.token;
      slot.setAttribute("data-token", t.token);
      slot.querySelector("input").checked = !!checked[t.token];
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
    setDisabled(preview, writing || blockers.length > 0);
    spin(submit, writing);
    ID("promote.preview-result").hidden = true;
    return blockers;
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

  // ---- aliases ----

  // The datalist and the Aliases table follow the catalogue (the server rows, or this browser's log without GET /ledger/aliases).
  function renderAliases() {
    AliasCatalog.rows.forEach(function (a) {
      addAliasOption(a.alias);
    });
    var wrap = alias.closest("[data-needs-backend]") || alias.parentNode;
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
  }

  // ---- wiring ----

  form.addEventListener("input", refreshPreflight);
  form.addEventListener("change", refreshPreflight);
  traceBox.addEventListener("change", function (event) {
    var slot = event.target.closest("label");
    if (slot) checked[slot.getAttribute("data-token")] = event.target.checked;
  });
  submit.addEventListener("click", askPromote);
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

  ID("timeline.loading").hidden = true;
  ID("timeline.empty").hidden = false;
  root.querySelector('[data-role="table-wrap"]').hidden = true;
  renderAliases();
  renderTraces();
  checkSize();
  refreshPreflight();
  return {};
})();
Console.register("ledger", LedgerScreen);
