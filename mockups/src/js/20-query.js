var QueryScreen = (function () {
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var RESULT_STATES = ["success", "partial", "empty-evidence"];
  var ERROR_STATES = ["refusal-422", "validation-422", "error-500"];
  // setState renders these fixtures (UI-SPEC section 1, Mock row).
  var STATE_FIXTURE = {
    success: "q-success",
    partial: "q-partial",
    "empty-evidence": "q-empty-evidence",
    "refusal-422": "q-refusal",
    "validation-422": "q-validation",
    "error-500": "q-500",
  };
  var SHAPE_STATE = { refusal: "refusal-422", validation: "validation-422", "server-failure": "error-500", generic: "error-500" };
  var STREAM_CLOSED = "The stream closed before the final event.";
  var STREAMING = "Streaming. The answer arrives with the final event.";
  var MSG = {
    textEmpty: "Query text is empty. Enter at least one non-space character.",
    badJson: "Raw selector JSON is not valid JSON.",
    multiMember: "A selector may set only one member: alias, capability or harness.",
  };
  var root = $id("screen-query");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var timers = [];
  var evidenceRefs = [];
  var lastTrace = null;
  var lastLabel = "Default";
  var history = FIX.query.history.slice();
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

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  // Exactly one state view is visible. Field errors belong to one render, so every state change clears them.
  function showState(name) {
    STATES.forEach(function (s) {
      ID("state." + s).hidden = s !== name;
    });
    ID("result.panel").hidden = RESULT_STATES.indexOf(name) < 0;
    errorsBox.hidden = ERROR_STATES.indexOf(name) < 0;
    var running = name === "running";
    ID("run.spinner").hidden = !running;
    setDisabled(ID("run.submit"), running);
    ID("mock.state-switcher").value = name;
    Array.prototype.forEach.call(root.querySelectorAll("[data-error-id]"), function (el) {
      setFieldError(el, "");
    });
    ID("run.message").hidden = true;
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
    root.querySelector('[data-role="evidence-wrap"]').hidden = false;
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

  function renderBadge(name, shown, text, reason) {
    var badge = ID("result." + name);
    badge.hidden = !shown;
    if (!shown) return;
    badge.textContent = text;
    badge.title = "operator diagnostics\n" + reason;
  }

  // opts.streaming renders the layout before the final event; opts.layoutSample labels the sample row.
  function renderResult(env, opts) {
    opts = opts || {};
    var partial = !!env.partial;
    var answer = ID("result.answer");
    var text = opts.streaming ? STREAMING : env.answer || "No answer was produced.";
    answer.textContent = text;
    answer.classList.toggle("muted", opts.streaming || !env.answer);
    ID("result.depth").textContent = "depth: " + (env.depth_label || "not answered");
    ID("result.depth").title = "operator diagnostics\ndepth_label: " + env.depth_label;
    renderBadge("partial", partial, "▲ partial", "stop_reason: " + env.stop_reason);
    renderBadge("degraded", !!env.degraded, "▲ degraded", "degradation_reason: " + env.degradation_reason);
    root.querySelector('[data-role="stop-reason"]').textContent = "stop_reason: " + env.stop_reason;

    evidenceRefs = [];
    root.querySelector('[data-role="evidence-wrap"]').hidden = env.evidence.length === 0;
    for (var n = 1; n <= 5; n++) {
      if (env.evidence[n - 1]) fillEvidence(n, env.evidence[n - 1]);
      else ID("evidence.open-" + n).closest("tr").hidden = true;
    }
    renderTokens(env.token_accounting);
    renderSeam(env.seam_events);
    root.querySelector('[data-role="layout-sample"]').hidden = !opts.layoutSample;

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
    root.querySelector('[data-role="no-trace"]').hidden = !!lastTrace || !!opts.streaming;
    ID("result.copy-trace").hidden = !lastTrace;

    setDisabled(ID("result.promote"), partial);
    root.querySelector('[data-role="no-promote"]').hidden = !partial;
    showState(opts.state || (partial ? "partial" : env.evidence.length === 0 ? "empty-evidence" : "success"));
  }

  // Classifies a response and shows its result layout or its error shape; returns the shape.
  function applyResponse(status, body, opts) {
    var shape = classifyResponse(status, body);
    if (shape === "result") renderResult(body, opts);
    else {
      showState(SHAPE_STATE[shape]);
      renderError("query", status, body, opts);
    }
    return shape;
  }

  function applyFixture(name) {
    var fx = FIX.query[name];
    if (!fx) throw new Error("unknown query fixture " + name);
    if (fx.stream_closed) return applyResponse(0, "", { text: STREAM_CLOSED });
    return applyResponse(fx.status, fx.body, { layoutSample: !!fx.layout_sample });
  }

  function renderHistory() {
    for (var n = 1; n <= 3; n++) {
      var row = ID("history.open-" + n).closest("tr");
      var entry = history[n - 1];
      row.hidden = !entry;
      if (!entry) continue;
      cell(row, 0, entry.time);
      cell(row, 1, entry.selector);
      cell(row, 2, entry.trace_token.slice(0, 8));
      cell(row, 3, entry.partial ? "partial" : "—");
    }
  }

  function remember(env) {
    if (!env.trace_token) return;
    var d = new Date();
    history.unshift({ time: d.toISOString().slice(0, 19).replace("T", " "), selector: lastLabel, trace_token: env.trace_token, partial: !!env.partial });
    history = history.slice(0, 3);
    renderHistory();
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
    if (!focus) ID("run.message").hidden = true;
    return { ok: !focus, selector: override !== null ? override : picker.value(), focus: focus };
  }

  var picker = Picker.attach("query", function () {
    if (touched) validate();
  });

  // The fixture a Run ends in: the Fixture select wins, otherwise the State select (idle and running fall back to success).
  function pickFixture() {
    var variant = ID("mock.fixture").value;
    if (variant !== "standard") return variant;
    return STATE_FIXTURE[ID("mock.state-switcher").value] || "q-success";
  }

  function finish(name) {
    var fx = FIX.query[name];
    var streaming = ID("run.stream").checked || !!fx.stream_closed;
    if (!streaming || classifyResponse(fx.status, fx.body) !== "result") {
      if (applyFixture(name) === "result") remember(fx.body);
      return;
    }
    var env = fx.body;
    var rows = fx.stream_closed ? env.evidence.slice(0, 1) : env.evidence;
    renderResult({ answer: "", evidence: [], trace_token: null, depth_label: null, partial: false, degraded: false, token_accounting: [], seam_events: [] }, { streaming: true, state: "success" });
    rows.forEach(function (ref, i) {
      later(200 * (i + 1), function () {
        fillEvidence(i + 1, ref);
      });
    });
    later(200 * (rows.length + 1), function () {
      if (applyFixture(name) === "result") remember(env);
    });
  }

  function run() {
    touched = true;
    var check = validate();
    if (!check.ok) {
      var message = ID("run.message");
      message.textContent = "Run blocked. Fix the message shown above.";
      message.hidden = false;
      check.focus.focus();
      return;
    }
    cancelTimers();
    lastLabel = selectorLabel(check.selector);
    var name = pickFixture();
    showState("running");
    later(800, function () {
      finish(name);
    });
  }

  function setMode(next) {
    mode = next;
    root.setAttribute("data-mode", mode);
    ID("mode.query").setAttribute("aria-selected", String(mode === "query"));
    ID("mode.compare").setAttribute("aria-selected", String(mode === "compare"));
  }

  function setState(name) {
    cancelTimers();
    if (STATES.indexOf(name) < 0) throw new Error("unknown query state " + name);
    if (name === "idle" || name === "running") showState(name);
    else applyFixture(STATE_FIXTURE[name]);
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
  ID("mock.state-switcher").addEventListener("change", function (event) {
    setState(event.target.value);
  });
  ID("mock.fixture").addEventListener("change", function (event) {
    cancelTimers();
    if (event.target.value === "standard") setState("success");
    else applyFixture(event.target.value);
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
  for (var row = 1; row <= 3; row++) {
    (function (n) {
      ID("history.open-" + n).addEventListener("click", function () {
        var entry = history[n - 1];
        if (!entry) return;
        Console.show("evidence");
        Console.emit("open-trace", { token: entry.trace_token });
      });
    })(row);
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

  wireErrors("query");
  buildResolutionTable();
  renderHistory();
  showState("idle");
  return {
    setMode: setMode,
    picker: picker,
    showState: showState,
    renderResult: renderResult,
    setState: setState,
    inject: function (response) {
      cancelTimers();
      applyResponse(response.status, response.body);
    },
    loadFixture: function (name) {
      cancelTimers();
      applyFixture(name);
    },
  };
})();
Console.register("query", QueryScreen);
