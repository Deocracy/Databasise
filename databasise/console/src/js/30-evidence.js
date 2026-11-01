WIRED["evidence GET /traces"] = true;
WIRED["evidence GET /log"] = true;

var EvidenceScreen = (function () {
  var STATES = ["idle", "loading", "resolved", "refusal"];
  var HISTORY_KEY = "databasise.console.history";
  var MSG = { noRef: "Enter an evidence ref.", noTrace: "Enter a trace reference." };
  var root = $id("screen-evidence");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var panes = { evidence: root.querySelector('[data-role="pane-evidence"]'), trace: root.querySelector('[data-role="pane-trace"]') };
  // Resolved records, kept by namespace and ref until a write changes the corpus (D-07, R18-09). Errors are never stored.
  var cache = Object.create(null);
  var tab = "evidence";
  var opener = null; // the Open button whose click is being dispatched
  var busyEl = null; // the Open button marked busy by the read in flight
  var resolveCtl = null;
  var traceCtl = null;
  var origin = null; // trace token of the run the shown record came from (WR-JSB-01)
  var shownDoc = null; // full_doc_id of the shown record, when it has one (IN-JSB-07)
  var loaded = null; // {token, rec, debug} of the trace on screen
  var debugView = null;
  var recentSeq = 0;

  function ID(name) {
    return $id("evidence." + name);
  }

  function isOk(result) {
    return result.status >= 200 && result.status < 300 && result.body !== null && typeof result.body === "object";
  }

  function cellText(value) {
    return value === null || value === undefined ? "—" : String(value);
  }

  // ---- evidence tab ----

  function evState(name) {
    STATES.forEach(function (s) {
      $id("evidence.state." + s).hidden = s !== name;
    });
  }

  // Leaving a pane abandons the read that belongs to it.
  function showTab(name) {
    tab = name;
    if (name !== "evidence") abortResolve();
    if (name !== "trace") abortTrace();
    ["evidence", "trace"].forEach(function (n) {
      panes[n].hidden = n !== name;
      ID("tabs." + n).setAttribute("aria-selected", String(n === name));
    });
  }

  function hideErrors() {
    renderError("evidence", 200, null);
    errorsBox.hidden = true;
  }

  // Every non-2xx goes through renderError (LIVE-03). An unresolvable ref also shows its state view (UI-SPEC).
  function showError(status, body) {
    var shape = renderError("evidence", status, body);
    errorsBox.hidden = shape === "result";
    if (shape === "result") return;
    if (tab === "evidence") evState(body && body.refusal_type === "UnresolvableEvidenceReferenceError" ? "refusal" : null);
    else traceView("none");
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

  // Aborts the evidence read in flight and gives its opener button back (IN-JSB-08). The abort sits beside the restore.
  function abortResolve() {
    if (resolveCtl) {
      resolveCtl.abort();
      resolveCtl = null;
      if (!ID("state.loading").hidden) evState("idle");
    }
    busy(false);
  }

  function syncOrigin() {
    var link = ID("inspector.trace-link");
    if (origin) {
      link.setAttribute("href", "#evidence");
      link.removeAttribute("aria-disabled");
      link.removeAttribute("tabindex");
    } else {
      link.removeAttribute("href");
      link.setAttribute("aria-disabled", "true");
      link.setAttribute("tabindex", "-1");
    }
    // The reason is written only while it applies, so the page never holds the text twice before a record is shown.
    var note = root.querySelector('[data-role="no-origin-trace"]');
    note.textContent = origin ? "" : "No trace token on this result.";
    note.hidden = !!origin;
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
    // Corpus lists v1 documents only: a HippoRAG document_id has no row there (IN-JSB-07).
    shownDoc = typeof rec.full_doc_id === "string" && rec.full_doc_id !== "" ? rec.full_doc_id : null;
    ID("inspector.document-link").hidden = shownDoc === null;

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

  function showRecord(ref, rec, score, token) {
    origin = token || null;
    renderRecord(ref, rec, score);
    syncOrigin();
    evState("resolved");
  }

  // One evidence lookup. The ref goes to the server exactly as it came (Pitfall 2). A cached record shows at once with no
  // request and no loading view; an error is never cached (D-07). `el` is the Open button to mark busy, or null.
  function resolve(ref, score, token, el) {
    abortResolve();
    showTab("evidence");
    hideErrors();
    var key = ref.namespace + "\u0001" + ref.ref;
    if (cache[key]) return showRecord(ref, cache[key], score, token);
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
      showRecord(ref, result.body, score, token);
    });
  }

  function submitLookup() {
    var input = ID("lookup.ref");
    var ref = input.value.trim();
    hideErrors();
    if (ref === "") return setFieldError(input, MSG.noRef);
    resolve({ ref: ref, namespace: ID("lookup.namespace").value, kind: ID("lookup.kind").value }, null, null, null);
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
    el.textContent = isSentinel ? "not yet recorded" : cellText(value);
    el.title = value === null || value === undefined ? "" : String(value);
  }

  function renderTrace(token, rec, debug) {
    loaded = { token: token, rec: rec, debug: debug };
    ID("trace.reference").value = token;
    syncLoad();
    var status = ID("trace.status");
    status.setAttribute("data-state", rec.partial ? "warn" : "ok");
    status.textContent = rec.partial ? "▲ partial" : "✓ clean";
    setField("stop_reason", "stop_reason: " + cellText(rec.stop_reason));
    setField("degradation_reason", "degradation_reason: " + cellText(rec.degradation_reason));
    ["executor_version", "concurrency_setting", "determinism_setting", "arm_execution_order"].forEach(function (key) {
      setField(key, cellText(rec[key]));
    });
    sentinel(ID("trace.bundle-ref"), rec.bundle_ref);
    sentinel(ID("trace.snapshot-hash"), rec.corpus_snapshot_hash);
    traceView("loaded");
  }

  // Aborts the trace read in flight. A view that was waiting for it goes back to empty.
  function abortTrace() {
    if (!traceCtl) return;
    traceCtl.abort();
    traceCtl = null;
    if (!ID("state.trace-loading").hidden) {
      loaded = null;
      traceView("empty");
    }
  }

  // token is optional: the Load button and Enter read the reference field. The Debug flag is read now, so every toggle re-requests.
  function loadTrace(tokenArg) {
    var token = typeof tokenArg === "string" ? tokenArg : ID("trace.reference").value.trim();
    if (token === "") return;
    abortTrace();
    hideErrors();
    var debug = ID("trace.debug").checked;
    var mine = (traceCtl = new AbortController());
    traceView("loading");
    api("POST", "/trace/resolve", { trace_reference: token, debug: debug }, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== traceCtl) return;
      traceCtl = null;
      if (isOk(result)) return renderTrace(token, result.body, debug);
      loaded = null;
      showError(result.status, result.body);
    });
  }

  function tokenCell(key) {
    return function (n) {
      return n.tokens ? n.tokens[key] : null;
    };
  }

  var NODE_CELLS = [
    function (n) { return n.node_id; },
    function (n) { return n.instance_hash; },
    function (n) { return n.depth; },
    function (n) { return n.effective_depth; },
    function (n) { return n.tier; },
    function (n) { return n.feed_tier; },
    function (n) { return n.status; },
    function (n) { return n.execution_mode; },
    function (n) { return n.wall_clock_ms; },
    function (n) { return n.cache_hit; },
    function (n) { return Array.isArray(n.guards_fired) && n.guards_fired.length ? n.guards_fired.join(", ") : null; },
    function (n) { return n.budget_state; },
    function (n) { return n.spent; },
    function (n) { return n.allowance; },
    function (n) { return n.realised_budget_share; },
    function (n) { return n.cross_process_failure_cause; },
    function (n) { return n.resumable; },
    tokenCell("prompt_tokens"),
    tokenCell("completion_tokens"),
    tokenCell("cached_read_tokens"),
    tokenCell("call_count"),
    tokenCell("counted_by"),
  ];
  var SUM_COLS = [8, 17, 18, 19, 20];

  function fillDebug(view, rec) {
    ["run_id", "wiring_id", "wiring_instance_hash", "arm_id"].forEach(function (key) {
      view.querySelector('[data-role="' + key + '"]').textContent = cellText(rec[key]);
    });
    Array.prototype.forEach.call(view.querySelectorAll("button[data-copy]"), function (button) {
      button.addEventListener("click", function () {
        copyText(String(rec[button.getAttribute("data-copy")]), button.parentElement.querySelector('[data-role="copied"]'));
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
        var td = h("td", cellText(cell(node)), i === 0 || i === 1 || i === 15 ? "mono" : "");
        if (i === 6 && state) td.style.fontWeight = "600";
        tr.appendChild(td);
        if (SUM_COLS.indexOf(i) >= 0) totals[i] = (totals[i] || 0) + (Number(cell(node)) || 0);
      });
      body.appendChild(tr);
    });
    NODE_CELLS.forEach(function (cell, i) {
      sums.appendChild(h("td", i === 0 ? "Sum" : SUM_COLS.indexOf(i) >= 0 ? String(totals[i] || 0) : ""));
    });

    var chart = view.querySelector(".bar-chart");
    var max = Math.max.apply(null, rec.nodes.map(function (n) { return Number(n.wall_clock_ms) || 0; }).concat([1]));
    rec.nodes.forEach(function (node) {
      var row = h("div", null, "bar-row");
      row.appendChild(h("span", node.node_id, "mono"));
      var bar = h("span", null, "bar");
      bar.style.setProperty("--w", Math.round(((Number(node.wall_clock_ms) || 0) / max) * 100) + "%");
      row.appendChild(bar);
      row.appendChild(h("span", cellText(node.wall_clock_ms) + " ms"));
      chart.appendChild(row);
    });
  }

  // The Debug view exists only as a template: one clone after the summary while the toggle is on and the loaded trace was read
  // with debug. Switching Debug off removes the clone before anything else happens.
  function syncDebug() {
    if (debugView) {
      debugView.parentNode.removeChild(debugView);
      debugView = null;
    }
    var absent = root.querySelector('[data-role="debug-absent"]');
    absent.hidden = true;
    var summary = ID("trace.summary");
    if (!ID("trace.debug").checked || summary.hidden || !loaded) return;
    if (!loaded.debug || !Array.isArray(loaded.rec.nodes)) {
      absent.hidden = false;
      return;
    }
    var clone = root.querySelector('template[data-role="debug-template"]').content.cloneNode(true);
    debugView = clone.firstElementChild;
    fillDebug(debugView, loaded.rec);
    summary.parentNode.insertBefore(debugView, summary.nextSibling);
  }

  function openTrace(token) {
    showTab("trace");
    hideErrors();
    ID("trace.reference").value = token;
    syncLoad();
    if (token === "") return traceView(loaded ? "loaded" : "empty");
    loadTrace(token);
  }

  // The picker lists this browser's run history, then (with GET /traces in the spec) the server's traces not already listed.
  function addRecent(select, token, time, label) {
    if (typeof token !== "string" || token === "") return;
    var listed = Array.prototype.some.call(select.options, function (option) {
      return option.value === token;
    });
    if (listed) return;
    var option = h("option", String(time).slice(0, 19).replace("T", " ") + " " + label + " " + token.slice(0, 8));
    option.value = token;
    select.appendChild(option);
  }

  // shortcut: a fresh SessionLog per call reads storage again; a blocked sessionStorage lists no history here, upgrade if that matters.
  function refreshRecent() {
    var select = ID("trace.recent");
    var seq = ++recentSeq;
    while (select.options.length > 1) select.remove(1);
    SessionLog(HISTORY_KEY, 50)
      .all()
      .forEach(function (entry) {
        addRecent(select, entry.trace_token, entry.timestamp, selectorLabel(entry.selector));
      });
    if (!Live.has("GET", "/traces")) return;
    api("GET", "/traces?limit=50&offset=0").then(function (result) {
      if (seq !== recentSeq || !isOk(result) || !Array.isArray(result.body.items)) return;
      result.body.items.forEach(function (item) {
        addRecent(select, item.trace_reference, item.created_at, "server");
      });
    });
  }

  // ---- wiring ----

  ID("tabs.evidence").addEventListener("click", function () {
    showTab("evidence");
    hideErrors();
    if (ID("state.loading").hidden && ID("state.resolved").hidden && ID("state.refusal").hidden) evState("idle");
  });
  ID("tabs.trace").addEventListener("click", function () {
    showTab("trace");
    hideErrors();
    traceView(traceCtl ? "loading" : loaded && loaded.token === ID("trace.reference").value.trim() ? "loaded" : "empty");
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
  ID("trace.load").addEventListener("click", function () {
    loadTrace();
  });
  ID("trace.debug").addEventListener("change", function () {
    var token = loaded ? loaded.token : traceCtl ? ID("trace.reference").value.trim() : "";
    if (token) loadTrace(token);
    else syncDebug();
  });
  ID("trace.recent").addEventListener("change", function (event) {
    if (!event.target.value) return;
    ID("trace.reference").value = event.target.value;
    setFieldError(ID("trace.reference"), "");
    syncLoad();
  });
  ID("trace.use-in-ledger").addEventListener("click", function () {
    Console.show("ledger");
    Console.emit("promote", { trace: ID("trace.reference").value.trim() });
  });
  ID("inspector.document-link").addEventListener("click", function (event) {
    event.preventDefault();
    if (shownDoc === null) return;
    Console.show("corpus");
    Console.emit("focus-document", shownDoc);
  });
  // Open trace loads the trace of the run the shown record came from, captured when the row was opened (WR-JSB-01).
  ID("inspector.trace-link").addEventListener("click", function (event) {
    event.preventDefault();
    if (origin) openTrace(origin);
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
    resolve(payload.ref, payload.score, payload.trace_token, el);
  });
  Console.on("open-trace", function (payload) {
    openTrace(payload.token || "");
  });
  // After a delete a cached record may be gone from the store: the next Open asks the server again (R18-09).
  Console.on("corpus-changed", function () {
    cache = Object.create(null);
  });
  // Entering the screen refreshes the picker; leaving it abandons both reads and restores the Open button (IN-JSB-08).
  Console.on("show", function (name) {
    if (name === "evidence") return refreshRecent();
    abortResolve();
    abortTrace();
  });

  evState("idle");
  traceView("empty");
  return {};
})();
Console.register("evidence", EvidenceScreen);
