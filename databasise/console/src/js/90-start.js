"use strict";
// 18-03: the start-up sequence. Every screen file has registered by now; the attribute set last is the test hook.

// The mock ids stay in the source and the DOM (the id check needs them, D-06); only their visibility goes.
Array.prototype.forEach.call(document.querySelectorAll('[data-mock-id*=".mock."], [data-mock-only]'), function (el) {
  el.hidden = true;
});

api("GET", "/openapi.json").then(function (result) {
  var ok = result.status >= 200 && result.status < 300 && result.body !== null && typeof result.body === "object";
  // A spec that does not load changes nothing visible: every badge stays, and the cause goes to the browser console.
  if (!ok) console.warn("GET /openapi.json failed (status " + result.status + "); every needs-backend badge stays.");
  applyBadges(ok ? result.body : null);
  Console.show(location.hash.slice(1) || "query");
  Console.loadHealth();
  $id("shell.root.app").setAttribute("data-live-ready", "true");
});
