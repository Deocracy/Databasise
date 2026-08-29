# Spike 004 amendment: can evalModules serve as the wiring/swap layer?
# A miniature fitting contract as a module: typed component slots,
# capability manifests, machine-enforced preconditions as assertions.
{ lib, config, ... }:
let
  inherit (lib) types mkOption;

  capability = types.enum [
    "build-index" "retrieve" "answer" "rank" "temporal" "mutate"
    "self-ingesting" "deferred-extraction" "parse-derived-graph"
    "pass-through-retrieve" "live-external-retrieval"
  ];

  component = types.submodule ({ name, ... }: {
    options = {
      version = mkOption { type = types.strMatching "[0-9]+\\.[0-9]+\\.[0-9]+"; };
      config_hash = mkOption { type = types.strMatching "[a-f0-9]{8,64}"; };
      capabilities = mkOption { type = types.listOf capability; default = [ ]; };
      dependencies = mkOption { type = types.listOf types.str; default = [ ]; };
    };
  });

  edge = types.submodule {
    options = {
      from = mkOption { type = types.str; };
      to = mkOption { type = types.str; };
      # clause 4: interpretation travels with the value
      semantics = mkOption { type = types.enum [ "similarity" "rank" "probability" "distance" ]; };
    };
  };
in
{
  options = {
    components = mkOption { type = types.attrsOf component; default = { }; };
    wiring = mkOption { type = types.listOf edge; default = [ ]; };
    assertions = mkOption {
      type = types.listOf (types.submodule {
        options = {
          assertion = mkOption { type = types.bool; };
          message = mkOption { type = types.str; };
        };
      });
      default = [ ];
    };
  };

  config = {
    assertions =
      # clause 1: declarations are machine-enforced preconditions, fail closed
      (map (e: {
        assertion = config.components ? ${e.from} && config.components ? ${e.to};
        message = "edge ${e.from} -> ${e.to}: undeclared component";
      }) config.wiring)
      ++ (lib.mapAttrsToList (n: c: {
        assertion = lib.all (d: config.components ? ${d}) c.dependencies;
        message = "component ${n}: unresolved dependency";
      }) config.components)
      # universal core: at least one of retrieve | answer somewhere
      ++ [{
        assertion = lib.any (c: lib.any (cap: cap == "retrieve" || cap == "answer")
          c.capabilities) (lib.attrValues config.components);
        message = "wiring provides neither retrieve nor answer";
      }];
  };
}
