WIRED["query GET /log"] = true;

var QueryScreen = (function () {
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var RESULT_STATES = ["success", "partial", "empty-evidence"];
  var ERROR_STATES = ["refusal-422", "validation-422", "error-500"];
  var SHAPE_STATE = { refusal: "refusal-422", validation: "validation-422", "server-failure": "error-500", generic: "error-500" };
  var MEMBERS = ["alias", "capability", "harness"];
  var RECEIVING = "Receiving evidence";
  var NO_TRACE = "No trace token on this result.";
  var UNFINISHED = "The run did not finish.";
  var DISCONNECTED = "The stream closed before the final event. Evidence received so far is shown below; the run is not complete. Run again to retry.";
  var MSG = {
    textEmpty: "Query text is empty. Enter at least one non-space character.",
    badJson: "Raw selector JSON is not valid JSON.",
    multiMember: "A selector may set only one member: alias, capability or harness.",
  };
  var root = $id("screen-query");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var evidenceRefs = [];
  var lastTrace = null;
  var runLog = SessionLog("databasise.console.history", 50);
  var controller = null;
  var touched = false;
  var mode = "query";

  function ID(name) {
    return $id("query." + name);
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
    Array.prototype.forEach.call(root.querySelectorAll("[data-error-id]"), function (el) {
      setFieldError(el, "");
    });
    ID("run.message").hidden = true;
  }

  function cell(row, i, text) {
    row.children[i].textContent = text;
  }

  // Fills every evidence row from the refs, however many there are. evidenceRefs keeps each EvidenceRef object unchanged.
  function fillEvidence(refs) {
    evidenceRefs = refs.slice();
    ensureRows(ID("evidence.table").tBodies[0], refs.length).forEach(function (row, i) {
      var ref = refs[i];
      cell(row, 0, String(i + 1));
      cell(row, 1, ref.ref);
      cell(row, 2, ref.namespace);
      cell(row, 3, ref.kind);
      cell(row, 4, typeof ref.score === "number" ? ref.score.toFixed(4) : "—");
      cell(row, 5, ref.tier === null || ref.tier === undefined ? "—" : String(ref.tier));
    });
    root.querySelector('[data-role="evidence-wrap"]').hidden = refs.length === 0;
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

  // Open trace, Copy, promote from this result: enabled only for a finished run that carries a trace token (IN-JSA-08).
  // phase is "streaming" (before the final event), "unfinished" (the stream ended without one) or "done" (env is the envelope).
  function syncTraceControls(env, phase) {
    var done = phase === "done";
    lastTrace = done ? env.trace_token || null : null;
    var partial = done && !!env.partial;
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
    var reason = root.querySelector('[data-role="no-trace"]');
    reason.textContent = phase === "unfinished" ? UNFINISHED : NO_TRACE;
    reason.hidden = phase === "streaming" || !!lastTrace;
    ID("result.copy-trace").hidden = !lastTrace;
    setDisabled(ID("result.promote"), !done || partial || !lastTrace);
    setDisabled(ID("result.compare"), phase === "streaming");
    root.querySelector('[data-role="no-promote"]').hidden = !partial;
  }

  function renderResult(env) {
    var partial = !!env.partial;
    var answer = ID("result.answer");
    answer.textContent = env.answer || "No answer was produced.";
    answer.classList.toggle("muted", !env.answer);
    ID("result.depth").hidden = false;
    ID("result.depth").textContent = "depth: " + (env.depth_label || "not answered");
    ID("result.depth").title = "operator diagnostics\ndepth_label: " + env.depth_label;
    renderBadge("partial", partial, "▲ partial", "stop_reason: " + env.stop_reason);
    renderBadge("degraded", !!env.degraded, "▲ degraded", "degradation_reason: " + env.degradation_reason);
    root.querySelector('[data-role="stop-reason"]').textContent = "stop_reason: " + env.stop_reason;
    fillEvidence(env.evidence);
    renderTokens(env.token_accounting);
    renderSeam(env.seam_events);
    syncTraceControls(env, "done");
    showState(partial ? "partial" : env.evidence.length === 0 ? "empty-evidence" : "success");
  }

  // Classifies a response and shows its result layout or its error shape; returns the shape. The state views print the real status (IN-JSA-09).
  function applyResponse(status, body) {
    var shape = classifyResponse(status, body);
    if (shape === "result") renderResult(body);
    else {
      showState(SHAPE_STATE[shape]);
      var note = ID("state." + SHAPE_STATE[shape]).querySelector("p");
      if (shape === "refusal") note.textContent = "The server refused the request (HTTP " + status + ").";
      else if (shape === "validation") note.textContent = "The server found invalid fields (HTTP " + status + ").";
      renderError("query", status, body);
    }
    return shape;
  }

  function renderHistory() {
    var entries = runLog.all();
    ensureRows(ID("history.table").tBodies[0], entries.length).forEach(function (row, i) {
      var entry = entries[i];
      cell(row, 0, String(entry.timestamp).slice(0, 19).replace("T", " "));
      cell(row, 1, selectorLabel(entry.selector));
      cell(row, 2, entry.trace_token ? String(entry.trace_token).slice(0, 8) : "—");
      cell(row, 3, "—");
      setDisabled(row.querySelector("button"), !entry.trace_token);
    });
  }

  function remember(env, body) {
    runLog.add({ query: body.query.text, selector: body.selector, trace_token: env.trace_token, timestamp: new Date().toISOString() });
    renderHistory();
  }

  // Raw selector JSON holds exactly one member with the right type (WR-JSA-01); {} is Default.
  function memberOk(key, value) {
    if (key === "capability") {
      return (
        Array.isArray(value) &&
        value.length > 0 &&
        value.every(function (token) {
          return typeof token === "string";
        })
      );
    }
    return typeof value === "string";
  }

  // Blockers, in the UI-SPEC order: text, raw selector JSON, then the picker. Returns {ok, selector, focus}.
  function validate() {
    var textBox = ID("text.input");
    var jsonBox = ID("advanced.selector-json");
    var raw = jsonBox.value.trim();
    var textMsg = textBox.value.trim() === "" ? MSG.textEmpty : "";
    var jsonMsg = "";
    var override = null;
    var hasOverride = false;
    if (raw !== "") {
      var parsed = null;
      try {
        parsed = JSON.parse(raw);
      } catch (e) {
        jsonMsg = MSG.badJson;
      }
      if (!jsonMsg) {
        if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) jsonMsg = MSG.badJson;
        else {
          var keys = Object.keys(parsed).filter(function (k) {
            return parsed[k] !== null;
          });
          var known = keys.every(function (k) {
            return MEMBERS.indexOf(k) >= 0;
          });
          if (keys.length > 1 && known) jsonMsg = MSG.multiMember;
          else if (keys.length > 1 || (keys.length === 1 && !(known && memberOk(keys[0], parsed[keys[0]])))) jsonMsg = MSG.badJson;
          else {
            hasOverride = true;
            if (keys.length === 1) {
              override = {};
              override[keys[0]] = parsed[keys[0]];
            }
          }
        }
      }
    }
    var pickMsg = raw !== "" ? "" : picker.blockers()[0] || "";
    setFieldError(textBox, textMsg);
    setFieldError(jsonBox, jsonMsg);
    setFieldError(ID("selector.group"), pickMsg);
    var focus = textMsg ? ID("text.error") : jsonMsg ? ID("advanced.selector-json-error") : pickMsg ? ID("selector.error") : null;
    if (jsonMsg) ID("advanced.panel").open = true;
    if (!focus) ID("run.message").hidden = true;
    return { ok: !focus, selector: hasOverride ? override : picker.value(), focus: focus };
  }

  var picker = Picker.attach("query", function () {
    if (touched) validate();
  });

  // The layout before the final event: a running notice, rows as they arrive, nothing to open or promote yet.
  function beginStream() {
    var answer = ID("result.answer");
    answer.textContent = RECEIVING;
    answer.classList.add("muted");
    ID("result.depth").hidden = true;
    renderBadge("partial", false);
    renderBadge("degraded", false);
    fillEvidence([]);
    renderTokens([]);
    renderSeam([]);
    syncTraceControls(null, "streaming");
    showState("running");
    ID("result.panel").hidden = false;
  }

  // The stream ended without a final event: the generic view, the rows already received stay, nothing is promoted or remembered.
  function showDisconnected() {
    showState("error-500");
    ID("result.panel").hidden = false;
    var answer = ID("result.answer");
    answer.textContent = "No answer was produced.";
    answer.classList.add("muted");
    syncTraceControls(null, "unfinished");
    renderError("query", 0, null, { text: DISCONNECTED });
  }

  // A read that fails before any byte arrives: the server went away.
  function lost(mine) {
    return function () {
      if (mine !== controller) return;
      Console.emit("unreachable");
      applyResponse(0, "server unreachable");
    };
  }

  function runStream(body, mine) {
    var refs = [];
    var finalEvent = null;
    beginStream();
    api("POST", "/query/stream", body, { raw: true, signal: mine.signal, kind: "query" }).then(function (result) {
      if (result.aborted || mine !== controller) return;
      if (result.status === 0) return applyResponse(0, result.body);
      var res = result.res;
      if (!res.ok || (res.headers.get("content-type") || "").indexOf("text/event-stream") !== 0) {
        // Not a stream (a refusal, a validation list, a 500): nothing is parsed as events.
        return res.text().then(function (text) {
          var parsed = text;
          try {
            parsed = JSON.parse(text);
          } catch (ignored) {
            // not JSON: the text itself is the body
          }
          if (mine === controller) applyResponse(res.status, parsed);
        }, lost(mine));
      }
      return readStream(
        res,
        function (ref) {
          if (mine !== controller) return;
          refs.push(ref);
          fillEvidence(refs);
        },
        function (event) {
          finalEvent = event;
        }
      ).then(function (finished) {
        if (mine !== controller) return;
        if (!finished) return showDisconnected();
        var env = {};
        Object.keys(finalEvent).forEach(function (key) {
          if (key !== "kind") env[key] = finalEvent[key];
        });
        env.evidence = refs;
        renderResult(env);
        remember(env, body);
      }, lost(mine));
    });
  }

  function run() {
    if (mode === "compare") return Compare.run();
    touched = true;
    var check = validate();
    if (!check.ok) {
      var message = ID("run.message");
      message.textContent = "Run blocked. Fix the message shown above.";
      message.hidden = false;
      check.focus.focus();
      return;
    }
    if (controller) controller.abort();
    var mine = (controller = new AbortController());
    var body = { query: { text: ID("text.input").value }, selector: check.selector };
    if (ID("run.stream").checked) return runStream(body, mine);
    showState("running");
    api("POST", "/query", body, { signal: mine.signal, kind: "query" }).then(function (result) {
      if (result.aborted || mine !== controller) return;
      if (applyResponse(result.status, result.body) === "result") remember(result.body, body);
    });
  }

  function setMode(next) {
    mode = next;
    root.setAttribute("data-mode", mode);
    ID("mode.query").setAttribute("aria-selected", String(mode === "query"));
    ID("mode.compare").setAttribute("aria-selected", String(mode === "compare"));
    ID("run.submit").textContent = mode === "compare" ? "Run compare" : "Run query";
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

  // The index of the table row that holds a clicked button.
  function rowIndex(event) {
    var button = event.target.closest("button");
    if (!button || button.disabled) return -1;
    var row = button.closest("tr");
    return Array.prototype.indexOf.call(row.parentNode.children, row);
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
  // One delegated listener serves every evidence row, cloned ones included. The payload carries the EvidenceRef unchanged:
  // the server refuses a renamed key (18-RESEARCH Pitfall 2).
  ID("evidence.table").addEventListener("click", function (event) {
    var ref = evidenceRefs[rowIndex(event)];
    if (!ref) return;
    Console.show("evidence");
    Console.emit("open-evidence", { ref: ref, score: ref.score, trace_token: lastTrace });
  });
  ID("history.table").addEventListener("click", function (event) {
    var entry = runLog.all()[rowIndex(event)];
    if (!entry || !entry.trace_token) return;
    Console.show("evidence");
    Console.emit("open-trace", { token: entry.trace_token });
  });
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
  setMode("query");
  renderHistory();
  showState("idle");
  return {
    setMode: setMode,
    picker: picker,
    showState: showState,
    renderResult: renderResult,
    applyResponse: applyResponse,
    remember: remember,
  };
})();
Console.register("query", QueryScreen);
