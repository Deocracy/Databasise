// Shared helpers for every screen. Text only ever reaches the DOM through textContent (Pitfall 11).
function h(tag, text, cls) {
  var node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

// Writes (or clears) the message under an input and marks the input invalid. The input names its message element in data-error-id.
function setFieldError(input, message) {
  var error = $id(input.getAttribute("data-error-id"));
  if (message) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
  if (error) {
    error.textContent = message || "";
    error.hidden = !message;
  }
}

// A selector value is null (Default), {alias}, {capability: [...]} or {harness}.
function selectorLabel(value) {
  if (!value) return "Default";
  if (value.alias !== undefined) return "alias " + value.alias;
  if (value.capability !== undefined) return "capability " + value.capability.join("+");
  return "harness " + value.harness;
}

// The server's un-prefixed rendering rule (compare keys): alias and harness are the string, capability joins with +, none is "default".
function comparisonKey(value) {
  if (!value) return "default";
  if (value.alias !== undefined) return value.alias;
  if (value.capability !== undefined) return value.capability.join("+");
  return value.harness;
}

var SELECTOR_MSG = {
  noCapability: "Select at least one capability. An empty set is refused by the server.",
  noAlias: "Enter an alias, or choose Default.",
  hashAlias: "This alias looks like a hash (64 hex characters, optional sha256: prefix). The server refuses it.",
};
var HASH_SHAPED = /^(sha256:)?[0-9a-f]{64}$/i;

// Selector resolution (D-06): the embedded post-WIRE-01 table plus the four documented combinations (API-INVENTORY 3.0).
var Resolution = (function () {
  var arms = {};
  var caps = {};
  var aliases = {};
  var def = null;
  var harness = null;
  var rows = FIX.resolution.rows.slice();
  var UNKNOWN = "Resolves to: unknown here (needs backend)";
  var ALIAS_UNKNOWN = "Alias not in the client-side ledger log; the server resolves it at run time.";

  function capKey(tokens) {
    return tokens.slice().sort().join("|");
  }

  rows.forEach(function (r) {
    if (r.wiring && !(r.wiring in arms)) arms[r.wiring] = r.node_count;
  });
  [
    [["reads_vector:chunks"], "naive"],
    [["calls_llm", "reads_graph"], "hipporag"],
    [["reads_graph", "reads_kv"], "hipporag"],
    [["calls_rerank", "reads_graph"], "local"],
  ].forEach(function (d) {
    rows.push({ selector: { capability: d[0] }, wiring: d[1], node_count: arms[d[1]], outcome: "resolved" });
  });
  rows.forEach(function (r) {
    var s = r.selector;
    if (s === null) def = r;
    else if (s.capability) caps[capKey(s.capability)] = r;
    else if (s.alias !== undefined) aliases[s.alias] = r;
    else harness = r;
  });
  FIX.aliases.forEach(function (a) {
    aliases[a.alias] = { wiring: a.arm, node_count: arms[a.arm], outcome: "resolved" };
  });

  function describe(r) {
    if (r.wiring) return { text: "Resolves to: " + r.wiring + " (" + r.node_count + " nodes)", arm: r.wiring, nodes: r.node_count };
    return { text: "Resolves to: not satisfiable (" + r.outcome + ")", arm: null, nodes: null };
  }

  return {
    rows: rows,
    resolve: function (value) {
      var r;
      if (value === null) r = def;
      else if (value.capability) r = caps[capKey(value.capability)];
      else if (value.alias !== undefined) {
        r = aliases[value.alias];
        if (!r) return { text: value.alias === "" ? UNKNOWN : ALIAS_UNKNOWN, arm: null, nodes: null };
      } else r = harness;
      return r ? describe(r) : { text: UNKNOWN, arm: null, nodes: null };
    },
  };
})();

// One selector picker per screen prefix: ids are <prefix>.selector.*. onChange runs after every edit.
var Picker = {
  attach: function (prefix, onChange) {
    function ID(name) {
      return $id(prefix + ".selector." + name);
    }
    var group = ID("group");
    var kinds = ["default", "alias", "capability", "harness"];
    var alias = ID("alias");
    var picker = ID("alias-picker");
    var capability = ID("capability");

    FIX.aliases.forEach(function (a) {
      var option = h("option", a.alias + " (" + a.arm + ", " + a.active_version + ")");
      option.value = a.alias;
      picker.appendChild(option);
    });

    function kind() {
      for (var i = 0; i < kinds.length; i++) if (ID("kind-" + kinds[i]).checked) return kinds[i];
      return "default";
    }

    function tokens() {
      return Array.prototype.filter
        .call(capability.options, function (o) {
          return o.selected;
        })
        .map(function (o) {
          return o.value;
        });
    }

    function value() {
      var k = kind();
      if (k === "alias") return { alias: alias.value };
      if (k === "capability") return { capability: tokens() };
      return null;
    }

    var api = {
      value: value,
      label: function () {
        return selectorLabel(value());
      },
      key: function () {
        return comparisonKey(value());
      },
      blockers: function () {
        var v = value();
        if (v && v.capability && v.capability.length === 0) return [SELECTOR_MSG.noCapability];
        if (v && v.alias !== undefined) {
          if (v.alias === "") return [SELECTOR_MSG.noAlias];
          if (HASH_SHAPED.test(v.alias)) return [SELECTOR_MSG.hashAlias];
        }
        return [];
      },
      resolve: function () {
        return Resolution.resolve(value()).text;
      },
      arm: function () {
        return Resolution.resolve(value()).arm;
      },
    };

    function refresh() {
      var chips = ID("chips");
      clearNode(chips);
      tokens().forEach(function (t) {
        chips.appendChild(h("span", t, "chip mono"));
      });
      ID("resolves-to").textContent = api.resolve();
      if (onChange) onChange(api);
    }

    group.addEventListener("input", function (event) {
      if (event.target === alias) ID("kind-alias").checked = true;
      refresh();
    });
    group.addEventListener("change", function (event) {
      if (event.target === picker && picker.value) {
        alias.value = picker.value;
        ID("kind-alias").checked = true;
      }
      if (event.target === capability) ID("kind-capability").checked = true;
      refresh();
    });
    refresh();
    return api;
  },
};

function copyText(text, flash) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {}, function () {}).catch(function () {});
    }
  } catch (e) {
    // clipboard access is optional in a file:// mockup
  }
  if (flash) {
    flash.hidden = false;
    setTimeout(function () {
      flash.hidden = true;
    }, 1500);
  }
}
