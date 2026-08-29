# evalModules standalone — no NixOS, only nixpkgs lib.
# args: wiringFile = path to a JSON wiring (authored by a non-Nix process),
#        overlayFile = optional second JSON merged on top (the "swap").
{ wiringFile, overlayFile ? null, forceSwap ? false }:
let
  lib = import <nixpkgs/lib>;
  fromJson = f: builtins.fromJSON (builtins.readFile f);
  base = { config = fromJson wiringFile; };
  overlay =
    if overlayFile == null then { }
    else if forceSwap then
      # swap-by-override: mkForce replaces the base definition wholesale
      { config = lib.mapAttrsRecursive (_: v: v) {
          components = lib.mapAttrs (_: c: lib.mkForce c) (fromJson overlayFile).components;
        }; }
    else { config = fromJson overlayFile; };
  eval = lib.evalModules {
    modules = [ ./contract.nix base overlay ];
  };
  failed = builtins.filter (a: !a.assertion) eval.config.assertions;
in
if failed != [ ]
then throw "wiring INVALID: ${lib.concatMapStringsSep "; " (a: a.message) failed}"
else {
  valid = true;
  components = lib.mapAttrs (_: c: { inherit (c) version config_hash capabilities; })
    eval.config.components;
  edges = builtins.length eval.config.wiring;
}
