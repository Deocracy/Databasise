var QueryScreen = (function () {
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var RESULT_STATES = ["success", "partial", "empty-evidence"];
  var MSG = {
    textEmpty: "Query text is empty. Enter at least one non-space character.",
    badJson: "Raw selector JSON is not valid JSON.",
    multiMember: "A selector may set only one member: alias, capability or harness.",
  };
  var root = $id("screen-query");
  var timers = [];
  var evidenceRefs = [];
  var lastTrace = null;
  var touched = false;
  var mode = "query";

  function ID(name) {
    return $id("query." + name);
  }

  function later(ms, fn) {
    timers.push(setTimeout(fn, ms));
  }

  function cancelTimers() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function showState(name) {
    STATES.forEach(function (s) {
      var view = ID("state." + s);
      if (view) view.hidden = s !== name; // the error views arrive with the shared error shapes
    });
    ID("result.panel").hidden = RESULT_STATES.indexOf(name) < 0;
    var running = name === "running";
    ID("run.spinner").hidden = !running;
    var submit = ID("run.submit");
    submit.disabled = running;
    if (running) submit.setAttribute("aria-disabled", "true");
    else submit.removeAttribute("aria-disabled");
  }

  function cell(row, i, text) {
    row.children[i].textContent = text;
  }

  function fillEvidence(n, ref) {
    evidenceRefs[n - 1] = ref;
    var row = ID("evidence.open-" + n).closest("tr");
    cell(row, 0, String(n));
    cell(row, 1, ref.ref);
    cell(row, 2, ref.namespace);
    cell(row, 3, ref.kind);
    cell(row, 4, typeof ref.score === "number" ? ref.score.toFixed(4) : "—");
    row.hidden = false;
  }

  function renderTokens(entries) {
    var body = ID("tokens.table").tBodies[0];
    clearNode(body);
    var total = [0, 0, 0, 0];
    entries
      .slice()
      .sort(function (a, b) {
        return a.counted_by < b.counted_by ? -1 : a.counted_by > b.counted_by ? 1 : 0;
      })
      .forEach(function (t) {
        var values = [t.prompt_tokens, t.completion_tokens, t.cached_read_tokens, t.call_count];
        var tr = h("tr");
        var first = h("td", t.counted_by, "mono");
        if (t.counted_by === "none") first.appendChild(h("div", "no tokenizer counted; the node may have raised", "muted"));
        tr.appendChild(first);
        values.forEach(function (v, i) {
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

  function renderSeam(events) {
    var body = ID("seam.table").tBodies[0];
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

  function renderResult(env) {
    var partial = !!env.partial;
    var answer = ID("result.answer");
    answer.textContent = env.answer || "No answer was produced.";
    answer.classList.toggle("muted", !env.answer);
    ID("result.depth").textContent = "depth: " + (env.depth_label || "not answered");

    evidenceRefs = [];
    for (var n = 1; n <= 5; n++) {
      if (env.evidence[n - 1]) fillEvidence(n, env.evidence[n - 1]);
      else ID("evidence.open-" + n).closest("tr").hidden = true;
    }
    renderTokens(env.token_accounting);
    renderSeam(env.seam_events);

    lastTrace = env.trace_token;
    var link = ID("result.trace-link");
    if (lastTrace) {
      link.setAttribute("href", "#evidence");
      link.removeAttribute("aria-disabled");
      link.removeAttribute("tabindex");
    } else {
      link.removeAttribute("href");
      link.setAttribute("aria-disabled", "true");
      link.setAttribute("tabindex", "-1");
    }

    var promote = ID("result.promote");
    promote.disabled = partial;
    if (partial) promote.setAttribute("aria-disabled", "true");
    else promote.removeAttribute("aria-disabled");
    root.querySelector('[data-role="no-promote"]').hidden = !partial;
    showState("success");
  }

  // Blockers, in the UI-SPEC order: text, raw selector JSON, then the picker. Returns {ok, selector, focus}.
  function validate() {
    var textBox = ID("text.input");
    var jsonBox = ID("advanced.selector-json");
    var raw = jsonBox.value.trim();
    var textMsg = textBox.value.trim() === "" ? MSG.textEmpty : "";
    var jsonMsg = "";
    var override = null;
    if (raw !== "") {
      var parsed = null;
      try {
        parsed = JSON.parse(raw);
      } catch (e) {
        jsonMsg = MSG.badJson;
      }
      if (!jsonMsg) {
        if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) jsonMsg = MSG.badJson;
        else if (Object.keys(parsed).filter(function (k) { return parsed[k] !== null; }).length > 1) jsonMsg = MSG.multiMember;
        else override = parsed;
      }
    }
    var pickMsg = raw !== "" ? "" : picker.blockers()[0] || "";
    setFieldError(textBox, textMsg);
    setFieldError(jsonBox, jsonMsg);
    setFieldError(ID("selector.group"), pickMsg);
    var focus = textMsg ? ID("text.error") : jsonMsg ? ID("advanced.selector-json-error") : pickMsg ? ID("selector.error") : null;
    if (jsonMsg) ID("advanced.panel").open = true;
    ID("run.message").hidden = !(touched && focus);
    return { ok: !focus, selector: override !== null ? override : picker.value(), focus: focus };
  }

  var picker = Picker.attach("query", function () {
    if (touched) validate();
  });

  function pickFixture() {
    return "q-success";
  }

  function run() {
    touched = true;
    var check = validate();
    if (!check.ok) {
      ID("run.message").textContent = "Run blocked. Fix the message shown above.";
      ID("run.message").hidden = false;
      check.focus.focus();
      return;
    }
    cancelTimers();
    showState("running");
    later(800, function () {
      renderResult(FIX.query[pickFixture()].body);
    });
  }

  function setMode(next) {
    mode = next;
    root.setAttribute("data-mode", mode);
    ID("mode.query").setAttribute("aria-selected", String(mode === "query"));
    ID("mode.compare").setAttribute("aria-selected", String(mode === "compare"));
  }

  function buildResolutionTable() {
    var body = ID("selector.table").tBodies[0];
    Resolution.rows.forEach(function (r) {
      var tr = h("tr");
      tr.appendChild(h("td", selectorLabel(r.selector), "mono"));
      tr.appendChild(h("td", r.wiring || "not satisfiable"));
      tr.appendChild(h("td", r.node_count === null || r.node_count === undefined ? "—" : String(r.node_count)));
      tr.appendChild(h("td", r.outcome));
      body.appendChild(tr);
    });
  }

  ID("run.submit").addEventListener("click", run);
  ID("mode.query").addEventListener("click", function () {
    setMode("query");
  });
  ID("mode.compare").addEventListener("click", function () {
    setMode("compare");
  });
  ["text.input", "advanced.selector-json"].forEach(function (name) {
    ID(name).addEventListener("input", function () {
      if (touched) validate();
    });
  });
  ID("selector.table-toggle").addEventListener("click", function () {
    var wrap = root.querySelector('[data-role="resolution-wrap"]');
    wrap.hidden = !wrap.hidden;
    ID("selector.table-toggle").setAttribute("aria-expanded", String(!wrap.hidden));
    ID("selector.table-toggle").textContent = wrap.hidden ? "Show resolution table" : "Hide resolution table";
  });
  ID("result.trace-link").addEventListener("click", function (event) {
    event.preventDefault();
    if (!lastTrace) return;
    Console.show("evidence");
    Console.emit("open-trace", { token: lastTrace });
  });
  for (var slot = 1; slot <= 5; slot++) {
    (function (n) {
      ID("evidence.open-" + n).addEventListener("click", function () {
        var ref = evidenceRefs[n - 1];
        if (!ref) return;
        Console.show("evidence");
        Console.emit("open-evidence", { ref: { id: ref.ref, namespace: ref.namespace, kind: ref.kind }, score: ref.score });
      });
    })(slot);
  }
  ID("result.copy-trace").addEventListener("click", function () {
    if (lastTrace) copyText(lastTrace, root.querySelector('[data-role="copied"]'));
  });
  ID("result.promote").addEventListener("click", function () {
    Console.show("ledger");
    Console.emit("promote", { trace: lastTrace });
  });
  ID("result.compare").addEventListener("click", function () {
    setMode("compare");
  });

  buildResolutionTable();
  showState("idle");
  return {
    setMode: setMode,
    picker: picker,
    setState: function (name) {
      cancelTimers();
      if (STATES.indexOf(name) < 0) throw new Error("unknown query state " + name);
      if (name === "idle" || name === "running") showState(name);
      else renderResult(FIX.query["q-success"].body);
    },
    inject: function () {},
    loadFixture: function (name) {
      cancelTimers();
      renderResult(FIX.query[name].body);
    },
  };
})();
Console.register("query", QueryScreen);
