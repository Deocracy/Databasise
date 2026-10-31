var CorpusScreen = (function () {
  var STORE_KEYS = [
    "kv:text_chunks", "graph:chunk_entity_relation", "vector:chunks", "vector:entities", "vector:relationships",
    "kv:hipporag-text-chunks", "graph:hipporag-graph", "vector:hipporag-chunks", "vector:hipporag-entities", "vector:hipporag-facts",
  ];
  var STORE_STATE = { ok: "ok", absent: "neutral", corrupted: "fail", busy: "warn", "not probed": "neutral" };
  var STORE_NOTE = {
    ok: "Opened read-only and readable.",
    absent: "Nothing on disk yet; the store is created on the first write.",
    corrupted: "Unreadable or half-written; the files fail their checks.",
    busy: "Held by another OS process, or a locked file.",
    "not probed": "The server did not report this key.",
  };
  var STATUSES = ["pending", "parsing", "analyzing", "processing", "preprocessed", "interrupted", "processed", "failed"];
  var STATUS_STATE = { processed: "ok", failed: "fail", processing: "progress", parsing: "progress", analyzing: "progress", pending: "neutral", preprocessed: "neutral", interrupted: "warn" };
  var GLYPH = { ok: "✓", fail: "✕", progress: "●", neutral: "■", warn: "▲" };
  var HIDE_AT_ZERO = { preprocessed: true, interrupted: true };
  var CLIENTS = ["llm", "embedding", "rerank"];
  var MSG = {
    pageSize: "Page size must be between 1 and 100.",
    limit: "Line limit must be between 1 and 1000.",
  };
  var HEALTH_MS = 800;
  var RETRY_MS = 300;

  var root = $id("screen-corpus");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var checkHealth = ID("error.check-health");
  var tiles = {};
  ["total"].concat(STATUSES).forEach(function (s) {
    tiles[s] = ID("kpi." + s);
  });
  var tbody = ID("table.documents").tBodies[0];
  var wrap = root.querySelector('[data-role="table-wrap"]');
  var pager = root.querySelector('[data-role="pager"]');
  var page = null; // {offset, limit, body}: the offset is the one this client asked for, because the routes do not echo it
  var counts = null; // the GET /corpus/counts body
  var statusFilter = "all";
  var isLoading = false;
  var loadedOnce = false;
  var pageCtl = null;
  var countsCtl = null;
  var healthTimer = null;
  var healthPoll = null;
  var tablePoll = null;
  var healthErrorShown = false;

  function ID(name) {
    return $id("corpus." + name);
  }

  function paintBadge(el, state, text) {
    el.setAttribute("data-state", state);
    el.textContent = GLYPH[state] + " " + text;
  }

  function chip(text, state) {
    var node = h("span", text, "chip");
    node.setAttribute("data-state", state);
    return node;
  }

  function ok(result) {
    return result.status >= 200 && result.status < 300;
  }

  // ---- errors ----

  function showError(status, body) {
    var shape = renderError("corpus", status, body);
    errorsBox.hidden = shape === "result";
    checkHealth.hidden = shape !== "generic";
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
    return shape;
  }

  // renderError clears every field message, so the client-side checks are rerun afterwards.
  function hideErrors() {
    renderError("corpus", 200, null);
    errorsBox.hidden = true;
    checkHealth.hidden = true;
    healthErrorShown = false;
    checkSize();
    checkLimit();
  }

  // The mock outcome select decides which server response the next retry gets (18-07 Task 3 replaces it).
  function failure(op, documentId) {
    var o = ID("mock.outcome").value;
    var retry = op === "retry";
    if (o === "refusal") {
      if (retry) return [404, { refusal_type: "UnknownDocumentError", message: "no document with this id in the v1 corpus", document_id: documentId }];
      return [422, { refusal_type: "PageSizeExceededError", message: "page size above the limit", requested: 500, limit: 100 }];
    }
    if (o === "validation") {
      var loc = retry ? ["path", "document_id"] : ["query", "limit"];
      return [422, { detail: [{ loc: loc, msg: retry ? "Field required" : "Input should be greater than or equal to 1", type: "value_error" }] }];
    }
    if (o === "server-failure") {
      return [502, { refusal_type: "ForeignEngineRefusalError", message: "operation '" + op + "' failed (CorpusOpSubprocessError)", operation: op, failure_class: "CorpusOpSubprocessError", cause: "the v1 driver exited with status 1" }];
    }
    if (o === "generic") return [500, "Internal Server Error"];
    return null;
  }

  // ---- health ----

  function fillStores(stores) {
    var body = ID("health.stores").tBodies[0];
    clearNode(body);
    // shortcut: a key outside the ten documented ones is appended after them, with its badge taken from the value.
    var keys = STORE_KEYS.slice();
    Object.keys(stores).forEach(function (key) {
      if (keys.indexOf(key) < 0) keys.push(key);
    });
    keys.forEach(function (key) {
      var value = key in stores ? stores[key] : "not probed";
      var state = STORE_STATE[value] || "neutral";
      var row = h("tr");
      row.appendChild(h("td", key, "mono"));
      var cell = h("td");
      var badge = h("span", null, "badge");
      paintBadge(badge, state, value);
      cell.appendChild(badge);
      row.appendChild(cell);
      row.appendChild(h("td", STORE_NOTE[value] || "Reported state: " + value));
      body.appendChild(row);
    });
  }

  function fillEngineRow(name, value) {
    paintBadge(ID("health." + name).querySelector('[data-role="value"]'), value ? "ok" : "fail", value ? "yes" : "no");
  }

  function fillBusy() {
    var info = FIX.shell.info;
    var box = ID("health.busy");
    clearNode(box);
    box.appendChild(chip("write in flight: " + (info.write_in_flight ? "yes" : "no"), info.write_in_flight ? "warn" : "neutral"));
    box.appendChild(chip("graph in use: " + (info.graph_busy ? "yes" : "no"), info.graph_busy ? "warn" : "neutral"));
  }

  function paintHealth() {
    var report = Console.health();
    var state = healthState(report);
    var overall = ID("health.overall");
    var badge = root.querySelector('[data-role="state-badge"]');
    overall.setAttribute("data-state", state);
    badge.setAttribute("data-state", state);
    badge.querySelector('[data-role="glyph"]').textContent = HEALTH_GLYPHS[state];
    ID("health.state").textContent = HEALTH_WORDS[state];
    ID("health.loading").hidden = state !== "loading";
    root.querySelector('[data-role="health-body"]').hidden = state === "loading" || state === "error";
    if (state === "error") {
      showError(report.status, report.body);
      healthErrorShown = true;
      return;
    }
    if (healthErrorShown) hideErrors();
    if (state === "loading") return;
    fillStores(report.stores);
    fillEngineRow("engine", report.engine.v1_reachable);
    fillEngineRow("interpreter", report.engine.interpreter_present);
    var chips = ID("health.clients").querySelector('[data-role="chips"]');
    clearNode(chips);
    CLIENTS.forEach(function (name) {
      var present = report.clients[name];
      chips.appendChild(chip(GLYPH[present ? "ok" : "warn"] + " " + name + " " + (present ? "present" : "missing"), present ? "ok" : "warn"));
    });
    ID("health.reasons").querySelector('[data-role="text"]').textContent = report.engine_reason || "none reported";
    fillBusy();
  }

  function refreshHealth() {
    clearTimeout(healthTimer);
    ID("health.overall").setAttribute("data-state", "loading");
    ID("health.loading").hidden = false;
    root.querySelector('[data-role="health-body"]').hidden = true;
    ID("health.refresh").setAttribute("aria-busy", "true");
    healthTimer = setTimeout(function () {
      ID("health.refresh").removeAttribute("aria-busy");
      paintHealth();
    }, HEALTH_MS);
  }

  function setHealthPoll() {
    clearInterval(healthPoll);
    healthPoll = null;
    if (ID("health.poll").checked) healthPoll = setInterval(refreshHealth, Number(ID("health.poll-interval").value) * 1000);
  }

  // ---- corpus table ----

  // Returns the page size, or null after showing the message.
  function checkSize() {
    var input = ID("table.page-size");
    var raw = input.value.trim();
    var n = Number(raw);
    var valid = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100;
    setFieldError(input, valid ? "" : MSG.pageSize);
    return valid ? n : null;
  }

  function visibleRows() {
    return page.body.documents.filter(function (d) {
      return statusFilter === "all" || d.status === statusFilter;
    });
  }

  function control(row, prefix) {
    return row.querySelector('[data-mock-id^="corpus.table.' + prefix + '-"]');
  }

  function fillRows(list) {
    ensureRows(tbody, list.length).forEach(function (row, i) {
      var doc = list[i];
      var toggle = control(row, "error-toggle");
      var reason = row.querySelector('[data-role="error"]');
      var retry = control(row, "retry");
      row.setAttribute("data-status", doc.status);
      row.removeAttribute("aria-current");
      row.removeAttribute("tabindex");
      row.querySelector('[data-role="retry-msg"]').hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Show error";
      reason.hidden = true;
      setDisabled(retry, false);
      row.querySelector('[data-role="id"]').textContent = doc.document_id;
      paintBadge(row.querySelector('[data-role="status"]'), STATUS_STATE[doc.status] || "neutral", doc.status);
      row.querySelector('[data-role="updated"]').textContent = doc.updated_at;
      reason.textContent = doc.error_message || "";
      toggle.hidden = doc.status !== "failed" || !doc.error_message;
      retry.hidden = doc.status !== "interrupted";
      control(row, "delete").setAttribute("aria-label", "Delete " + doc.document_id);
      retry.setAttribute("aria-label", "Retry " + doc.document_id);
    });
  }

  function fillCounts() {
    var box = ID("table.counts");
    clearNode(box);
    if (!counts) return;
    box.appendChild(chip("Total " + counts.total, "neutral"));
    // An unknown status key still gets a chip; the chips wrap with no cap.
    Object.keys(counts.by_status).forEach(function (key) {
      box.appendChild(chip(key + " " + counts.by_status[key], STATUS_STATE[key] || "neutral"));
    });
  }

  function paintTiles() {
    var by = counts ? counts.by_status : {};
    tiles.total.querySelector('[data-role="count"]').textContent = counts ? String(counts.total) : "—";
    STATUSES.forEach(function (s) {
      var n = by[s] || 0;
      tiles[s].querySelector('[data-role="count"]').textContent = counts ? String(n) : "—";
      tiles[s].hidden = !!HIDE_AT_ZERO[s] && n === 0;
      tiles[s].setAttribute("aria-pressed", String(statusFilter === s));
    });
    fillCounts();
  }

  // The previous rows stay on screen while a read is in flight; the panel is aria-busy and the controls wait.
  function paintBusy() {
    var panel = ID("table.panel");
    if (isLoading) panel.setAttribute("aria-busy", "true");
    else panel.removeAttribute("aria-busy");
    panel.querySelector('[data-role="loading"]').hidden = !isLoading;
    setDisabled(ID("table.refresh"), isLoading);
    ID("state.loading").hidden = !(isLoading && !page);
    var next = page && page.body.next_offset !== null && page.body.next_offset !== undefined;
    setDisabled(ID("table.prev"), isLoading || !page || page.offset <= 0);
    setDisabled(ID("table.next"), isLoading || !next);
  }

  // Rows, pager and filter chip. Counts alone repaint through paintTiles, so an open error text or a retry note survives them.
  function paintPage() {
    paintTiles();
    paintBusy();
    if (!page) {
      ID("state.empty").hidden = true;
      root.querySelector('[data-role="no-match"]').hidden = true;
      wrap.hidden = true;
      pager.hidden = true;
      return;
    }
    var body = page.body;
    var empty = body.total === 0;
    var list = visibleRows();
    fillRows(list);
    ID("table.clear-filter").hidden = statusFilter === "all";
    var filterChip = root.querySelector('[data-role="filter-chip"]');
    filterChip.hidden = statusFilter === "all";
    filterChip.textContent = "Filtered: " + statusFilter;
    ID("state.empty").hidden = !empty;
    root.querySelector('[data-role="no-match"]').hidden = empty || list.length > 0;
    wrap.hidden = empty || list.length === 0;
    pager.hidden = empty;
    pager.querySelector('[data-role="range"]').textContent = body.documents.length ? "Showing " + (page.offset + 1) + " to " + (page.offset + body.documents.length) + " of " + body.total : "";
  }

  function setFilter(status) {
    statusFilter = status;
    paintPage();
  }

  // GET /corpus at an offset the client chooses. A newer read replaces an older one; a failed read keeps the previous rows.
  function loadPage(offset) {
    var size = checkSize();
    if (size === null) return Promise.resolve();
    if (pageCtl) pageCtl.abort();
    var mine = (pageCtl = new AbortController());
    hideErrors();
    isLoading = true;
    paintBusy();
    return api("GET", "/corpus?limit=" + size + "&offset=" + offset, null, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== pageCtl) return;
      pageCtl = null;
      isLoading = false;
      // shortcut: a 2xx body without a documents list is ignored; upgrade when the route can answer one.
      if (ok(result) && result.body && Array.isArray(result.body.documents)) page = { offset: offset, limit: size, body: result.body };
      else if (!ok(result)) showError(result.status, result.body);
      paintPage();
    });
  }

  function loadCounts() {
    if (countsCtl) countsCtl.abort();
    var mine = (countsCtl = new AbortController());
    return api("GET", "/corpus/counts", null, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== countsCtl) return;
      countsCtl = null;
      if (ok(result) && result.body && typeof result.body.by_status === "object") {
        counts = result.body;
        paintTiles();
      } else if (!ok(result)) showError(result.status, result.body);
    });
  }

  function refreshAll() {
    loadedOnce = true;
    loadPage(0);
    loadCounts();
  }

  function retryDocument(n) {
    var row = tbody.rows[n - 1];
    var button = ID("table.retry-" + n);
    var message = row.querySelector('[data-role="retry-msg"]');
    var id = row.querySelector('[data-role="id"]').textContent;
    hideErrors();
    setDisabled(button, true);
    button.setAttribute("aria-busy", "true");
    setTimeout(function () {
      button.removeAttribute("aria-busy");
      setDisabled(button, false);
      var bad = failure("retry", id);
      if (bad) return showError(bad[0], bad[1]);
      message.textContent = "Retry enqueued: job " + FIX.corpus.retry.job_id;
      message.hidden = false;
    }, RETRY_MS);
  }

  // ---- operator panels ----

  function fillInstance() {
    var info = FIX.shell.info;
    var panel = ID("instance.panel");
    ID("instance.version").textContent = info.version;
    ID("instance.workspace").textContent = info.workspace;
    panel.querySelector('[data-role="clients"]').textContent = CLIENTS.map(function (c) {
      return c + " " + (info.clients[c] ? "yes" : "no");
    }).join(", ");
    panel.querySelector('[data-role="write"]').textContent = info.write_in_flight ? "yes" : "no";
    panel.querySelector('[data-role="graph"]').textContent = info.graph_busy ? "yes" : "no";
  }

  function yesNo(value) {
    return value ? "yes" : "no";
  }

  function fillWirings() {
    var body = ID("wirings.table").tBodies[0];
    FIX.corpus.wirings.forEach(function (w) {
      var row = h("tr");
      [w.name, w.wiring_id, w.wiring_version, w.title, String(w.node_count), w.effects.join(", "), w.provides.join(", "), w.harnesses.join(", ") || "none", yesNo(w.default_eligible), yesNo(w.is_default), yesNo(w.reachable)].forEach(function (text, i) {
        row.appendChild(h("td", text, i < 3 ? "mono" : ""));
      });
      body.appendChild(row);
    });
  }

  function fillCatalogue() {
    var q = ID("catalogue.filter").value.trim().toLowerCase();
    var body = ID("catalogue.table").tBodies[0];
    var shown = 0;
    clearNode(body);
    FIX.refusals.forEach(function (r) {
      if (q !== "" && r.refusal_type.toLowerCase().indexOf(q) < 0) return;
      var row = h("tr");
      row.appendChild(h("td", r.refusal_type, "mono"));
      row.appendChild(h("td", String(r.http_status)));
      row.appendChild(h("td", r.attribute_keys.join(", ") || "none", "mono"));
      body.appendChild(row);
      shown += 1;
    });
    ID("catalogue.panel").querySelector('[data-role="count"]').textContent = shown + " of " + FIX.refusals.length + " refusal types";
  }

  // Returns the limit, or null after showing the error.
  function checkLimit() {
    var input = ID("log.limit");
    var raw = input.value.trim();
    var n = Number(raw);
    var valid = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 1000;
    setFieldError(input, valid ? "" : MSG.limit);
    return valid ? n : null;
  }

  function fillLog() {
    var n = checkLimit();
    if (n === null) return;
    ID("log.lines").textContent = FIX.corpus.log.lines.slice(-n).join("\n");
  }

  function openPanel(name) {
    var panel = ID(name);
    panel.open = true;
    panel.scrollIntoView({ block: "start" });
  }

  // ---- wiring ----

  Console.on("health", paintHealth);
  Console.on("show", function (name) {
    if (name === "corpus" && !loadedOnce) refreshAll();
  });
  Console.on("corpus-changed", refreshAll);
  Console.on("focus-health", function () {
    ID("health.panel").scrollIntoView({ block: "start" });
    ID("health.refresh").focus();
  });
  Console.on("open-log", function () {
    openPanel("log.panel");
  });
  Console.on("open-catalogue", function () {
    openPanel("catalogue.panel");
  });

  ID("health.refresh").addEventListener("click", refreshHealth);
  ID("health.poll").addEventListener("change", setHealthPoll);
  ID("health.poll-interval").addEventListener("change", setHealthPoll);
  ID("error.check-health").addEventListener("click", function () {
    Console.emit("focus-health");
  });

  Object.keys(tiles).forEach(function (status) {
    tiles[status].addEventListener("click", function () {
      setFilter(status === "total" ? "all" : status);
    });
  });
  ID("table.clear-filter").addEventListener("click", function () {
    setFilter("all");
  });
  ID("table.page-size").addEventListener("input", checkSize);
  ID("table.refresh").addEventListener("click", refreshAll);
  ID("table.prev").addEventListener("click", function () {
    loadPage(Math.max(0, page.offset - page.limit));
  });
  ID("table.next").addEventListener("click", function () {
    loadPage(page.body.next_offset);
  });
  ID("state.ingest-link").addEventListener("click", function (event) {
    event.preventDefault();
    Console.emit("open-ingest");
  });
  // One delegated listener serves the literal slot rows and every cloned row.
  tbody.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    var row = button.closest("tr");
    var mock = button.getAttribute("data-mock-id") || "";
    if (mock.indexOf("corpus.table.error-toggle-") === 0) {
      var open = button.getAttribute("aria-expanded") !== "true";
      row.querySelector('[data-role="error"]').hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      button.textContent = open ? "Hide error" : "Show error";
    } else if (mock.indexOf("corpus.table.delete-") === 0) {
      Console.emit("delete-document", { document_id: row.querySelector('[data-role="id"]').textContent });
    } else if (mock.indexOf("corpus.table.retry-") === 0) {
      retryDocument(Number(mock.slice(mock.lastIndexOf("-") + 1)));
    }
  });
  ID("catalogue.filter").addEventListener("input", fillCatalogue);
  ID("log.limit").addEventListener("input", checkLimit);
  ID("log.refresh").addEventListener("click", fillLog);

  wireErrors("corpus");
  fillInstance();
  fillWirings();
  fillCatalogue();
  fillLog();
  checkSize();
  paintHealth();
  paintPage();
  return {};
})();
Console.register("corpus", CorpusScreen);
