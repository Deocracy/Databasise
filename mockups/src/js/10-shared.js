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

// The four server error shapes (GUI-06, D-04). One classifier, in the UI-SPEC order, never on status alone.
var ERROR_SHAPES = ["refusal", "validation", "server-failure", "generic"];
var MONO_KEY = /trace|alias|version|document|job|key|ref/i;
var REFUSAL_HINTS = {
  UnknownTraceReferenceError: "Check the trace token. Tokens come from a query result or from Recent runs.",
  UnresolvableEvidenceReferenceError: "record no longer present; the store changed since the query.",
  UnsatisfiableSelectorError: "No wiring matches this selector. See the selector table.",
  DuplicateComparisonKeyError: "Change one selector so each comparison key is unique.",
  PartialRunEvidenceError: "Remove the partial run from the selection.",
  DisagreeingPromotionTraceIdsError: "Select traces from one selector only.",
  InvalidPromotionAliasError: "Use an alias that is not 64 hex characters.",
  InvalidChangeOriginError: "Choose human_edit or machine_mutation.",
  ActiveGenerationRetirementError: "roll back first, then retire.",
  TombstonedGenerationError: "This version is retired. Choose another version.",
  StoreBusyError: "The store is in use by another process. Retry when it has finished.",
  PageSizeExceededError: "Use a page size from 1 to 100.",
  NoRawUploadPathForModalityError: "Raw upload is not available for this selector. Use Paste text.",
};

function classifyResponse(status, body) {
  var structured = body !== null && typeof body === "object";
  if (structured && body.refusal_type === "ForeignEngineRefusalError") return "server-failure";
  if (structured && typeof body.refusal_type === "string") return "refusal";
  if (status === 422 && structured && Array.isArray(body.detail)) return "validation";
  if (status >= 200 && status < 300) return "result";
  return "generic";
}

function fillRole(banner, role, text) {
  banner.querySelector('[data-role="' + role + '"]').textContent = text;
}

function appendAttribute(list, key, value) {
  list.appendChild(h("dt", key));
  var dd = h("dd", null, MONO_KEY.test(key) ? "mono" : "");
  (Array.isArray(value) ? value : [value]).forEach(function (item, i) {
    if (i) dd.appendChild(document.createTextNode(", "));
    var text = item === null || item === undefined ? "—" : typeof item === "object" ? JSON.stringify(item) : String(item);
    if (/trace/i.test(key) && item) {
      var mark = document.createElement("mark");
      mark.textContent = text;
      dd.appendChild(mark);
    } else {
      dd.appendChild(document.createTextNode(text));
    }
  });
  list.appendChild(dd);
}

function fillRefusal(banner, status, body) {
  fillRole(banner, "type", body.refusal_type);
  fillRole(banner, "message", body.message || "");
  var list = banner.querySelector('[data-role="attrs"]');
  clearNode(list);
  Object.keys(body).forEach(function (key) {
    if (key !== "refusal_type" && key !== "message") appendAttribute(list, key, body[key]);
  });
  banner.querySelector('[data-role="attrs-wrap"]').hidden = list.children.length === 0;
  fillRole(banner, "hint", REFUSAL_HINTS[body.refusal_type] || "Review the attributes and change the request.");
  var entry = FIX.refusals.filter(function (r) {
    return r.refusal_type === body.refusal_type;
  })[0];
  var keys = entry ? entry.attribute_keys.join(", ") || "none" : "not in the catalogue";
  fillRole(banner, "footer", "HTTP " + status + ". Documented attributes: " + keys + ".");
}

function fillValidation(screen, banner, body) {
  var list = banner.querySelector('[data-role="list"]');
  clearNode(list);
  fillRole(banner, "summary", "The request has " + body.detail.length + " invalid field(s).");
  var fields = Array.prototype.slice.call($id("screen-" + screen).querySelectorAll("[data-field-loc]"));
  body.detail.forEach(function (d) {
    var loc = (d.loc || []).join(".");
    list.appendChild(h("li", loc + ": " + d.msg));
    fields.forEach(function (field) {
      if (field.getAttribute("data-field-loc") === loc) setFieldError(field, d.msg);
    });
  });
}

function fillServerFailure(banner, body) {
  fillRole(banner, "text", "The server could not complete the operation (" + body.operation + ", " + body.failure_class + "). The input was not at fault. Retry later or check the server log.");
  var list = banner.querySelector('[data-role="detail-list"]');
  clearNode(list);
  ["message", "failure_class", "operation", "trace_token", "cause"].forEach(function (key) {
    if (body[key] !== undefined && body[key] !== null) list.appendChild(h("div", key + ": " + body[key]));
  });
  var open = banner.querySelector('[data-mock-id$=".error.open-trace"]');
  open.hidden = !body.trace_token;
  open.setAttribute("data-token", body.trace_token || "");
  banner.querySelector('[data-role="details"]').hidden = true;
  var toggle = banner.querySelector('[data-mock-id$=".error.details-toggle"]');
  toggle.setAttribute("aria-expanded", "false");
  toggle.textContent = "Show details";
}

function fillGeneric(banner, status, body, opts) {
  fillRole(banner, "text", opts && opts.text ? opts.text : status === 0 ? "No response from the server." : "The server returned HTTP " + status + " with no structured body. Check the server log.");
  var pre = banner.querySelector('[data-role="body"]');
  var text = typeof body === "string" ? body : body === null || body === undefined ? "" : JSON.stringify(body);
  pre.textContent = text.slice(0, 500);
  pre.hidden = text === "";
}

// Shows exactly one of the four shapes of a screen (or none for a 2xx) and returns the shape name.
function renderError(screen, status, body, opts) {
  var shape = classifyResponse(status, body);
  ERROR_SHAPES.forEach(function (s) {
    $id(screen + ".error." + s).hidden = true;
  });
  Array.prototype.forEach.call($id("screen-" + screen).querySelectorAll("[data-error-id]"), function (el) {
    setFieldError(el, "");
  });
  if (shape === "result") return shape;
  var banner = $id(screen + ".error." + shape);
  if (shape === "refusal") fillRefusal(banner, status, body);
  else if (shape === "validation") fillValidation(screen, banner, body);
  else if (shape === "server-failure") fillServerFailure(banner, body);
  else fillGeneric(banner, status, body, opts);
  banner.hidden = false;
  return shape;
}

// Click behaviour of the shared error components; every screen with the errors partial calls this once.
function wireErrors(screen) {
  var toggle = $id(screen + ".error.details-toggle");
  toggle.addEventListener("click", function () {
    var open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.parentElement.querySelector('[data-role="details"]').hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Hide details" : "Show details";
  });
  [["catalogue-link", "open-catalogue"], ["server-log", "open-log"]].forEach(function (pair) {
    $id(screen + ".error." + pair[0]).addEventListener("click", function (event) {
      event.preventDefault();
      Console.show("corpus");
      Console.emit(pair[1]);
    });
  });
  var open = $id(screen + ".error.open-trace");
  open.addEventListener("click", function () {
    Console.show("evidence");
    Console.emit("open-trace", { token: open.getAttribute("data-token") });
  });
}

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
