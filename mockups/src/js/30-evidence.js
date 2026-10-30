var EvidenceScreen = (function () {
  var STATES = ["idle", "loading", "resolved", "refusal"];
  var NS_OF = { "e-lightrag-chunk": "chunks", "e-hipporag-chunk": "hipporag-chunks" };
  var KIND = "text_chunk";
  var LOAD_MS = 300;
  var MSG = { noRef: "Enter an evidence ref.", noTrace: "Enter a trace reference." };
  var root = $id("screen-evidence");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var panes = { evidence: root.querySelector('[data-role="pane-evidence"]'), trace: root.querySelector('[data-role="pane-trace"]') };
  var cache = {};
  var tab = "evidence";
  var timer = null;
  var opener = null;
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

  // Records come from the fixtures; any other well-formed chunk ref of the two namespaces gets a generic record so Open works from every screen.
  function find(ns, ref) {
    if (ns === "chunks") {
      if (ref === FIX.evidence["e-lightrag-chunk"].id) return FIX.evidence["e-lightrag-chunk"];
      if (FIX.evidence.chunks[ref]) return FIX.evidence.chunks[ref];
      if (/^c-[0-9a-f]{6}$/.test(ref)) return { id: ref, full_doc_id: FIX.evidence["e-lightrag-chunk"].full_doc_id, content: "Fixture text for chunk " + ref + ".", file_path: FIX.evidence["e-lightrag-chunk"].file_path };
    }
    if (ns === "hipporag-chunks") {
      if (ref === FIX.evidence["e-hipporag-chunk"].id) return FIX.evidence["e-hipporag-chunk"];
      if (/^chunk:[0-9a-f]{6,}$/.test(ref)) return { id: ref, document_id: FIX.evidence["e-hipporag-chunk"].document_id, ordinal: 0, content: "Fixture text for chunk " + ref + "." };
    }
    return null;
  }

  function renderRecord(ns, rec, score) {
    var header = ID("inspector.header");
    clearNode(header);
    header.appendChild(h("span", rec.id, "mono"));
    header.appendChild(h("span", ns, "chip"));
    header.appendChild(h("span", KIND, "chip"));
    ID("inspector.score").textContent = typeof score === "number" ? score.toFixed(4) : "—";
    ID("inspector.content").textContent = rec.content === undefined ? "" : String(rec.content);
    var doc = ID("inspector.document-id");
    doc.hidden = rec.document_id === undefined;
    doc.textContent = "document_id: " + rec.document_id;
    var ord = ID("inspector.ordinal");
    ord.hidden = rec.ordinal === undefined;
    ord.textContent = "ordinal: " + rec.ordinal;
    ID("inspector.document-link").hidden = rec.document_id === undefined;

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

  function finishResolve(ns, ref, score) {
    busy(false);
    var o = outcome();
    var key = ns + "\u0001" + ref;
    if (o === "refusal") return evState("refusal");
    if (o === "validation" || o === "server-failure" || o === "generic") return fail(o, "evidence");
    var rec = cache[key] || find(ns, ref);
    if (!rec) return evState("refusal");
    cache[key] = rec;
    renderRecord(ns, rec, score);
    evState("resolved");
  }

  // One evidence lookup: loading for about 300 ms, then the record, a refusal or the mock outcome. A cached record resolves at once.
  function resolve(ns, ref, score) {
    clearTimeout(timer);
    showTab("evidence");
    hideErrors();
    if (cache[ns + "\u0001" + ref] && outcome() === "success") return finishResolve(ns, ref, score);
    evState("loading");
    busy(true);
    timer = setTimeout(function () {
      finishResolve(ns, ref, score);
    }, LOAD_MS);
  }

  function submitLookup() {
    var input = ID("lookup.ref");
    var ref = input.value.trim();
    hideErrors();
    if (ref === "") return setFieldError(input, MSG.noRef);
    busyEl = null;
    resolve(ID("lookup.namespace").value, ref, null);
  }

  function batch() {
    ["c-7f3a91", "c-02be44", "c-91d0c7"].forEach(function (ref) {
      cache["chunks\u0001" + ref] = find("chunks", ref);
    });
    ID("batch.status").textContent = "Resolved 3 of 3 (fixture)";
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

  // ---- hooks ----

  function setState(name) {
    clearTimeout(timer);
    busy(false);
    if (name === "trace-loading") {
      showTab("trace");
      hideErrors();
      return traceView("loading");
    }
    if (STATES.indexOf(name) < 0) throw new Error("unknown evidence state " + name);
    showTab("evidence");
    hideErrors();
    if (name === "resolved" && !cache["chunks\u0001c-7f3a91"]) loadFixture("e-lightrag-chunk");
    else evState(name);
  }

  function loadFixture(name) {
    clearTimeout(timer);
    busy(false);
    if (NS_OF[name]) {
      showTab("evidence");
      hideErrors();
      var rec = FIX.evidence[name];
      cache[NS_OF[name] + "\u0001" + rec.id] = rec;
      renderRecord(NS_OF[name], rec, null);
      return evState("resolved");
    }
    if (name !== "t-clean" && name !== "t-partial-debug") throw new Error("unknown evidence fixture " + name);
    showTab("trace");
    hideErrors();
    renderTrace(name, DEFAULT_TOKEN[name]);
  }

  function inject(response) {
    clearTimeout(timer);
    busy(false);
    showError(response.status, response.body);
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
  ID("batch.submit").addEventListener("click", batch);
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
  Console.on("open-evidence", function (payload) {
    busyEl = opener;
    var origin = opener && opener.closest('[data-mock-id="query.result.panel"], .cmp-col');
    originLink = origin ? origin.querySelector('[data-mock-id$=".trace-link"]') : null;
    opener = null;
    resolve(payload.ref.namespace, payload.ref.id, payload.score);
  });
  Console.on("open-trace", function (payload) {
    openTrace(payload.token || "");
  });

  evState("idle");
  traceView("empty");
  return { setState: setState, inject: inject, loadFixture: loadFixture };
})();
Console.register("evidence", EvidenceScreen);
