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

function renderHealth(fixtureName) {
  var h = FIX.health[fixtureName];
  $id("shell.health.status").setAttribute("data-state", "ok");
  document.querySelector('[data-role="health-badge"]').setAttribute("data-state", "ok");
  document.querySelector('[data-role="health-glyph"]').textContent = "✓";
  document.querySelector('[data-role="health-word"]').textContent = h.status;
}

SCREENS.forEach(function (name) {
  $id("shell.nav." + name).addEventListener("click", function () {
    Console.show(name);
  });
});
window.addEventListener("hashchange", function () {
  var name = location.hash.slice(1);
  if (name !== Console.current) Console.show(name);
});

function dispatch(method) {
  return function (screen) {
    var impl = Console.screens[screen];
    if (!impl || typeof impl[method] !== "function") {
      throw new Error(screen + " has no " + method);
    }
    return impl[method].apply(impl, Array.prototype.slice.call(arguments, 1));
  };
}

renderHealth("health-ok");
Console.show(location.hash.slice(1) || "query");

window.Console = Console;
window.__mock = {
  show: function (name) {
    Console.show(name);
  },
  setState: dispatch("setState"),
  inject: dispatch("inject"),
  loadFixture: dispatch("loadFixture"),
};
