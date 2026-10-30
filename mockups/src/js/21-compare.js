// Compare mode of Query & Compare (GUI-05). Text only ever reaches the DOM through textContent (Pitfall 11).
var Compare = (function () {
  var MAX = 4;
  var root = $id("screen-query");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var TEXT_EMPTY = "Query text is empty. Enter at least one non-space character.";
  var model = [{ kind: "default", alias: "", tokens: [] }];
  var shown = [];
  var timers = [];
  var running = false;
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

  function later(ms, fn) {
    timers.push(setTimeout(fn, ms));
  }

  function cancel() {
    timers.forEach(clearTimeout);
    timers = [];
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

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  // Query-mode Run stays clickable; compare-mode Run is disabled while a blocker is active.
  function syncRun(blocked) {
    if (root.getAttribute("data-mode") !== "compare" || running) return;
    setDisabled(ID("run.submit"), blocked);
  }

  // Derives keys, parts, chips and messages from the model; the slots hold the controls.
  function update() {
    var blocked = model.length === 0;
    model.forEach(function (m, idx) {
      var i = idx + 1;
      var v = selectorOf(m);
      var msg = blockerOf(v);
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
    });
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

  // A column is one q-success-shaped result; r is {key, arm, resolve, body}.
  function fillHeader(c, r) {
    C(c, "header").textContent = r.key + " · " + (r.arm || "unresolved");
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
    for (var n = 1; n <= 5; n++) {
      var row = C(c, "open-" + n).closest("tr");
      var ref = env.evidence[n - 1];
      row.hidden = !ref;
      if (!ref) continue;
      [String(n), ref.ref, ref.namespace, ref.kind, typeof ref.score === "number" ? ref.score.toFixed(4) : "—"].forEach(function (text, i) {
        row.children[i].textContent = text;
      });
    }
    fillTokens(C(c, "tokens"), env.token_accounting);
    fillSeam(C(c, "seam"), env.seam_events);
    C(c, "promote").title = partial ? "A partial run cannot be promoted." : "";
  }

  function showColumns(results) {
    shown = results;
    ID("compare.columns").hidden = false;
    for (var c = 1; c <= MAX; c++) {
      var r = results[c - 1];
      C(c, "panel").hidden = !r;
      if (!r) continue;
      fillHeader(c, r);
      fillBody(c, r);
    }
  }

  function describe(m) {
    var v = selectorOf(m);
    var res = Resolution.resolve(v);
    return { value: v, key: comparisonKey(v), arm: res.arm, resolve: res.text };
  }

  function run() {
    var textBox = ID("text.input");
    if (textBox.value.trim() === "") {
      setFieldError(textBox, TEXT_EMPTY);
      ID("text.error").focus();
      return;
    }
    setFieldError(textBox, "");
    cancel();
    running = true;
    hideColumns();
    QueryScreen.showState("running");
    var specs = model.map(describe);
    later(800, function () {
      hideStates();
      var body = FIX.query["q-success"].body;
      showColumns(
        specs.map(function (s) {
          return { key: s.key, arm: s.arm, resolve: s.resolve, body: body };
        })
      );
      running = false;
      update();
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
    var hit = button && /^query\.row(\d)\.remove$/.exec(button.getAttribute("data-mock-id"));
    if (!hit) return;
    model.splice(+hit[1] - 1, 1);
    paint();
    ID("compare.add").focus();
  });
  ID("compare.add").addEventListener("click", function () {
    if (model.length >= MAX) return;
    model.push({ kind: "default", alias: "", tokens: [] });
    paint();
    R(model.length, "kind").focus();
  });

  for (var c = 1; c <= MAX; c++) {
    (function (col) {
      C(col, "trace-link").addEventListener("click", function (event) {
        event.preventDefault();
        var r = shown[col - 1];
        if (!r || !r.body.trace_token) return;
        Console.show("evidence");
        Console.emit("open-trace", { token: r.body.trace_token });
      });
      for (var n = 1; n <= 5; n++) {
        (function (slot) {
          C(col, "open-" + slot).addEventListener("click", function () {
            var r = shown[col - 1];
            var ref = r && r.body.evidence[slot - 1];
            if (!ref) return;
            Console.show("evidence");
            Console.emit("open-evidence", { ref: { id: ref.ref, namespace: ref.namespace, kind: ref.kind }, score: ref.score });
          });
        })(n);
      }
    })(c);
  }

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

  new MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ["data-mode"] });
  hideColumns();
  paint();
  return { run: run, loadFixture: function () {} };
})();
