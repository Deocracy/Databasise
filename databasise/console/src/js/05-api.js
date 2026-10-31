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
