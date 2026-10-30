var QueryScreen = (function () {
  var STATES = ["idle", "running", "success", "partial", "empty-evidence", "refusal-422", "validation-422", "error-500"];
  var RESULT_STATES = ["success", "partial", "empty-evidence"];
  var root = $id("screen-query");
  var timers = [];
  var evidenceRefs = [];
  var lastTrace = null;

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
    showState("success");
  }

  function run() {
    cancelTimers();
    showState("running");
    later(800, function () {
      renderResult(FIX.query["q-success"].body);
    });
  }

  ID("run.submit").addEventListener("click", run);
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

  showState("idle");
  return {
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
