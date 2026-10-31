"use strict";
// 18-03 (D-05, D-13): the live core. `api` is the only fetch call in the console and always resolves; `InFlight` is the
// shared registry of calls that block the header health poll; `Live` holds the OpenAPI spec and the last health report.

var InFlight = {
  counts: {},
  begin: function (kind) {
    var ended = false;
    this.counts[kind] = (this.counts[kind] || 0) + 1;
    Console.emit("inflight");
    return function () {
      if (ended) return;
      ended = true;
      InFlight.counts[kind] -= 1;
      Console.emit("inflight");
    };
  },
  any: function () {
    var counts = this.counts;
    return Object.keys(counts).some(function (kind) {
      return counts[kind] > 0;
    });
  },
  writing: function () {
    return (this.counts.ingest || 0) + (this.counts["delete"] || 0) > 0;
  },
};

// Resolves {status, body}; {status: 0, body: "server unreachable"} for a rejected fetch; {status: -1, aborted: true}
// for an abort; {status, res} with opts.raw. opts.kind registers the call in InFlight. Never throws.
function api(method, path, body, opts) {
  opts = opts || {};
  var init = { method: method, headers: {}, signal: opts.signal };
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    init.body = body; // no Content-Type: the browser adds the multipart boundary
  } else if (body !== undefined && body !== null) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  var done = opts.kind ? InFlight.begin(opts.kind) : function () {};
  return fetch(path, init)
    .then(function (res) {
      if (opts.raw) return { status: res.status, res: res };
      return res.text().then(function (text) {
        var parsed = text;
        try {
          parsed = JSON.parse(text);
        } catch (ignored) {
          // not JSON: the text itself is the body
        }
        return { status: res.status, body: parsed };
      });
    })
    .catch(function (error) {
      if (error && error.name === "AbortError") return { status: -1, aborted: true };
      Console.emit("unreachable");
      return { status: 0, body: "server unreachable" };
    })
    .then(function (result) {
      done();
      return result;
    });
}

// Reads a text/event-stream response (D-10). The caller has checked res.ok and the content type. Frames are separated by a blank
// line; a frame without a data line (a ": ping" comment) is skipped. onEvidence(ref) and onFinal(event) are called in arrival
// order. Resolves true once a final event arrived and false when the stream ended without one, including a read that failed
// after the first chunk (18-RESEARCH A3); a read that fails before any chunk rejects.
function readStream(res, onEvidence, onFinal) {
  var reader = res.body.getReader();
  var decoder = new TextDecoder();
  var buffer = "";
  var gotChunk = false;
  var sawFinal = false;

  function frame(text) {
    var data = text
      .split(/\r?\n/)
      .filter(function (line) {
        return line.indexOf("data:") === 0;
      })
      .map(function (line) {
        return line.slice(5).replace(/^ /, "");
      })
      .join("\n");
    if (!data) return;
    var event;
    try {
      event = JSON.parse(data);
    } catch (ignored) {
      return; // a frame that is not JSON counts as lost; without a final the run shows as unfinished
    }
    if (event.kind === "evidence") onEvidence(event.evidence);
    else if (event.kind === "final") {
      sawFinal = true;
      onFinal(event);
    }
  }

  function pump() {
    return reader.read().then(
      function (chunk) {
        if (chunk.done) {
          if (buffer.trim()) frame(buffer);
          return sawFinal;
        }
        gotChunk = true;
        buffer += decoder.decode(chunk.value, { stream: true });
        var gap;
        while ((gap = /\r?\n\r?\n/.exec(buffer))) {
          frame(buffer.slice(0, gap.index));
          buffer = buffer.slice(gap.index + gap[0].length);
        }
        return pump();
      },
      function (error) {
        if (gotChunk) return sawFinal;
        throw error;
      }
    );
  }
  return pump();
}

// A newest-first list kept in memory and mirrored to sessionStorage under `key`, trimmed to `cap`. Every storage access is in
// try/catch: a storage that throws leaves the memory list working with no message (D-07, 18-RESEARCH Pitfall 13).
function SessionLog(key, cap) {
  var items = [];
  try {
    var parsed = JSON.parse(sessionStorage.getItem(key) || "[]");
    if (Array.isArray(parsed)) {
      items = parsed
        .filter(function (entry) {
          return entry !== null && typeof entry === "object";
        })
        .slice(0, cap);
    }
  } catch (ignored) {
    // unreadable or blocked storage starts an empty log
  }
  function save() {
    try {
      sessionStorage.setItem(key, JSON.stringify(items));
    } catch (ignored) {
      // the memory list stays the source of truth
    }
  }
  return {
    all: function () {
      return items.slice();
    },
    add: function (entry) {
      items.unshift(entry);
      items = items.slice(0, cap);
      save();
    },
    clear: function () {
      items = [];
      save();
    },
  };
}

function normalizePath(path) {
  return path.replace(/\{[^}]*\}/g, "{}");
}

var Live = {
  spec: null,
  healthReport: { loading: true },
  // The OpenAPI operation for a method and path template, or null. Parameter names in the path are ignored.
  operation: function (method, path) {
    var paths = this.spec && this.spec.paths;
    if (!paths) return null;
    var want = normalizePath(path);
    var keys = Object.keys(paths);
    for (var i = 0; i < keys.length; i++) {
      if (normalizePath(keys[i]) === want) return paths[keys[i]][method.toLowerCase()] || null;
    }
    return null;
  },
  has: function (method, path) {
    return this.operation(method, path) !== null;
  },
};

// ---- run-time badge rule (D-08, D-09, LIVE-09) ----

// Keys are "<scope> <data-needs-backend value>". A badge drops only when its route is in the spec AND its key is
// here. Each screen file adds its own keys at its top, e.g. WIRED["query GET /log"] = true; this literal is not edited.
var WIRED = { "shell GET /info": true };

// Absent routes with a client-side fallback: the screens show their own fallback line instead of a disabled control.
var FALLBACK = ["GET /ledger/aliases", "POST /ledger/history", "POST /promote/preview", "POST /selectors/resolve", "GET /refusals"];

var CONTROLS = "button, input, select, textarea";

// "shell" (header), "dialog", or the name of the closest screen-<name> ancestor.
function scopeOf(el) {
  if (el.closest("dialog")) return "dialog";
  var screen = el.closest('[data-mock-id^="screen-"]');
  return screen ? screen.getAttribute("data-mock-id").slice("screen-".length) : "shell";
}

// "METHOD /path (p1, p2)" -> {method, path, params}, or null for text that is not a route.
function routeOf(value) {
  var m = /^(GET|POST|PUT|DELETE)\s+(\S+)(?:\s*\(([^)]*)\))?\s*$/.exec(value);
  if (!m) return null;
  var params = (m[3] || "")
    .split(",")
    .map(function (name) {
      return name.trim();
    })
    .filter(Boolean);
  return { method: m[1], path: m[2], params: params };
}

function routePresent(value) {
  var route = routeOf(value);
  var operation = route && Live.operation(route.method, route.path);
  if (!operation) return false;
  var names = (operation.parameters || []).map(function (p) {
    return p.name;
  });
  return route.params.every(function (name) {
    return names.indexOf(name) >= 0;
  });
}

function controlsIn(el) {
  var list = Array.prototype.slice.call(el.querySelectorAll(CONTROLS + ", a"));
  if (el.matches(CONTROLS + ", a")) list.unshift(el);
  return list;
}

// Shared by every screen: a control inside an absent route stays disabled whatever the screen asks for.
function setDisabled(el, disabled) {
  var locked = !!el.closest("[data-route-absent]");
  var off = disabled || locked;
  if ("disabled" in el) el.disabled = off;
  if (off) el.setAttribute("aria-disabled", "true");
  else el.removeAttribute("aria-disabled");
}

function markAbsent(el) {
  var value = el.getAttribute("data-needs-backend");
  var route = routeOf(value);
  if (route && FALLBACK.indexOf(route.method + " " + route.path) >= 0) return;
  el.setAttribute("data-route-absent", "");
  var controls = controlsIn(el);
  controls.forEach(function (control) {
    if (control.tagName === "A") {
      control.setAttribute("aria-disabled", "true");
      control.setAttribute("tabindex", "-1");
    } else {
      control.disabled = true;
      control.setAttribute("aria-disabled", "true");
    }
  });
  // shortcut: a wrapper with no control (the header chip) carries only its badge, no reason line.
  if (!controls.length) return;
  var line = document.createElement("span");
  line.className = "needs-route muted";
  line.textContent = "Needs " + value + "."; // the full value, so "GET /corpus (status, sort, search)" names its parameters
  el.appendChild(line);
}

// spec === null (the spec failed to load) counts every element as absent, so every badge stays.
function applyBadges(spec) {
  Live.spec = spec;
  Array.prototype.forEach.call(document.querySelectorAll("[data-needs-backend]"), function (el) {
    var value = el.getAttribute("data-needs-backend");
    if (!routePresent(value) || !WIRED[scopeOf(el) + " " + value]) return markAbsent(el);
    // Collect the wrapper's own badges first: a badge in a nested wrapper keeps that wrapper's.
    var own = Array.prototype.filter.call(el.querySelectorAll(".badge-nb, .badge-op"), function (badge) {
      return badge.closest("[data-needs-backend]") === el;
    });
    el.removeAttribute("data-needs-backend");
    el.removeAttribute("data-backend-state");
    el.removeAttribute("title");
    own.forEach(function (badge) {
      badge.remove();
    });
  });
}

// ---- dynamic rows (D-14) ----

// Makes the table body show exactly n data rows and returns them. The literal slot rows stay; rows above the literal count
// are clones of the last literal slot whose control ids take the next numeric suffix. Clones of an earlier render are
// removed first, so callers refill every returned row. A cell that holds a control keeps it when its row is hidden.
function ensureRows(tbody, n) {
  Array.prototype.forEach.call(tbody.querySelectorAll("tr[data-clone]"), function (clone) {
    clone.remove();
  });
  var rows = Array.prototype.slice.call(tbody.children);
  var last = rows[rows.length - 1];
  for (var number = rows.length + 1; number <= n; number++) {
    var copy = last.cloneNode(true);
    copy.setAttribute("data-clone", "true");
    Array.prototype.forEach.call(copy.querySelectorAll("[data-mock-id]"), function (el) {
      el.setAttribute("data-mock-id", el.getAttribute("data-mock-id").replace(/\d+$/, String(number)));
    });
    tbody.appendChild(copy);
    rows.push(copy);
  }
  rows.forEach(function (row, i) {
    row.hidden = i >= n;
    if (i < n) return;
    Array.prototype.forEach.call(row.children, function (cell) {
      if (!cell.children.length) cell.textContent = "";
    });
  });
  return rows.slice(0, n);
}

document.addEventListener(
  "click",
  function (event) {
    var target = event.target.closest('[aria-disabled="true"]');
    if (target && target.closest("[data-route-absent]")) {
      event.preventDefault();
      event.stopPropagation();
    }
  },
  true
);
