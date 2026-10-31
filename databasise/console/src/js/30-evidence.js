var EvidenceScreen = (function () {
  var STATES = ["idle", "loading", "resolved", "refusal"];
  var LOAD_MS = 300;
  var MSG = { noRef: "Enter an evidence ref.", noTrace: "Enter a trace reference." };
  var root = $id("screen-evidence");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var panes = { evidence: root.querySelector('[data-role="pane-evidence"]'), trace: root.querySelector('[data-role="pane-trace"]') };
  var cache = {};
  var tab = "evidence";
  var timer = null;
  var opener = null;
  var resolveCtl = null;
  var busyEl = null;
  var originLink = null;
  var loaded = null;
  var debugView = null;

  function ID(name) {
    return $id("evidence." + name);
  }

  // Token -> which trace fixture it resolves to, read from the query and compare fixtures (a partial body gives the partial trace).
  var TRACE_OF = {};
  var DEFAULT_TOKEN = {};
  (function scan(o) {
    if (Array.isArray(o)) return o.forEach(scan);
    if (o && typeof o === "object") {
      if (typeof o.trace_token === "string" && o.trace_token) {
        var name = o.partial ? "t-partial-debug" : "t-clean";
        TRACE_OF[o.trace_token] = TRACE_OF[o.trace_token] || name;
        DEFAULT_TOKEN[name] = DEFAULT_TOKEN[name] || o.trace_token;
      }
      Object.keys(o).forEach(function (k) {
        scan(o[k]);
      });
    }
  })([FIX.query, FIX.compare]);

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  function outcome() {
    return ID("mock.outcome").value;
  }

  // ---- evidence tab ----

  function evState(name) {
    STATES.forEach(function (s) {
      $id("evidence.state." + s).hidden = s !== name;
    });
  }

  function showTab(name) {
    tab = name;
    ["evidence", "trace"].forEach(function (n) {
      panes[n].hidden = n !== name;
      ID("tabs." + n).setAttribute("aria-selected", String(n === name));
    });
  }

  function hideErrors() {
    renderError("evidence", 200, null);
    errorsBox.hidden = true;
  }

  function showError(status, body) {
    var shape = renderError("evidence", status, body);
    errorsBox.hidden = shape === "result";
    if (shape !== "result") {
      if (tab === "evidence") evState(null);
      else traceView("none");
    }
  }

  function busy(on) {
    if (!busyEl) return;
    var row = busyEl.closest("tr");
    if (on) {
      busyEl.setAttribute("aria-busy", "true");
      busyEl.setAttribute("aria-label", "Opening");
      if (row) row.setAttribute("aria-busy", "true");
    } else {
      busyEl.removeAttribute("aria-busy");
      busyEl.removeAttribute("aria-label");
      if (row) row.removeAttribute("aria-busy");
      busyEl = null;
    }
  }

  function renderRecord(ref, rec, score) {
    var header = ID("inspector.header");
    clearNode(header);
    header.appendChild(h("span", rec.id, "mono"));
    header.appendChild(h("span", ref.namespace, "chip"));
    header.appendChild(h("span", ref.kind, "chip"));
    ID("inspector.score").textContent = typeof score === "number" ? score.toFixed(4) : "—";
    ID("inspector.content").textContent = rec.content === undefined || rec.content === null ? "" : String(rec.content);
    var doc = ID("inspector.document-id");
    doc.hidden = rec.document_id === undefined;
    doc.textContent = "document_id: " + rec.document_id;
    var ord = ID("inspector.ordinal");
    ord.hidden = rec.ordinal === undefined;
    ord.textContent = "ordinal: " + rec.ordinal;

    var body = ID("inspector.kv").tBodies[0];
    clearNode(body);
    Object.keys(rec).forEach(function (key) {
      if (["id", "content", "document_id", "ordinal"].indexOf(key) >= 0) return;
      var value = rec[key];
      var tr = h("tr");
      tr.appendChild(h("td", key, "mono"));
      tr.appendChild(h("td", value !== null && typeof value === "object" ? JSON.stringify(value) : String(value), "mono"));
      body.appendChild(tr);
    });
    root.querySelector('[data-role="kv-wrap"]').hidden = body.children.length === 0;
  }

  function fail(which, ns) {
    var op = ns === "trace" ? "resolve_trace" : "resolve_evidence";
    var field = ns === "trace" ? "trace_reference" : "ref";
    if (which === "validation") return showError(422, { detail: [{ loc: ["body", field], msg: "Field required", type: "missing" }] });
    if (which === "server-failure") {
      return showError(502, { refusal_type: "ForeignEngineRefusalError", message: "operation '" + op + "' failed (StoreFault)", operation: op, failure_class: "StoreFault", cause: "index checksum mismatch" });
    }
    return showError(500, "Internal Server Error");
  }

  function isOk(result) {
    return result.status >= 200 && result.status < 300 && result.body !== null && typeof result.body === "object";
  }

  // Aborts the evidence read in flight and gives its opener button back (IN-JSB-08). The abort sits beside the restore.
  function abortResolve() {
    if (resolveCtl) {
      resolveCtl.abort();
      resolveCtl = null;
      if (!ID("state.loading").hidden) evState("idle");
    }
    busy(false);
  }

  // One evidence lookup. The ref goes to the server exactly as it came (Pitfall 2). A cached record shows at once with no
  // request and no loading view; an error is never cached (D-07). `el` is the Open button to mark busy, or null.
  function resolve(ref, score, el) {
    abortResolve();
    showTab("evidence");
    hideErrors();
    var key = ref.namespace + "\u0001" + ref.ref;
    if (cache[key]) return showRecord(ref, cache[key], score);
    busyEl = el;
    busy(true);
    evState("loading");
    var mine = (resolveCtl = new AbortController());
    api("POST", "/evidence/resolve", ref, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== resolveCtl) return;
      resolveCtl = null;
      busy(false);
      if (!isOk(result)) return showError(result.status, result.body);
      cache[key] = result.body;
      showRecord(ref, result.body, score);
    });
  }

  function showRecord(ref, rec, score) {
    renderRecord(ref, rec, score);
    evState("resolved");
  }

  function submitLookup() {
    var input = ID("lookup.ref");
    var ref = input.value.trim();
    hideErrors();
    if (ref === "") return setFieldError(input, MSG.noRef);
    resolve({ ref: ref, namespace: ID("lookup.namespace").value, kind: ID("lookup.kind").value }, null, null);
  }


  // ---- trace tab ----

  function traceView(name) {
    root.querySelector('[data-role="trace-empty"]').hidden = name !== "empty";
    ID("state.trace-loading").hidden = name !== "loading";
    ID("trace.summary").hidden = name !== "loaded";
    syncDebug();
  }

  function syncLoad() {
    setDisabled(ID("trace.load"), ID("trace.reference").value.trim() === "");
  }

  function setField(name, text) {
    root.querySelector('[data-role="' + name + '"]').textContent = text;
  }

  function sentinel(el, value) {
    var isSentinel = typeof value === "string" && value.indexOf("sentinel:") === 0;
    el.textContent = isSentinel ? "not yet recorded" : String(value);
    el.title = value === null || value === undefined ? "" : String(value);
  }

  function renderTrace(name, token) {
    var rec = FIX.evidence[name];
    loaded = { name: name, token: token, rec: rec };
    ID("trace.reference").value = token;
    syncLoad();
    var status = ID("trace.status");
    status.setAttribute("data-state", rec.partial ? "warn" : "ok");
    status.textContent = rec.partial ? "▲ partial" : "✓ clean";
    setField("stop_reason", "stop_reason: " + (rec.stop_reason === null ? "—" : rec.stop_reason));
    setField("degradation_reason", "degradation_reason: " + (rec.degradation_reason === null ? "—" : rec.degradation_reason));
    ["executor_version", "concurrency_setting", "determinism_setting", "arm_execution_order"].forEach(function (key) {
      setField(key, String(rec[key]));
    });
    sentinel(ID("trace.bundle-ref"), rec.bundle_ref);
    sentinel(ID("trace.snapshot-hash"), rec.corpus_snapshot_hash);
    traceView("loaded");
  }

  function loadTrace() {
    var token = ID("trace.reference").value.trim();
    if (token === "") return;
    clearTimeout(timer);
    hideErrors();
    traceView("loading");
    timer = setTimeout(function () {
      var o = outcome();
      if (o === "validation" || o === "server-failure" || o === "generic") return fail(o, "trace");
      var name = TRACE_OF[token];
      if (o === "refusal" || o === "unknown-trace" || !name) {
        return showError(404, { refusal_type: "UnknownTraceReferenceError", message: "unknown trace reference", trace_reference: token });
      }
      renderTrace(name, token);
    }, LOAD_MS);
  }

  var NODE_CELLS = [
    function (n) { return n.node_id; },
    function (n) { return n.instance_hash; },
    function (n) { return n.depth; },
    function (n) { return n.effective_depth; },
    function () { return "—"; },
    function () { return "—"; },
    function (n) { return n.status; },
    function (n) { return n.execution_mode; },
    function (n) { return n.wall_clock_ms; },
    function (n) { return n.cache_hit; },
    function (n) { return n.guards_fired.length ? n.guards_fired.join(", ") : "—"; },
    function (n) { return n.budget_state; },
    function (n) { return n.spent; },
    function (n) { return n.allowance; },
    function (n) { return n.realised_budget_share; },
    function (n) { return n.cross_process_failure_cause; },
    function (n) { return n.resumable; },
    function (n) { return n.tokens.prompt_tokens; },
    function (n) { return n.tokens.completion_tokens; },
    function (n) { return n.tokens.cached_read_tokens; },
    function (n) { return n.tokens.call_count; },
    function (n) { return n.tokens.counted_by; },
  ];
  var PLACEHOLDER_COLS = [4, 5];
  var SUM_COLS = [8, 17, 18, 19, 20];

  function cellText(value) {
    return value === null || value === undefined ? "—" : String(value);
  }

  function fillDebug(view, rec) {
    ["run_id", "wiring_id", "wiring_instance_hash", "arm_id"].forEach(function (key) {
      view.querySelector('[data-role="' + key + '"]').textContent = rec[key];
    });
    Array.prototype.forEach.call(view.querySelectorAll("button[data-copy]"), function (button) {
      button.addEventListener("click", function () {
        copyText(rec[button.getAttribute("data-copy")], button.parentElement.querySelector('[data-role="copied"]'));
      });
    });

    var body = view.querySelector("tbody");
    var sums = view.querySelector("tfoot tr");
    var totals = {};
    rec.nodes.forEach(function (node) {
      var tr = h("tr");
      var state = node.status === "failed" ? "failed" : node.budget_state === "halted" ? "halted" : null;
      if (state) tr.setAttribute("data-row-state", state);
      NODE_CELLS.forEach(function (cell, i) {
        var td = h("td", null, i === 0 || i === 1 || i === 15 ? "mono" : "");
        td.appendChild(document.createTextNode(cellText(cell(node))));
        if (PLACEHOLDER_COLS.indexOf(i) >= 0) {
          td.appendChild(document.createTextNode(" "));
          var badge = h("span", "placeholder", "badge");
          badge.setAttribute("data-state", "neutral");
          td.appendChild(badge);
        }
        if (i === 6 && state) td.style.fontWeight = "600";
        tr.appendChild(td);
        if (SUM_COLS.indexOf(i) >= 0) totals[i] = (totals[i] || 0) + cell(node);
      });
      body.appendChild(tr);
    });
    NODE_CELLS.forEach(function (cell, i) {
      sums.appendChild(h("td", i === 0 ? "Sum" : SUM_COLS.indexOf(i) >= 0 ? String(totals[i] || 0) : ""));
    });

    var chart = view.querySelector(".bar-chart");
    var max = Math.max.apply(null, rec.nodes.map(function (n) { return n.wall_clock_ms; }).concat([1]));
    rec.nodes.forEach(function (node) {
      var row = h("div", null, "bar-row");
      row.appendChild(h("span", node.node_id, "mono"));
      var bar = h("span", null, "bar");
      bar.style.setProperty("--w", Math.round((node.wall_clock_ms / max) * 100) + "%");
      row.appendChild(bar);
      row.appendChild(h("span", node.wall_clock_ms + " ms"));
      chart.appendChild(row);
    });
  }

  // The Debug view exists only as a template: one clone after the summary while the toggle is on and the loaded trace has debug fields.
  function syncDebug() {
    if (debugView) {
      debugView.parentNode.removeChild(debugView);
      debugView = null;
    }
    var absent = root.querySelector('[data-role="debug-absent"]');
    absent.hidden = true;
    var summary = ID("trace.summary");
    if (!ID("trace.debug").checked || summary.hidden || !loaded) return;
    if (!loaded.rec.nodes) {
      absent.hidden = false;
      return;
    }
    var clone = root.querySelector('template[data-role="debug-template"]').content.cloneNode(true);
    debugView = clone.firstElementChild;
    fillDebug(debugView, loaded.rec);
    summary.parentNode.insertBefore(debugView, summary.nextSibling);
  }

  function openTrace(token) {
    clearTimeout(timer);
    showTab("trace");
    hideErrors();
    ID("trace.reference").value = token;
    syncLoad();
    traceView(loaded && loaded.token === token ? "loaded" : "empty");
  }

  ID("tabs.evidence").addEventListener("click", function () {
    showTab("evidence");
    hideErrors();
    if (ID("state.loading").hidden && ID("state.resolved").hidden && ID("state.refusal").hidden) evState("idle");
  });
  ID("tabs.trace").addEventListener("click", function () {
    showTab("trace");
    hideErrors();
    traceView(loaded && loaded.token === ID("trace.reference").value.trim() ? "loaded" : "empty");
  });
  ID("lookup.submit").addEventListener("click", submitLookup);
  ID("lookup.ref").addEventListener("input", function () {
    if (this.value.trim() !== "") setFieldError(this, "");
  });
  ID("trace.reference").addEventListener("input", function () {
    syncLoad();
    setFieldError(this, this.value.trim() === "" ? MSG.noTrace : "");
  });
  ID("trace.reference").addEventListener("keydown", function (event) {
    if (event.key === "Enter") loadTrace();
  });
  ID("trace.load").addEventListener("click", loadTrace);
  ID("trace.debug").addEventListener("change", syncDebug);
  ID("trace.recent").addEventListener("change", function (event) {
    if (!event.target.value) return;
    ID("trace.reference").value = event.target.value;
    setFieldError(ID("trace.reference"), "");
    syncLoad();
  });
  FIX.query.history.forEach(function (entry) {
    var option = h("option", entry.time + " " + entry.selector + " " + entry.trace_token.slice(0, 8));
    option.value = entry.trace_token;
    ID("trace.recent").appendChild(option);
  });
  ID("trace.use-in-ledger").addEventListener("click", function () {
    Console.show("ledger");
    Console.emit("promote", { trace: ID("trace.reference").value.trim() });
  });
  ID("inspector.document-link").addEventListener("click", function (event) {
    event.preventDefault();
    Console.show("corpus");
  });
  // Open trace delegates to the Open trace link of the result the evidence came from, so the token is the one that result holds.
  ID("inspector.trace-link").addEventListener("click", function (event) {
    event.preventDefault();
    var link = originLink || $id("query.result.trace-link");
    if (link) link.click();
  });
  wireErrors("evidence");

  // Capture phase: runs before the Open button's own handler, so the opener is known when open-evidence arrives.
  document.addEventListener(
    "click",
    function (event) {
      var button = event.target.closest && event.target.closest("button");
      var id = button && button.getAttribute("data-mock-id");
      if (id && /^(query\.evidence|query\.col\d|graph\.chunks)\.open-\d+$/.test(id)) opener = button;
    },
    true
  );
  // After the button's own handler has run, a click that emitted nothing must not leave its button as the next opener.
  document.addEventListener("click", function () {
    opener = null;
  });
  // payload: {ref: <EvidenceRef unchanged>, score, trace_token} from Query, Compare and the chunk browser.
  Console.on("open-evidence", function (payload) {
    var el = opener;
    opener = null;
    originLink = null; // replaced by the origin token in the next task
    resolve(payload.ref, payload.score, el);
  });
  Console.on("open-trace", function (payload) {
    openTrace(payload.token || "");
  });

  evState("idle");
  traceView("empty");
  return {};
})();
Console.register("evidence", EvidenceScreen);
