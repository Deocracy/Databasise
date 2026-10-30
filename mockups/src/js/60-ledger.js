var LedgerScreen = (function () {
  var L = FIX.ledger;
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
  var REFUSAL_FOR = { promote: "refusal-partial", rollback: "refusal-unknown-trace", retire: "refusal-active-retire" };
  var LOAD_MS = 300;
  var CONFIRM_MS = 300;

  var root = $id("screen-ledger");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var rollBackWrap = root.querySelector('[data-role="roll-back-wrap"]');
  var timers = [];
  var loadTimer = null;
  var busy = false;
  var current = null;
  var pendingPromote = null;

  function ID(name) {
    return $id("ledger." + name);
  }

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  function later(fn, ms) {
    timers.push(setTimeout(fn, ms));
  }

  function clearTimers() {
    timers.forEach(clearTimeout);
    timers = [];
    clearTimeout(loadTimer);
  }

  function outcome() {
    return ID("mock.outcome").value;
  }

  function spin(button, on) {
    button.querySelector(".spinner").hidden = !on;
    if (on) button.setAttribute("aria-busy", "true");
    else button.removeAttribute("aria-busy");
  }

  function short(token) {
    return token.slice(0, 8);
  }

  function traceByRef(ref) {
    return L.traces.filter(function (t) {
      return t.trace_reference === ref;
    })[0];
  }

  // ---- errors ----

  function showError(status, body) {
    var shape = renderError("ledger", status, body);
    errorsBox.hidden = shape === "result";
    rollBackWrap.hidden = !(body && body.refusal_type === "ActiveGenerationRetirementError");
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
    return shape;
  }

  function hideErrors() {
    renderError("ledger", 200, null);
    errorsBox.hidden = true;
    rollBackWrap.hidden = true;
  }

  // The mock outcome select decides which server response the next confirm gets; null means success.
  function failure(op) {
    var o = outcome();
    if (o === "refusal") return L[REFUSAL_FOR[op]];
    if (o === "validation") {
      if (op === "promote") return L.validation;
      return { status: 422, body: { detail: [{ loc: ["body", "version"], msg: L.validation.body.detail[0].msg, type: "string_too_short" }] } };
    }
    if (o === "server-failure") return L["server-failure"];
    if (o === "generic") return L["generic-5xx"];
    return null;
  }

  // ---- promote form ----

  var alias = ID("promote.alias");
  var datalist = document.getElementById("ledger-alias-list");
  var form = ID("promote.form");
  var traceBox = ID("promote.traces");
  var slots = Array.prototype.slice.call(traceBox.querySelectorAll('[data-role="slot"]'));
  var boxes = slots.map(function (slot) {
    return slot.querySelector("input");
  });
  var headings = [];
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

  function chip(text, state, cls) {
    var c = h("span", text, "chip" + (cls ? " " + cls : ""));
    if (state) c.setAttribute("data-state", state);
    return c;
  }

  function fillSlots() {
    var last = null;
    slots.forEach(function (slot, i) {
      var t = L.traces[i];
      slot.title = t.trace_reference;
      slot.querySelector('[data-role="token"]').textContent = short(t.trace_reference);
      slot.querySelector('[data-role="time"]').textContent = t.created_at;
      slot.querySelector('[data-role="selector"]').textContent = t.selector;
      var chips = slot.querySelector('[data-role="chips"]');
      if (t.partial) chips.appendChild(chip("partial", "warn"));
      if (t.arm === "hipporag") chips.appendChild(chip("HippoRAG", "neutral"));
      if (t.degraded) chips.appendChild(chip("degraded", "warn"));
      if (t.selector !== last) {
        var heading = h("p", t.selector, "trace-group");
        traceBox.insertBefore(heading, slot);
        headings.push(heading);
        last = t.selector;
      }
    });
  }

  function setSource(recent) {
    headings.forEach(function (heading) {
      heading.hidden = recent;
    });
    slots.forEach(function (slot) {
      slot.querySelector('[data-role="selector"]').hidden = !recent;
    });
  }

  function selectedTraces() {
    return L.traces.filter(function (t, i) {
      return boxes[i].checked;
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
      if (t.partial) blockers.push("Trace " + short(t.trace_reference) + " is a partial run and cannot be promoted.");
    });
    if (!origin()) blockers.push(MSG.noOrigin);
    if (alias.value === "") blockers.push(MSG.noAlias);
    else if (HASH_SHAPED.test(alias.value)) blockers.push(MSG.hashAlias);
    var labels = [];
    chosen.forEach(function (t) {
      if (labels.indexOf(t.selector) < 0) labels.push(t.selector);
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
    setDisabled(submit, busy || blockers.length > 0);
    setDisabled(preview, busy || blockers.length > 0);
    spin(submit, busy);
    ID("promote.preview-result").hidden = true;
    return blockers;
  }

  function showPreview() {
    if (busy || preview.disabled) return;
    hideErrors();
    busy = true;
    setDisabled(preview, true);
    spin(preview, true);
    later(function () {
      busy = false;
      spin(preview, false);
      var bad = failure("promote");
      if (bad) {
        refreshPreflight();
        return showError(bad.status, bad.body);
      }
      var rec = Object.assign({}, L.preview, { arm: selectedTraces()[0].arm });
      refreshPreflight();
      var list = ID("promote.preview-result").querySelector('[data-role="attrs"]');
      clearNode(list);
      ["arm", "mutation_class", "next_version", "promotable", "reason"].forEach(function (key) {
        appendAttribute(list, key, rec[key]);
      });
      ID("promote.preview-result").hidden = false;
    }, CONFIRM_MS);
  }

  function showResult(rec) {
    var card = ID("promote.result");
    card.querySelector('[data-role="alias"]').textContent = rec.alias;
    card.querySelector('[data-role="version"]').textContent = rec.version;
    card.querySelector('[data-role="kind"]').textContent = rec.record_kind;
    card.querySelector('[data-role="provenance"]').textContent = rec.provenance;
    card.querySelector('[data-role="ordinal"]').textContent = String(rec.generation_ordinal);
    card.hidden = false;
    addAliasOption(rec.alias);
  }

  // ---- confirm dialogs ----

  // One factory for the three ledger dialogs. extraOk adds the dialog's own condition (the typed version for Retire).
  function makeDialog(kind, extraOk) {
    var d = {
      el: $id("shell.dialog." + kind),
      confirm: $id("shell.dialog." + kind + "-confirm"),
      pending: null,
    };
    d.traces = $id("shell.dialog." + kind + "-traces");
    d.human = $id("shell.dialog." + kind + "-origin-human");
    d.machine = $id("shell.dialog." + kind + "-origin-machine");
    d.ok = function () {
      var picked = Array.prototype.some.call(d.traces.options, function (o) {
        return o.selected;
      });
      return !!d.pending && picked && (d.human.checked || d.machine.checked) && extraOk(d);
    };
    d.update = function () {
      setDisabled(d.confirm, !d.ok());
    };
    return d;
  }

  function fillTraceOptions(select) {
    L.traces.forEach(function (t) {
      var option = h("option", short(t.trace_reference) + "  " + t.selector + (t.partial ? "  (partial run)" : ""));
      option.value = t.trace_reference;
      select.appendChild(option);
    });
  }

  function openFor(d, texts, pending) {
    d.pending = pending;
    Object.keys(texts).forEach(function (role) {
      d.el.querySelector('[data-role="' + role + '"]').textContent = texts[role];
    });
    Array.prototype.forEach.call(d.traces.options, function (o) {
      o.selected = false;
    });
    d.human.checked = false;
    d.machine.checked = false;
    d.update();
  }

  var retireVersion = $id("shell.dialog.retire-version");
  var dialogs = {
    promote: { el: $id("shell.dialog.promote"), confirm: $id("shell.dialog.promote-confirm") },
    rollback: makeDialog("rollback", function () {
      return true;
    }),
    retire: makeDialog("retire", function (d) {
      return retireVersion.value === d.pending.version;
    }),
  };

  function newVersion(active) {
    return String(parseInt(active.minted_version, 10) + 1) + ".0.0";
  }

  function showNotice(text) {
    var notice = ID("timeline.notice");
    notice.textContent = text;
    notice.hidden = false;
  }

  function finish(kind, p) {
    var bad = failure(kind);
    if (bad) return showError(bad.status, bad.body);
    hideErrors();
    if (kind === "retire") {
      current.records.forEach(function (r) {
        if (r.minted_version === p.version && r.record_kind !== "tombstone") r.tombstoned = true;
      });
      renderTimeline(current);
      showNotice("Retired version " + p.version + " of alias " + p.alias + ". Nothing un-retires it.");
    } else {
      // shortcut: the page has five row slots, so the minted rollback record is reported here and not appended; upgrade with the real history call.
      var ordinal = Math.max.apply(null, current.records.map(function (r) { return r.generation_ordinal; })) + 1;
      renderTimeline(current);
      showNotice("Rolled back " + p.alias + " to " + p.target + ". Version " + newVersion({ minted_version: p.active }) + " minted as generation " + ordinal + ". Reload the timeline to see the new record.");
    }
  }

  function wireDialog(kind, d) {
    $id("shell.dialog." + kind + "-cancel").addEventListener("click", function () {
      d.el.close();
    });
    [d.traces, d.human, d.machine].forEach(function (el) {
      el.addEventListener("change", d.update);
    });
    d.el.addEventListener("close", function () {
      d.pending = null;
      spin(d.confirm, false);
      d.update();
    });
    d.confirm.addEventListener("click", function () {
      if (!d.pending || d.confirm.disabled) return;
      var p = d.pending;
      setDisabled(d.confirm, true);
      spin(d.confirm, true);
      later(function () {
        d.el.close();
        finish(kind, p);
      }, CONFIRM_MS);
    });
  }

  fillTraceOptions(dialogs.rollback.traces);
  fillTraceOptions(dialogs.retire.traces);
  retireVersion.addEventListener("input", dialogs.retire.update);
  wireDialog("rollback", dialogs.rollback);
  wireDialog("retire", dialogs.retire);

  // The promote dialog has no fields; its confirm is always enabled.
  $id("shell.dialog.promote-cancel").addEventListener("click", function () {
    dialogs.promote.el.close();
  });
  dialogs.promote.el.addEventListener("close", function () {
    pendingPromote = null;
    spin(dialogs.promote.confirm, false);
    setDisabled(dialogs.promote.confirm, false);
  });
  dialogs.promote.confirm.addEventListener("click", function () {
    if (!pendingPromote || dialogs.promote.confirm.disabled) return;
    var p = pendingPromote;
    setDisabled(dialogs.promote.confirm, true);
    spin(dialogs.promote.confirm, true);
    busy = true;
    refreshPreflight();
    later(function () {
      busy = false;
      dialogs.promote.el.close();
      refreshPreflight();
      var bad = failure("promote");
      if (bad) return showError(bad.status, bad.body);
      hideErrors();
      showResult(Object.assign({}, L["promote-success"], { alias: p.alias }));
    }, CONFIRM_MS);
  });

  function askPromote() {
    if (submit.disabled) return;
    pendingPromote = { alias: alias.value, n: selectedTraces().length };
    var d = dialogs.promote.el;
    d.querySelector('[data-role="alias"]').textContent = pendingPromote.alias;
    d.querySelector('[data-role="count"]').textContent = String(pendingPromote.n);
    openDialog("shell.dialog.promote", "shell.dialog.promote-cancel");
  }

  // ---- timeline ----

  var table = ID("timeline.table");
  var rows = table.tBodies[0].rows;

  function timelineView(name) {
    var loading = name === "loading";
    ID("timeline.loading").hidden = !loading;
    ID("timeline.empty").hidden = name !== "empty";
    root.querySelector('[data-role="table-wrap"]').hidden = name !== "table";
    table.setAttribute("aria-busy", String(loading));
    if (loading) {
      setDisabled(ID("timeline.prev"), true);
      setDisabled(ID("timeline.next"), true);
    }
  }

  function statusOf(r, active) {
    if (r.active) return "active";
    var targetOfRollback = active && active.record_kind === "rollback" && r.record_kind !== "tombstone" && r.minted_version === active.targets_version;
    if (targetOfRollback) return "target";
    return r.tombstoned ? "tombstoned" : "none";
  }

  function fillTraces(cell, ids) {
    clearNode(cell);
    ids.forEach(function (id) {
      cell.appendChild(chip(short(id), null, "mono"));
      var t = traceByRef(id);
      if (t && t.partial) cell.appendChild(chip("partial run", "warn"));
    });
  }

  function renderTimeline(rec) {
    current = rec;
    var active = rec.records.filter(function (r) {
      return r.active;
    })[0];
    if (!rec.records.length) {
      timelineView("empty");
    } else {
      timelineView("table");
    }
    Array.prototype.forEach.call(rows, function (row, i) {
      var r = rec.records[i];
      row.hidden = !r;
      if (!r) return;
      var status = statusOf(r, active);
      var isTombstoneRecord = r.record_kind === "tombstone";
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
      var rollback = ID("timeline.rollback-" + (i + 1));
      var retire = ID("timeline.retire-" + (i + 1));
      var wrap = cell("retire-wrap");
      rollback.hidden = isTombstoneRecord;
      wrap.hidden = isTombstoneRecord;
      setDisabled(rollback, status === "active" || status === "tombstoned");
      var blocked = status !== "none";
      setDisabled(retire, blocked);
      if (blocked) wrap.setAttribute("title", TIP[status]);
      else wrap.removeAttribute("title");
    });
    ID("timeline.alias").value = rec.alias;
    setDisabled(ID("timeline.prev"), rec.offset <= 0);
    setDisabled(ID("timeline.next"), rec.next_offset === null);
  }

  function showRecord(name) {
    ID("timeline.notice").hidden = true;
    renderTimeline(JSON.parse(JSON.stringify(L[name])));
  }

  function emptyRecord(name) {
    return { alias: name, offset: 0, records: [], total: 0, next_offset: null };
  }

  function loadAlias(name) {
    clearTimeout(loadTimer);
    ID("timeline.notice").hidden = true;
    ID("timeline.alias").value = name;
    timelineView("loading");
    loadTimer = setTimeout(function () {
      if (name === "prod") showRecord("timeline-prod");
      else renderTimeline(emptyRecord(name));
    }, LOAD_MS);
  }

  function askRollback(i) {
    var r = current.records[i];
    var active = current.records.filter(function (x) {
      return x.active;
    })[0];
    var activeVersion = active ? active.minted_version : "—";
    openFor(dialogs.rollback, { alias: current.alias, active: activeVersion, target: r.minted_version }, { alias: current.alias, active: activeVersion, target: r.minted_version });
    openDialog("shell.dialog.rollback", "shell.dialog.rollback-cancel");
  }

  function askRetire(i) {
    var r = current.records[i];
    openFor(dialogs.retire, { alias: current.alias, version: r.minted_version, hint: r.minted_version }, { alias: current.alias, version: r.minted_version });
    retireVersion.value = "";
    dialogs.retire.update();
    openDialog("shell.dialog.retire", "shell.dialog.retire-cancel");
  }

  function checkSize() {
    var input = ID("timeline.page-size");
    var raw = input.value.trim();
    var n = Number(raw);
    var ok = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100;
    setFieldError(input, ok ? "" : MSG.pageSize);
  }

  // ---- hooks ----

  function setState(name) {
    clearTimers();
    busy = false;
    if (name === "loading") return timelineView("loading");
    if (name === "empty") return renderTimeline(emptyRecord(current ? current.alias : "prod"));
    if (name === "populated") return showRecord("timeline-prod");
    if (name !== "idle") throw new Error("unknown ledger state " + name);
    hideErrors();
    ID("promote.result").hidden = true;
    ID("timeline.notice").hidden = true;
    refreshPreflight();
  }

  function loadFixture(name) {
    clearTimers();
    busy = false;
    var fixture = L[name];
    if (/^timeline-/.test(name) && fixture) {
      hideErrors();
      return showRecord(name);
    }
    if (name === "promote-success") {
      hideErrors();
      return showResult(fixture);
    }
    if (fixture && fixture.status !== undefined) return showError(fixture.status, fixture.body);
    throw new Error("unknown ledger fixture " + name);
  }

  function inject(response) {
    clearTimers();
    busy = false;
    refreshPreflight();
    showError(response.status, response.body);
  }

  // ---- wiring ----

  FIX.aliases.forEach(function (a, i) {
    addAliasOption(a.alias);
    var option = h("option", a.alias);
    option.value = a.alias;
    ID("timeline.alias").appendChild(option);
    var row = ID("aliases.table").tBodies[0].rows[i];
    row.querySelector('[data-role="alias"]').textContent = a.alias;
    row.querySelector('[data-role="version"]').textContent = a.active_version;
    row.querySelector('[data-role="kind"]').textContent = a.record_kind;
    row.querySelector('[data-role="ordinal"]').textContent = String(a.generation_ordinal);
    row.querySelector('[data-role="created"]').textContent = a.created_at;
    ID("aliases.view-" + (i + 1)).addEventListener("click", function () {
      loadAlias(a.alias);
      ID("timeline.region").scrollIntoView({ block: "nearest" });
    });
  });

  fillSlots();
  form.addEventListener("input", refreshPreflight);
  form.addEventListener("change", refreshPreflight);
  ID("promote.source-history").addEventListener("change", function () {
    setSource(false);
  });
  ID("promote.source-recent").addEventListener("change", function () {
    setSource(true);
  });
  submit.addEventListener("click", askPromote);
  preview.addEventListener("click", showPreview);

  [1, 2, 3, 4, 5].forEach(function (n) {
    ID("timeline.rollback-" + n).addEventListener("click", function () {
      askRollback(n - 1);
    });
    ID("timeline.retire-" + n).addEventListener("click", function () {
      askRetire(n - 1);
    });
  });
  ID("timeline.alias").addEventListener("change", function () {
    loadAlias(this.value);
  });
  ID("timeline.page-size").addEventListener("input", checkSize);
  ID("error.roll-back-first").addEventListener("click", function (event) {
    event.preventDefault();
    var row = table.querySelector('tr[data-status="active"]:not([hidden])');
    if (row) {
      row.focus();
      row.scrollIntoView({ block: "nearest" });
    }
  });
  ID("mock.fixture").addEventListener("change", function () {
    loadFixture(this.value);
  });

  wireErrors("ledger");
  // Promote from a Query, Compare or Evidence result: tick the matching trace slot (the token is the full trace reference).
  Console.on("promote", function (event) {
    var token = event && event.trace;
    L.traces.forEach(function (t, i) {
      if (t.trace_reference === token) boxes[i].checked = true;
    });
    refreshPreflight();
    form.scrollIntoView({ block: "nearest" });
  });

  showRecord("timeline-prod");
  checkSize();
  refreshPreflight();
  return { setState: setState, inject: inject, loadFixture: loadFixture };
})();
Console.register("ledger", LedgerScreen);
