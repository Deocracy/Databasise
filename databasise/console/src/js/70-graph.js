WIRED["graph POST /graph/nodes"] = true;
WIRED["graph POST /graph/node"] = true;
WIRED["graph POST /chunks"] = true;
WIRED["graph GET /ledger/aliases"] = true;
WIRED["graph GET /log"] = true;

var GraphScreen = (function () {
  var MSG = {
    pageSize: "Page size must be between 1 and 100.",
    noId: "Enter a node id.",
    prompt: "Choose a selector to read the graph.",
    badBody: "The server answered without a page.",
  };

  var root = $id("screen-graph");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var busyWrap = root.querySelector('[data-role="busy-wrap"]');
  var unknownWrap = root.querySelector('[data-role="unknown-wrap"]');
  var detailBody = root.querySelector('[data-role="detail-body"]');
  var nodesBody = ID("nodes.table").tBodies[0];
  var edgesBody = ID("edges.table").tBodies[0];
  var sizeInputs = [ID("nodes.page-size"), ID("edges.page-size"), ID("chunks.page-size")];
  var PANELS = { nodes: "nodes.panel", node: "node.panel", chunks: "chunks.panel" };

  var nodes = null; // the last good page: {offset, limit, body}
  var node = null; // the open node: {id, offset, limit, body}
  var ctl = { nodes: null, node: null, chunks: null }; // abort handles of the reads in flight
  var busy = { nodes: false, node: false, chunks: false };
  var last = null; // the last request, for Retry request: {key, path, body, onOk}
  var lastKey = null; // the selector the lists were last read for
  var loaded = false; // a read has been started from this screen
  var ready = false;
  var picker = null;

  function ID(name) {
    return $id("graph." + name);
  }

  function ok(result) {
    return result.status >= 200 && result.status < 300;
  }

  function sel() {
    return picker.value() || {};
  }

  function wrapOf(table) {
    return table.parentElement;
  }

  function pagerOf(table) {
    return wrapOf(table).nextElementSibling;
  }

  // ---- errors ----

  function hideErrors() {
    renderError("graph", 200, null);
    errorsBox.hidden = true;
    busyWrap.hidden = true;
    unknownWrap.hidden = true;
    checkAll();
  }

  function showState(name, body) {
    hideErrors();
    if (name === "store-busy") {
      busyWrap.querySelector('[data-role="message"]').textContent = body.message || "";
      busyWrap.hidden = false;
    } else {
      unknownWrap.querySelector("mark").textContent = body.node_id;
      unknownWrap.hidden = false;
    }
  }

  // The two named refusals have their own banners; every other response uses the shared error shapes.
  function fail(status, body, opts) {
    var name = body && typeof body === "object" ? body.refusal_type : "";
    if (name === "StoreBusyError") return showState("store-busy", body);
    if (name === "UnknownGraphNodeError") return showState("unknown-node", body);
    busyWrap.hidden = true;
    unknownWrap.hidden = true;
    var shape = renderError("graph", status, body, opts);
    errorsBox.hidden = shape === "result";
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
  }

  // ---- checks ----

  function limitOf(input) {
    var raw = input.value.trim();
    var n = Number(raw);
    return raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100 ? n : null;
  }

  function checkSize(input) {
    setFieldError(input, limitOf(input) === null ? MSG.pageSize : "");
  }

  // renderError clears every field message, so the client-side checks are rerun afterwards.
  function checkAll() {
    sizeInputs.forEach(checkSize);
    if (picker) setFieldError(ID("selector.group"), picker.blockers()[0] || "");
  }

  // ---- paint ----

  function paintCounts() {
    // No route reports store counts (POST /stores/counts), so the tiles never show a number.
    ["nodes", "edges", "chunks"].forEach(function (key) {
      ID("counts." + key).querySelector('[data-role="count"]').textContent = "—";
    });
  }

  function paintPager(table, prev, next, view, count, total, nextOffset) {
    var bar = pagerOf(table);
    bar.hidden = !view || (count === 0 && view.offset === 0);
    setDisabled(prev, !view || view.offset <= 0);
    setDisabled(next, !view || nextOffset === null || nextOffset === undefined);
    bar.querySelector('[data-role="range"]').textContent = view && count ? "Showing " + (view.offset + 1) + " to " + (view.offset + count) + " of " + total : "";
  }

  function paintNodes() {
    var list = nodes ? nodes.body.nodes : [];
    var prefix = ID("nodes.prefix").value;
    ensureRows(nodesBody, list.length).forEach(function (row, i) {
      row.querySelector('[data-role="id"]').textContent = list[i].id;
      row.querySelector('[data-role="degree"]').textContent = String(list[i].degree);
      row.querySelector("button").setAttribute("aria-label", "Open " + list[i].id);
    });
    ID("nodes.total").textContent = nodes ? nodes.body.total + (prefix === "" ? " nodes in this graph" : " nodes match this prefix") : MSG.prompt;
    ID("nodes.empty").hidden = !nodes || list.length > 0;
    wrapOf(ID("nodes.table")).hidden = list.length === 0;
    paintPager(ID("nodes.table"), ID("nodes.prev"), ID("nodes.next"), nodes, list.length, nodes && nodes.body.total, nodes && nodes.body.next_offset);
  }

  function fillTypes(cell, types) {
    clearNode(cell);
    if (!types || !types.length) return cell.appendChild(document.createTextNode("—"));
    types.forEach(function (t) {
      cell.appendChild(h("span", t, "chip"));
    });
  }

  function paintDetail() {
    root.querySelector('[data-role="prompt"]').hidden = node !== null;
    detailBody.hidden = node === null;
    var edges = node ? node.body.edges : [];
    if (node) {
      detailBody.querySelector('[data-role="node-id"]').textContent = node.id;
      ID("node.degree").textContent = String(node.body.degree);
    }
    ensureRows(edgesBody, edges.length).forEach(function (row, i) {
      var edge = edges[i];
      row.querySelector('[data-role="src"]').textContent = edge.src;
      row.querySelector('[data-role="tgt"]').textContent = edge.tgt;
      fillTypes(row.querySelector('[data-role="types"]'), edge.edge_types);
      row.querySelector('[data-role="weight"]').textContent = edge.weight === null || edge.weight === undefined ? "—" : String(edge.weight);
      row.querySelector("button").setAttribute("aria-label", "Open node " + edge.tgt);
    });
    ID("edges.empty").hidden = !node || edges.length > 0;
    wrapOf(ID("edges.table")).hidden = edges.length === 0;
    paintPager(ID("edges.table"), ID("edges.prev"), ID("edges.next"), node, edges.length, node && node.body.degree, node && node.body.next_offset);
  }

  function paintBusy() {
    Object.keys(PANELS).forEach(function (key) {
      var panel = ID(PANELS[key]);
      if (busy[key]) panel.setAttribute("aria-busy", "true");
      else panel.removeAttribute("aria-busy");
    });
    ID("nodes.loading").hidden = !busy.nodes;
    ID("node.loading").hidden = !(busy.node && node === null);
    ID("edges.loading").hidden = !(busy.node && node !== null);
    ID("chunks.loading").hidden = !busy.chunks;
    [ID("nodes.prev"), ID("nodes.next")].forEach(function (button) {
      if (busy.nodes) setDisabled(button, true);
    });
    [ID("edges.prev"), ID("edges.next")].forEach(function (button) {
      if (busy.node) setDisabled(button, true);
    });
  }

  function paint() {
    paintCounts();
    paintNodes();
    paintDetail();
    paintBusy();
  }

  // ---- reads ----

  function cancel(key) {
    if (ctl[key]) ctl[key].abort();
    ctl[key] = null;
    busy[key] = false;
  }

  // One read of a list or a node. A replaced read is dropped; the last good page stays on screen while it runs and after it fails.
  function run(key, path, body, onOk) {
    cancel(key);
    var mine = (ctl[key] = new AbortController());
    last = { key: key, path: path, body: body, onOk: onOk };
    hideErrors();
    busy[key] = true;
    paint();
    return api("POST", path, body, { signal: mine.signal }).then(function (result) {
      if (result.aborted || mine !== ctl[key]) return;
      ctl[key] = null;
      busy[key] = false;
      var page = result.body;
      var good = ok(result) && page !== null && typeof page === "object";
      if (good) onOk(page);
      paint();
      if (good) return;
      var odd = ok(result);
      fail(odd ? 0 : result.status, odd ? null : result.body, odd ? { text: MSG.badBody } : undefined);
    });
  }

  function loadNodes(offset) {
    var limit = limitOf(ID("nodes.page-size"));
    if (limit === null) return checkSize(ID("nodes.page-size"));
    var body = { selector: sel(), prefix: ID("nodes.prefix").value, limit: limit, offset: offset };
    return run("nodes", "/graph/nodes", body, function (page) {
      nodes = { offset: offset, limit: limit, body: page };
    });
  }

  function openNode(id, offset) {
    if (picker.blockers().length) return checkAll();
    var limit = limitOf(ID("edges.page-size"));
    if (limit === null) return checkSize(ID("edges.page-size"));
    var body = { selector: sel(), node_id: id, limit: limit, offset: offset };
    return run("node", "/graph/node", body, function (page) {
      node = { id: id, offset: offset, limit: limit, body: page };
      if (offset === 0) ID("node.panel").scrollIntoView({ block: "nearest" });
    });
  }

  // A new selector starts the lists again and closes the open node.
  function loadAll() {
    loaded = true;
    lastKey = JSON.stringify(sel());
    cancel("node");
    node = null;
    loadNodes(0);
  }

  function submitLookup() {
    var input = ID("node.lookup");
    var id = input.value.trim();
    if (id === "") return setFieldError(input, MSG.noId);
    openNode(id, 0);
  }

  // ---- wiring ----

  ID("state.retry").addEventListener("click", function () {
    if (last) run(last.key, last.path, last.body, last.onOk);
  });
  wireErrors("graph");

  sizeInputs.forEach(function (input) {
    input.addEventListener("input", function () {
      checkSize(input);
    });
  });
  ID("nodes.prefix").addEventListener("change", function () {
    if (loaded && !picker.blockers().length) loadNodes(0);
  });
  ID("nodes.page-size").addEventListener("change", function () {
    if (loaded && !picker.blockers().length) loadNodes(0);
  });
  ID("edges.page-size").addEventListener("change", function () {
    if (node) openNode(node.id, 0);
  });
  ID("node.lookup-submit").addEventListener("click", submitLookup);
  ID("node.lookup").addEventListener("keydown", function (event) {
    if (event.key === "Enter") submitLookup();
  });
  ID("node.lookup").addEventListener("input", function () {
    setFieldError(this, "");
  });
  ID("nodes.table").addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (button && !button.disabled) openNode(button.closest("tr").querySelector('[data-role="id"]').textContent, 0);
  });
  ID("edges.table").addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (button && !button.disabled) openNode(button.closest("tr").querySelector('[data-role="tgt"]').textContent, 0);
  });

  // A selector edit reads again only when the selector itself changed: the alias catalogue refilling the picker is not an edit.
  picker = Picker.attach("graph", function (p) {
    if (!ready) return;
    checkAll();
    if (!Live.has("POST", "/graph/nodes") || p.blockers().length) return;
    if (JSON.stringify(sel()) !== lastKey) loadAll();
  });
  // Choosing Default while it is already chosen is a click, not a change: it starts the first read.
  ID("selector.kind-default").addEventListener("click", function () {
    if (!loaded && ready && Live.has("POST", "/graph/nodes")) loadAll();
  });
  lastKey = JSON.stringify(sel());
  ready = true;
  checkAll();
  paint();
  return {};
})();
Console.register("graph", GraphScreen);
