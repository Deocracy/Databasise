"use strict";
// Shared scope: every js/*.js file is concatenated into one script, so FIX, $id and Console are global to later screens.
var FIX = JSON.parse(document.getElementById("mock-fixtures").textContent);
var SCREENS = ["query", "evidence", "documents", "corpus", "ledger", "graph"];

function $id(mockId) {
  return document.querySelector('[data-mock-id="' + mockId + '"]');
}

var Console = {
  screens: {},
  handlers: {},
  current: null,
  register: function (name, impl) {
    this.screens[name] = impl;
  },
  show: function (name) {
    if (SCREENS.indexOf(name) < 0) name = "query";
    SCREENS.forEach(function (n) {
      $id("screen-" + n).hidden = n !== name;
      var button = $id("shell.nav." + n);
      if (n === name) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    this.current = name;
    if (location.hash !== "#" + name) location.hash = name;
    this.emit("show", name);
  },
  on: function (event, fn) {
    (this.handlers[event] = this.handlers[event] || []).push(fn);
  },
  emit: function (event, payload) {
    (this.handlers[event] || []).forEach(function (fn) {
      fn(payload);
    });
  },
};

var HEALTH_WORDS = { ok: "ok", degraded: "degraded", loading: "checking", error: "unreachable" };
var HEALTH_GLYPHS = { ok: "✓", degraded: "▲", loading: "", error: "✕" };
var HEALTH_TIMEOUT_MS = 60000;

function healthState(h) {
  if (h.loading) return "loading";
  return typeof h.status === "number" ? "error" : h.status;
}

// report: {loading: true}, a GET /health body, or {status: <number>, text: <cause>}.
function renderHealth(report) {
  Live.healthReport = report;
  var state = healthState(report);
  $id("shell.health.status").setAttribute("data-state", state);
  var badge = document.querySelector('[data-role="health-badge"]');
  badge.setAttribute("data-state", state);
  badge.querySelector(".spinner").hidden = state !== "loading";
  badge.querySelector('[data-role="health-glyph"]').textContent = HEALTH_GLYPHS[state];
  badge.querySelector('[data-role="health-word"]').textContent = HEALTH_WORDS[state];
  if (state === "error" && report.text) badge.setAttribute("title", report.text);
  else badge.removeAttribute("title");
  Console.emit("health", state);
}

// Corpus & Health reads the same report.
Console.health = function () {
  return Live.healthReport;
};

// The 60 s abort is a setTimeout (not AbortSignal.timeout) so a faked clock can drive it in tests.
Console.loadHealth = function () {
  renderHealth({ loading: true });
  var controller = new AbortController();
  var timer = setTimeout(function () {
    controller.abort();
  }, HEALTH_TIMEOUT_MS);
  return api("GET", "/health", null, { signal: controller.signal }).then(function (result) {
    clearTimeout(timer);
    var report;
    if (result.aborted) report = { status: 0, text: "Health check timed out after 60 seconds." };
    else if (result.status === 0) report = { status: 0, text: "No response from the server." };
    else if (result.status >= 200 && result.status < 300 && result.body && (result.body.status === "ok" || result.body.status === "degraded")) report = result.body;
    else report = { status: result.status, text: "The server answered HTTP " + result.status + "." };
    renderHealth(report);
    Console.emit("health-report", report);
    return report;
  });
};

// A rejected call on any screen also puts the header at unreachable (D-12).
Console.on("unreachable", function () {
  renderHealth({ status: 0, text: "No response from the server." });
});

$id("shell.health.details").addEventListener("click", function () {
  Console.show("corpus");
  Console.emit("focus-health");
});

SCREENS.forEach(function (name) {
  $id("shell.nav." + name).addEventListener("click", function () {
    Console.show(name);
  });
});
window.addEventListener("hashchange", function () {
  var name = location.hash.slice(1);
  if (name !== Console.current) Console.show(name);
});

window.Console = Console;
