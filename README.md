# LLDB python example


Example on how to interact with lldb through the API. Used ~lldb-13~ lldb-15.

Setting breakpoints and extracting information when the process halts.

Just some notes for future me.

Import some shared object into current target to obtain it's debug symbols (for types)
```
target modules add <shared_object_path> --symfile <shared_object_path>
target modules load --file <shared_object_path> .text <some_unused_adress_to_map_to>
```

## Usage
```
nix develop
```
