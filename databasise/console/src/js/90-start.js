"use strict";
// 18-03: the start-up sequence. Every screen file has registered by now; the attribute set last is the test hook.
Console.show(location.hash.slice(1) || "query");
Console.loadHealth();
$id("shell.root.app").setAttribute("data-live-ready", "true");
