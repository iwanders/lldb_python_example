{
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-22.11"; 
    flake-utils.url = "github:numtide/flake-utils/v1.0.0";
  };

  description = "LLDB python environment";

  outputs = { self, nixpkgs, flake-utils }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      lldb_py_env = pkgs.symlinkJoin {
        name = "lldb_py";
        paths = [pkgs.lldb_15.lib pkgs.lldb_15.out pkgs.python3];
      };
    in {
      defaultPackage = lldb_py_env;
      devShell = pkgs.mkShellNoCC {
        buildInputs = [ lldb_py_env ];
        LLDB_DEBUGSERVER_PATH = "${lldb_py_env}/bin/lldb-server";
        debian_chroot="${lldb_py_env.name}";
      };
    });
}
