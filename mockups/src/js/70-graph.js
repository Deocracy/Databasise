var GraphScreen = (function () {
  var MSG = { pageSize: "Page size must be between 1 and 100.", noId: "Enter a node id." };
  var LOAD_MS = 300;
  var EDGE_PAGE = 6;
  var EMPTY = { offset: 0, total: 0, next_offset: null, nodes: [], refs: [] };

  var root = $id("screen-graph");
  var errorsBox = root.querySelector('[data-role="errors"]');
  var busyWrap = root.querySelector('[data-role="busy-wrap"]');
  var unknownWrap = root.querySelector('[data-role="unknown-wrap"]');
  var detailBody = root.querySelector('[data-role="detail-body"]');
  var nodeRows = ID("nodes.table").tBodies[0].rows;
  var edgeRows = ID("edges.table").tBodies[0].rows;
  var chunkRows = ID("chunks.table").tBodies[0].rows;
  var sizeInputs = [ID("nodes.page-size"), ID("edges.page-size"), ID("chunks.page-size")];

  var fixName = "lightrag";
  var nodePage = 0;
  var chunkPage = 0;
  var edgeOffset = 0;
  var openId = null;
  var attrsShown = false;
  var empty = false;
  var ready = false;
  var picker = null;
  var timer = null;
  var loading = { nodes: false, node: false, edges: false, chunks: false };

  function ID(name) {
    return $id("graph." + name);
  }

  function fix() {
    return FIX.graph[fixName];
  }

  function setDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
  }

  function wrapOf(table) {
    return table.parentElement;
  }

  function pagerOf(table) {
    return wrapOf(table).nextElementSibling;
  }

  // ---- fixture lookups ----

  function allNodes() {
    return fix().nodes.reduce(function (all, page) {
      return all.concat(page.nodes);
    }, []);
  }

  // null when the id is not a node of the current fixture graph.
  function degreeOf(id) {
    var hit = allNodes().filter(function (n) {
      return n.id === id;
    })[0];
    return hit ? hit.degree : null;
  }

  // Edges as references {src, tgt, edge_types, weight}. Nodes without explicit rows get rows derived from their degree.
  function edgesOf(id) {
    var f = fix();
    if (f.edges[id]) return f.edges[id];
    var pool = allNodes()
      .map(function (n) {
        return n.id;
      })
      .filter(function (other) {
        return other !== id;
      });
    var rows = [];
    for (var i = 0; i < degreeOf(id); i++) {
      rows.push({ src: id, tgt: pool[i % pool.length], edge_types: f.edge_types, weight: Math.round((f.weight.start - i * f.weight.step) * 100) / 100 });
    }
    return rows;
  }

  function attrsOf(id) {
    return (
      fix().attrs[id] || {
        entity_type: id.indexOf("chunk:") === 0 ? "CHUNK" : "ENTITY",
        description: "Fixture description for " + id + ".",
        source_id: fix().chunks[0].refs[1].ref,
      }
    );
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
  function fail(status, body) {
    var name = body && typeof body === "object" ? body.refusal_type : "";
    if (name === "StoreBusyError") return showState("store-busy", body);
    if (name === "UnknownGraphNodeError") return showState("unknown-node", body);
    busyWrap.hidden = true;
    unknownWrap.hidden = true;
    var shape = renderError("graph", status, body);
    errorsBox.hidden = shape === "result";
    if (shape !== "result") errorsBox.scrollIntoView({ block: "nearest" });
  }

  function unknownBody(id) {
    return { refusal_type: "UnknownGraphNodeError", message: FIX.graph["unknown-node"].body.message, node_id: id };
  }

  // The mock outcome select decides which server response the next call gets.
  function failure(op, id) {
    var o = ID("mock.outcome").value;
    if (o === "refusal") {
      if (op === "node" || op === "edges") return [422, unknownBody(id)];
      return [409, FIX.graph["store-busy"].body];
    }
    if (o === "validation") {
      var loc = op === "nodes" ? ["body", "limit"] : op === "node" ? ["body", "node_id"] : ["body", "offset"];
      return [422, { detail: [{ loc: loc, msg: "Input should be greater than or equal to " + (op === "nodes" ? 1 : 0), type: "value_error" }] }];
    }
    if (o === "server-failure") {
      return [502, { refusal_type: "ForeignEngineRefusalError", message: "operation '" + op + "' failed (StoreFault)", operation: op, failure_class: "StoreFault" }];
    }
    if (o === "generic") return [500, "Internal Server Error"];
    return null;
  }

  // ---- checks ----

  function checkSize(input) {
    var raw = input.value.trim();
    var n = Number(raw);
    var ok = raw !== "" && Number.isInteger(n) && n >= 1 && n <= 100;
    setFieldError(input, ok ? "" : MSG.pageSize);
  }

  // renderError clears every field message, so the client-side checks are rerun afterwards.
  function checkAll() {
    sizeInputs.forEach(checkSize);
    if (picker) setFieldError(ID("selector.group"), picker.blockers()[0] || "");
  }

  // ---- paint ----

  function pageOf(list) {
    return empty ? EMPTY : list[list === fix().nodes ? nodePage : chunkPage];
  }

  function paintCounts() {
    var counts = empty ? { nodes: 0, edges: 0, chunks: 0 } : fix().counts;
    ["nodes", "edges", "chunks"].forEach(function (key) {
      ID("counts." + key).querySelector('[data-role="count"]').textContent = String(counts[key]);
    });
  }

  function pager(table, prev, next, busy, page, shown) {
    var bar = pagerOf(table);
    var items = page.nodes || page.refs;
    bar.hidden = busy || shown === 0;
    setDisabled(prev, busy || page.offset <= 0);
    setDisabled(next, busy || page.next_offset === null);
    bar.querySelector('[data-role="range"]').textContent = items.length ? "Showing " + (page.offset + 1) + " to " + (page.offset + items.length) + " of " + page.total : "";
  }

  function paintNodes() {
    var page = pageOf(fix().nodes);
    var prefix = ID("nodes.prefix").value;
    var list = page.nodes.filter(function (n) {
      return n.id.indexOf(prefix) === 0;
    });
    Array.prototype.forEach.call(nodeRows, function (row, i) {
      var node = list[i];
      row.hidden = !node;
      if (!node) return;
      row.querySelector('[data-role="id"]').textContent = node.id;
      row.querySelector('[data-role="degree"]').textContent = String(node.degree);
      ID("nodes.open-" + (i + 1)).setAttribute("aria-label", "Open " + node.id);
    });
    ID("nodes.total").textContent = (empty ? 0 : fix().nodes[0].total) + " nodes in this graph";
    ID("nodes.loading").hidden = !loading.nodes;
    ID("nodes.empty").hidden = loading.nodes || list.length > 0;
    wrapOf(ID("nodes.table")).hidden = loading.nodes || list.length === 0;
    // The prefix narrows the current page only, so paging stays available while it matches nothing here.
    pager(ID("nodes.table"), ID("nodes.prev"), ID("nodes.next"), loading.nodes, page, page.nodes.length);
    if (prefix !== "" && page.nodes.length) pagerOf(ID("nodes.table")).querySelector('[data-role="range"]').textContent += ". " + list.length + " on this page start with the prefix.";
  }

  function paintChunks() {
    var page = pageOf(fix().chunks);
    Array.prototype.forEach.call(chunkRows, function (row, i) {
      var chunk = page.refs[i];
      row.hidden = !chunk;
      if (!chunk) return;
      row.querySelector('[data-role="ref"]').textContent = chunk.ref;
      row.querySelector('[data-role="kind"]').textContent = chunk.kind;
      ID("chunks.open-" + (i + 1)).setAttribute("aria-label", "Open chunk " + chunk.ref);
    });
    ID("chunks.total").textContent = page.total + " chunks in this store";
    ID("chunks.loading").hidden = !loading.chunks;
    ID("chunks.empty").hidden = loading.chunks || page.refs.length > 0;
    wrapOf(ID("chunks.table")).hidden = loading.chunks || page.refs.length === 0;
    pager(ID("chunks.table"), ID("chunks.prev"), ID("chunks.next"), loading.chunks, page, page.refs.length);
  }

  function fillTypes(cell, types) {
    clearNode(cell);
    if (!types) return cell.appendChild(document.createTextNode("—"));
    types.forEach(function (t) {
      cell.appendChild(h("span", t, "chip"));
    });
  }

  function paintEdges() {
    var rows = edgesOf(openId);
    var slice = rows.slice(edgeOffset, edgeOffset + EDGE_PAGE);
    Array.prototype.forEach.call(edgeRows, function (row, i) {
      var edge = slice[i];
      row.hidden = !edge;
      if (!edge) return;
      row.querySelector('[data-role="src"]').textContent = edge.src;
      row.querySelector('[data-role="tgt"]').textContent = edge.tgt;
      fillTypes(row.querySelector('[data-role="types"]'), edge.edge_types);
      row.querySelector('[data-role="weight"]').textContent = edge.weight === null || edge.weight === undefined ? "—" : String(edge.weight);
      ID("edges.open-" + (i + 1)).setAttribute("aria-label", "Open node " + edge.tgt);
    });
    ID("edges.loading").hidden = !loading.edges;
    ID("edges.empty").hidden = loading.edges || rows.length > 0;
    wrapOf(ID("edges.table")).hidden = loading.edges || rows.length === 0;
    pager(ID("edges.table"), ID("edges.prev"), ID("edges.next"), loading.edges, { offset: edgeOffset, total: rows.length, next_offset: edgeOffset + EDGE_PAGE < rows.length ? edgeOffset + EDGE_PAGE : null, refs: slice }, rows.length);
  }

  function paintDetail() {
    ID("node.loading").hidden = !loading.node;
    root.querySelector('[data-role="prompt"]').hidden = loading.node || openId !== null;
    detailBody.hidden = loading.node || openId === null;
    if (openId === null) return;
    detailBody.querySelector('[data-role="node-id"]').textContent = openId;
    ID("node.degree").textContent = String(degreeOf(openId));
    var attrs = ID("node.attrs");
    attrs.hidden = !attrsShown;
    clearNode(attrs);
    if (attrsShown) {
      var data = attrsOf(openId);
      Object.keys(data).forEach(function (key) {
        appendAttribute(attrs, key, data[key]);
      });
    }
    paintEdges();
  }

  function paint() {
    ID("selector.family").textContent = "Reading: " + fix().family + " graph";
    ID("mock.fixture").value = fixName;
    paintCounts();
    paintNodes();
    paintDetail();
    paintChunks();
  }

  // ---- actions ----

  function resetView() {
    nodePage = 0;
    chunkPage = 0;
    edgeOffset = 0;
    openId = null;
    attrsShown = false;
    empty = false;
  }

  // Shows a short loading state on the named regions, then the mock outcome or the result of fn.
  function later(regions, op, id, fn) {
    clearTimeout(timer);
    hideErrors();
    regions.forEach(function (r) {
      loading[r] = true;
    });
    paint();
    timer = setTimeout(function () {
      Object.keys(loading).forEach(function (r) {
        loading[r] = false;
      });
      var bad = failure(op, id);
      if (bad) {
        paint();
        return fail(bad[0], bad[1]);
      }
      fn();
      paint();
    }, LOAD_MS);
  }

  function reload(name) {
    later(["nodes", "chunks"], "nodes", null, function () {
      fixName = name;
      resetView();
    });
  }

  function openNode(id) {
    later(["node"], "node", id, function () {
      if (degreeOf(id) === null) return fail(422, unknownBody(id));
      openId = id;
      edgeOffset = 0;
      attrsShown = false;
      ID("node.panel").scrollIntoView({ block: "nearest" });
    });
  }

  function submitLookup() {
    var input = ID("node.lookup");
    var id = input.value.trim();
    if (id === "") return setFieldError(input, MSG.noId);
    openNode(id);
  }

  // ---- hooks ----

  function setState(name) {
    clearTimeout(timer);
    if (name === "loading") {
      hideErrors();
      Object.keys(loading).forEach(function (r) {
        loading[r] = true;
      });
      return paint();
    }
    Object.keys(loading).forEach(function (r) {
      loading[r] = false;
    });
    if (name === "empty") {
      hideErrors();
      resetView();
      empty = true;
      return paint();
    }
    if (name !== "idle" && name !== "populated") throw new Error("unknown graph state " + name);
    hideErrors();
    resetView();
    paint();
  }

  function loadFixture(name) {
    clearTimeout(timer);
    Object.keys(loading).forEach(function (r) {
      loading[r] = false;
    });
    if (name === "store-busy" || name === "unknown-node") {
      ID("mock.fixture").value = name;
      return showState(name, FIX.graph[name].body);
    }
    if (name !== "lightrag" && name !== "hipporag") throw new Error("unknown graph fixture " + name);
    hideErrors();
    fixName = name;
    resetView();
    paint();
  }

  function inject(response) {
    clearTimeout(timer);
    Object.keys(loading).forEach(function (r) {
      loading[r] = false;
    });
    paint();
    fail(response.status, response.body);
  }

  // ---- wiring ----

  ID("mock.fixture").addEventListener("change", function () {
    loadFixture(this.value);
  });
  ID("state.retry").addEventListener("click", function () {
    reload(fixName);
  });
  wireErrors("graph");

  sizeInputs.forEach(function (input) {
    input.addEventListener("input", function () {
      checkSize(input);
    });
  });
  ID("nodes.prefix").addEventListener("input", paintNodes);
  ID("nodes.prev").addEventListener("click", function () {
    later(["nodes"], "nodes", null, function () {
      nodePage -= 1;
    });
  });
  ID("nodes.next").addEventListener("click", function () {
    later(["nodes"], "nodes", null, function () {
      nodePage += 1;
    });
  });
  ID("edges.prev").addEventListener("click", function () {
    later(["edges"], "edges", openId, function () {
      edgeOffset -= EDGE_PAGE;
    });
  });
  ID("edges.next").addEventListener("click", function () {
    later(["edges"], "edges", openId, function () {
      edgeOffset += EDGE_PAGE;
    });
  });
  ID("chunks.prev").addEventListener("click", function () {
    later(["chunks"], "chunks", null, function () {
      chunkPage -= 1;
    });
  });
  ID("chunks.next").addEventListener("click", function () {
    later(["chunks"], "chunks", null, function () {
      chunkPage += 1;
    });
  });
  ID("node.lookup-submit").addEventListener("click", submitLookup);
  ID("node.lookup").addEventListener("keydown", function (event) {
    if (event.key === "Enter") submitLookup();
  });
  ID("node.lookup").addEventListener("input", function () {
    setFieldError(this, "");
  });
  ID("node.attrs-load").addEventListener("click", function () {
    attrsShown = true;
    paintDetail();
  });
  [1, 2, 3, 4, 5, 6, 7, 8].forEach(function (n) {
    ID("nodes.open-" + n).addEventListener("click", function () {
      openNode(nodeRows[n - 1].querySelector('[data-role="id"]').textContent);
    });
    ID("chunks.open-" + n).addEventListener("click", function () {
      var ref = pageOf(fix().chunks).refs[n - 1];
      Console.show("evidence");
      Console.emit("open-evidence", { ref: { id: ref.ref, namespace: fix().chunk_namespace, kind: ref.kind } });
    });
  });
  [1, 2, 3, 4, 5, 6].forEach(function (n) {
    ID("edges.open-" + n).addEventListener("click", function () {
      openNode(edgeRows[n - 1].querySelector('[data-role="tgt"]').textContent);
    });
  });

  // The family follows the selector: HippoRAG arms read the hipporag graph, every other resolved arm the LightRAG graph.
  picker = Picker.attach("graph", function (api) {
    if (!ready) return;
    checkAll();
    var arm = api.arm();
    if (api.blockers().length || arm === null) return;
    var next = arm === "hipporag" ? "hipporag" : "lightrag";
    if (next !== fixName) reload(next);
  });
  ready = true;
  checkAll();
  paint();
  return { setState: setState, inject: inject, loadFixture: loadFixture };
})();
Console.register("graph", GraphScreen);
