// Compare mode of Query & Compare (GUI-05). Text only ever reaches the DOM through textContent (Pitfall 11).
var Compare = (function () {
  var MAX = 4;
  var root = $id("screen-query");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var TEXT_EMPTY = "Query text is empty. Enter at least one non-space character.";
  var MSG = {
    zero: "Add at least one selector. A comparison with no selectors is refused.",
    one: "One selector runs as a plain query and returns a single result, not a set of columns.",
  };

  function duplicateMessage(key) {
    return 'Duplicate comparison key "' + key + '". Each selector must render a unique key; the server refuses duplicates after earlier arms have run.';
  }
  var model = [{ kind: "default", alias: "", tokens: [] }];
  var shown = [];
  var controller = null;
  var running = false;
  var lastBlocked = false;
  var lastMode = root.getAttribute("data-mode");

  function ID(name) {
    return $id("query." + name);
  }

  function R(i, name) {
    return ID("row" + i + "." + name);
  }

  function C(c, name) {
    return ID("col" + c + "." + name);
  }

  // Aborts the compare read in flight; its answer then renders nothing (WR-JSA-04).
  function cancel() {
    if (controller) controller.abort();
    controller = null;
    running = false;
  }

  function selectorOf(m) {
    if (m.kind === "alias") return { alias: m.alias };
    if (m.kind === "capability") return { capability: m.tokens };
    return null;
  }

  // Row-level blockers reuse the single-picker messages.
  function blockerOf(v) {
    if (v && v.capability && v.capability.length === 0) return SELECTOR_MSG.noCapability;
    if (v && v.alias !== undefined) {
      if (v.alias === "") return SELECTOR_MSG.noAlias;
      if (HASH_SHAPED.test(v.alias)) return SELECTOR_MSG.hashAlias;
    }
    return "";
  }

  function read(i) {
    return {
      kind: R(i, "kind").value,
      alias: R(i, "alias").value,
      tokens: Array.prototype.filter
        .call(R(i, "capability").options, function (o) {
          return o.selected;
        })
        .map(function (o) {
          return o.value;
        }),
    };
  }

  // Query-mode Run is QueryScreen's; compare-mode Run is disabled while a blocker is active or a run is in flight.
  function syncRun(blocked) {
    lastBlocked = blocked;
    if (root.getAttribute("data-mode") !== "compare") return;
    setDisabled(ID("run.submit"), blocked || running);
  }

  // Derives keys, parts, chips and messages from the model; the slots hold the controls.
  function update() {
    var keys = [];
    var dupKeys = [];
    var dupRows = [];
    model.forEach(function (m, idx) {
      var v = selectorOf(m);
      if (blockerOf(v)) return;
      var key = comparisonKey(v);
      // Exact comparison: the later occurrence is the one the server would refuse.
      if (keys.indexOf(key) >= 0) {
        dupRows.push(idx);
        if (dupKeys.indexOf(key) < 0) dupKeys.push(key);
      }
      keys.push(key);
    });
    var blocked = model.length === 0 || dupKeys.length > 0;
    model.forEach(function (m, idx) {
      var i = idx + 1;
      var v = selectorOf(m);
      var msg = blockerOf(v) || (dupRows.indexOf(idx) >= 0 ? duplicateMessage(comparisonKey(v)) : "");
      var row = R(i, "kind").closest('[data-role="row"]');
      Array.prototype.forEach.call(row.querySelectorAll("[data-part]"), function (part) {
        part.hidden = part.getAttribute("data-part") !== m.kind;
      });
      var chips = R(i, "chips");
      clearNode(chips);
      m.tokens.forEach(function (t) {
        chips.appendChild(h("span", t, "chip mono"));
      });
      R(i, "key").textContent = "Key: " + comparisonKey(v);
      var error = R(i, "error");
      error.textContent = msg;
      error.hidden = !msg;
      if (msg) blocked = true;
      setDisabled(R(i, "move-up"), i === 1);
      setDisabled(R(i, "move-down"), i === model.length);
    });
    var dup = ID("compare.warning-duplicate");
    clearNode(dup);
    dupKeys.forEach(function (key) {
      dup.appendChild(h("p", duplicateMessage(key)));
    });
    dup.hidden = dupKeys.length === 0;
    var count = ID("compare.warning-count");
    count.textContent = model.length === 0 ? MSG.zero : model.length === 1 ? MSG.one : "";
    count.setAttribute("data-state", model.length === 0 ? "warn" : "neutral");
    count.hidden = model.length > 1;
    setDisabled(ID("compare.add"), model.length >= MAX);
    ID("compare.add").closest(".cmp-add-row").querySelector('[data-role="cap-note"]').hidden = model.length < MAX;
    syncRun(blocked);
  }

  function paint() {
    for (var i = 1; i <= MAX; i++) {
      var m = model[i - 1];
      R(i, "kind").closest('[data-role="row"]').hidden = !m;
      if (!m) continue;
      R(i, "kind").value = m.kind;
      R(i, "alias").value = m.alias;
      Array.prototype.forEach.call(R(i, "capability").options, function (o) {
        o.selected = m.tokens.indexOf(o.value) >= 0;
      });
    }
    update();
  }

  function hideStates() {
    STATES.forEach(function (s) {
      ID("state." + s).hidden = true;
    });
    ID("result.panel").hidden = true;
    errorsBox.hidden = true;
  }

  function hideColumns() {
    shown = [];
    ID("compare.columns").hidden = true;
    for (var c = 1; c <= MAX; c++) C(c, "panel").hidden = true;
  }

  function sortedTokens(entries) {
    return entries.slice().sort(function (a, b) {
      return a.counted_by < b.counted_by ? -1 : a.counted_by > b.counted_by ? 1 : 0;
    });
  }

  function fillTokens(table, entries) {
    var body = table.tBodies[0];
    clearNode(body);
    var total = [0, 0, 0, 0];
    sortedTokens(entries).forEach(function (t) {
      var tr = h("tr");
      var first = h("td", t.counted_by, "mono");
      if (t.counted_by === "none") first.appendChild(h("div", "no tokenizer counted; the node may have raised", "muted"));
      tr.appendChild(first);
      [t.prompt_tokens, t.completion_tokens, t.cached_read_tokens, t.call_count].forEach(function (v, i) {
        total[i] += v;
        tr.appendChild(h("td", String(v)));
      });
      body.appendChild(tr);
    });
    var sum = h("tr");
    sum.appendChild(h("td", "Total"));
    total.forEach(function (v) {
      sum.appendChild(h("td", String(v)));
    });
    body.appendChild(sum);
  }

  function fillSeam(table, events) {
    var body = table.tBodies[0];
    clearNode(body);
    if (events.length === 0) {
      var tr = h("tr");
      var td = h("td", "No seam events. Query wirings do not mutate stores.", "muted");
      td.colSpan = 3;
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    events.forEach(function (e) {
      var row = h("tr");
      row.appendChild(h("td", e.component, "mono"));
      var outcome = h("td");
      var badge = h("span", e.outcome, "badge");
      badge.setAttribute("data-state", e.outcome === "completed" ? "ok" : e.outcome === "halted" ? "warn" : "fail");
      outcome.appendChild(badge);
      row.appendChild(outcome);
      var s = e.spend;
      row.appendChild(h("td", s ? s.counted_by + ": " + s.prompt_tokens + " / " + s.completion_tokens + " / " + s.cached_read_tokens + " / " + s.call_count : "—"));
      body.appendChild(row);
    });
  }

  function fillBadge(c, name, shownFlag, reason) {
    var badge = C(c, name);
    badge.hidden = !shownFlag;
    if (!shownFlag) return;
    badge.textContent = "▲ " + name;
    badge.title = "operator diagnostics\n" + reason;
  }

  // A column is one response envelope; r is {key, selector, arm, resolve, body}.
  function fillHeader(c, r) {
    C(c, "header").textContent = r.arm ? r.key + " · " + r.arm : r.key;
    C(c, "resolves-to").textContent = r.resolve;
  }

  function fillBody(c, r) {
    var env = r.body;
    var partial = !!env.partial;
    var answer = C(c, "answer");
    answer.textContent = env.answer || "No answer was produced.";
    answer.classList.toggle("muted", !env.answer);
    C(c, "depth").textContent = "depth: " + (env.depth_label || "not answered");
    C(c, "depth").title = "operator diagnostics\ndepth_label: " + env.depth_label;
    fillBadge(c, "partial", partial, "stop_reason: " + env.stop_reason);
    fillBadge(c, "degraded", !!env.degraded, "degradation_reason: " + env.degradation_reason);
    C(c, "state-partial").hidden = !partial;
    C(c, "state-partial").querySelector('[data-role="stop-reason"]').textContent = "stop_reason: " + env.stop_reason;
    var panel = C(c, "panel");
    panel.querySelector('[data-role="evidence-wrap"]').hidden = env.evidence.length === 0;
    ensureRows(C(c, "evidence").tBodies[0], env.evidence.length).forEach(function (row, i) {
      var ref = env.evidence[i];
      [String(i + 1), ref.ref, ref.namespace, ref.kind, typeof ref.score === "number" ? ref.score.toFixed(4) : "—", ref.tier === null || ref.tier === undefined ? "—" : String(ref.tier)].forEach(function (text, k) {
        row.children[k].textContent = text;
      });
    });
    fillTokens(C(c, "tokens"), env.token_accounting);
    fillSeam(C(c, "seam"), env.seam_events);
    setDisabled(C(c, "promote"), partial);
    C(c, "promote").title = partial ? "A partial run cannot be promoted." : "";
    panel.querySelector('[data-role="no-promote"]').hidden = !partial;
  }

  // Below 768 px the CSS shows only the active column; the tabs pick it.
  function selectTab(active) {
    for (var c = 1; c <= MAX; c++) {
      var r = shown[c - 1];
      var tab = ID("compare.tab" + c);
      tab.hidden = !r;
      tab.textContent = r ? r.key : "";
      tab.setAttribute("aria-selected", String(c === active));
      C(c, "panel").setAttribute("data-active", String(c === active));
    }
  }

  function renderDiff() {
    var count = Object.create(null);
    shown.forEach(function (r) {
      r.body.evidence.forEach(function (e) {
        count[e.ref] = (count[e.ref] || 0) + 1;
      });
    });
    var shared = Object.keys(count).filter(function (ref) {
      return count[ref] > 1;
    }).length;
    var totals = shown.map(function (r) {
      var sum = r.body.token_accounting.reduce(function (acc, t) {
        return acc + t.prompt_tokens + t.completion_tokens;
      }, 0);
      return r.key + " " + sum;
    });
    ID("compare.diff").textContent = "Evidence refs shared between columns: " + shared + ". Tokens per column (prompt + completion): " + totals.join(" · ") + ".";
  }

  function showColumns(results) {
    shown = results;
    ID("compare.columns").hidden = false;
    ID("compare.diff").textContent = "";
    for (var c = 1; c <= MAX; c++) {
      var r = results[c - 1];
      C(c, "panel").hidden = !r;
      if (!r) continue;
      fillHeader(c, r);
      fillBody(c, r);
    }
    selectTab(1);
    renderDiff();
  }

  // One column per requested selector, read from the response map by that selector's own comparison key.
  function columnsOf(chosen, body) {
    var cols = [];
    chosen.forEach(function (m) {
      var v = selectorOf(m);
      var key = comparisonKey(v);
      if (!Object.prototype.hasOwnProperty.call(body, key)) return;
      var res = Resolution.resolve(v);
      cols.push({ key: key, selector: v, arm: res.arm, resolve: res.text, body: body[key] });
    });
    return cols;
  }

  function run() {
    var textBox = ID("text.input");
    if (textBox.value.trim() === "") {
      setFieldError(textBox, TEXT_EMPTY);
      ID("text.error").focus();
      return;
    }
    setFieldError(textBox, "");
    var text = textBox.value;
    var chosen = model.slice();
    // Default is {} for compare (null is a 422 here); /query keeps null.
    var sent = chosen.map(function (m) {
      return selectorOf(m) || {};
    });
    cancel();
    var mine = (controller = new AbortController());
    running = true;
    syncRun(lastBlocked);
    QueryScreen.showState("running");
    api("POST", "/compare", { query: { text: text }, selectors: sent }, { signal: mine.signal, kind: "compare" }).then(function (result) {
      if (result.aborted || mine !== controller) return;
      controller = null;
      running = false;
      syncRun(lastBlocked);
      // Two or more selectors answer a map keyed by comparison key; one answers a bare envelope. The count sent decides, never the keys (D-11).
      if (sent.length > 1 && classifyResponse(result.status, result.body) === "result") {
        var cols = columnsOf(chosen, result.body);
        hideStates();
        showColumns(cols);
        cols
          .slice()
          .reverse()
          .forEach(function (col) {
            QueryScreen.remember(col.body, { query: { text: text }, selector: col.selector });
          });
      } else if (QueryScreen.applyResponse(result.status, result.body) === "result") {
        QueryScreen.remember(result.body, { query: { text: text }, selector: selectorOf(chosen[0]) });
      }
    });
  }

  // Mode changes arrive from the tab buttons and from "Compare this query"; both only set data-mode.
  function sync() {
    var mode = root.getAttribute("data-mode");
    if (mode === lastMode) return;
    lastMode = mode;
    cancel();
    running = false;
    if (mode === "compare") {
      if (shown.length) hideStates();
      else QueryScreen.showState("idle");
    } else {
      hideColumns();
      QueryScreen.showState("idle");
    }
    update();
  }

  function onEdit(event) {
    var row = event.target.closest('[data-role="row"]');
    if (!row) return;
    var i = Array.prototype.indexOf.call(ID("compare.builder").querySelectorAll('[data-role="row"]'), row) + 1;
    if (event.target === R(i, "alias-picker") && event.target.value) {
      R(i, "alias").value = event.target.value;
      R(i, "kind").value = "alias";
    }
    model[i - 1] = read(i);
    update();
  }

  var builder = ID("compare.builder");
  builder.addEventListener("input", onEdit);
  builder.addEventListener("change", onEdit);
  builder.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    var hit = button && /^query\.row(\d)\.(remove|move-up|move-down)$/.exec(button.getAttribute("data-mock-id"));
    if (!hit) return;
    var idx = +hit[1] - 1;
    if (hit[2] === "remove") {
      model.splice(idx, 1);
      paint();
      ID("compare.add").focus();
      return;
    }
    var to = idx + (hit[2] === "move-up" ? -1 : 1);
    if (to < 0 || to >= model.length) return;
    model.splice(to, 0, model.splice(idx, 1)[0]);
    paint();
    R(to + 1, hit[2]).focus();
  });
  ID("compare.add").addEventListener("click", function () {
    if (model.length >= MAX) return;
    model.push({ kind: "default", alias: "", tokens: [] });
    paint();
    R(model.length, "kind").focus();
  });

  // One delegated listener serves every column, cloned ones included: the column is read from the panel that holds the control.
  ID("compare.columns").addEventListener("click", function (event) {
    var el = event.target.closest("a, button");
    if (!el || el.disabled) return;
    var id = el.getAttribute("data-mock-id") || "";
    var tab = /^query\.compare\.tab(\d+)$/.exec(id);
    if (tab) return selectTab(+tab[1]);
    var panel = el.closest(".cmp-col");
    var which = panel && /^query\.col(\d+)\.panel$/.exec(panel.getAttribute("data-mock-id"));
    var r = which && shown[+which[1] - 1];
    if (!r) return;
    var env = r.body;
    if (/\.trace-link$/.test(id)) {
      event.preventDefault();
      if (!env.trace_token) return;
      Console.show("evidence");
      Console.emit("open-trace", { token: env.trace_token });
    } else if (/\.promote$/.test(id)) {
      Console.show("ledger");
      Console.emit("promote", { trace: env.trace_token });
    } else if (/\.open-\d+$/.test(id)) {
      // The EvidenceRef goes on unchanged: the server refuses a renamed key (18-RESEARCH Pitfall 2).
      var row = el.closest("tr");
      var ref = env.evidence[Array.prototype.indexOf.call(row.parentNode.children, row)];
      if (!ref) return;
      Console.show("evidence");
      Console.emit("open-evidence", { ref: ref, score: ref.score, trace_token: env.trace_token });
    }
  });

  for (var i = 1; i <= MAX; i++) {
    var picker = R(i, "alias-picker");
    FIX.aliases.forEach(function (a) {
      var option = h("option", a.alias + " (" + a.arm + ", " + a.active_version + ")");
      option.value = a.alias;
      picker.appendChild(option);
    });
    R(i, "kind").setAttribute("data-field-loc", "body.selectors." + (i - 1));
    R(i, "kind").setAttribute("data-error-id", "query.row" + i + ".error");
  }

  ID("text.input").addEventListener("input", function (event) {
    var box = event.target;
    if (root.getAttribute("data-mode") === "compare" && box.getAttribute("aria-invalid")) setFieldError(box, box.value.trim() === "" ? TEXT_EMPTY : "");
  });
  new MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ["data-mode"] });
  hideColumns();
  paint();
  return { run: run, cancel: cancel };
})();
