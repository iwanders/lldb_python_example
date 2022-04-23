#!/usr/bin/env python3

import sys
sys.path.insert(0, "/usr/lib/llvm-13/lib/python3/dist-packages")


import time
import sys
import argparse
import struct

import lldb
import lldb_utils

# Wrapped debugger
dbg = lldb_utils.Debugger()




# Some global lookups to handle breakpoints later.
breakpoints = {}
handlers = {}

def track_going_into_function(process):
    frame = process.threads[0].frame[0]

    # Read registers
    size = frame.register["edx"]
    esp = frame.register["esp"]

    # Interpret values like so:
    size = size.unsigned

    # Obtain an integer 4 bytes above the stack pointer.
    path = frame.EvaluateExpression("(((uint32_t*)$esp)[1])")

    # Read c string from memory, with max size.
    error = lldb.SBError()
    path = frame.thread.process.ReadCStringFromMemory(path.unsigned, 64, error);

    # Read arbitrary memory:
    content = process.ReadMemory(esp.unsigned + 8, 4, error)
    if not error.Success():
        print(f"Failed to read memory at 0x{ptr:0>8x} of 0x{size:0>8x}")
    new_bytes = bytearray(content)
    linenr = struct.unpack("<I", new_bytes)[0]

    # Or use unpack_from on the process.
    line_nr_alternate = process.unpack_from("<I", esp.unsigned + 8)[0]

        # Print some things.
    print("---")
    print(f"Size 0x{size:>X}")
    print(f"  from {path}:{linenr}")
    print(f"  {line_nr_alternate}")

    # Enable a one-shot breakpoint to catch the return of the function.
    process.target.breakpoint_by_address(breakpoints["track_return_from_function"][0]).SetOneShot(True)

def track_return_from_function(process):
    frame = process.threads[0].frame[0]

    # More evaluations!
    path = frame.EvaluateExpression("(((uint32_t*)$esp)[3])")
    linenr = frame.GetValueForVariablePath("(((uint32_t*)$esp)[4])")
    err = lldb.SBError()
    path = frame.thread.process.ReadCStringFromMemory(path.unsigned, 64, err);

    ptr = frame.register["eax"].unsigned
    print(f"-> 0x{ptr:>X}  ({path}:{linenr.unsigned})")



def get_target_process():
    usecore = False

    if usecore:
        target, process = dbg.load_core_file("/tmp/my_core.bin")
        memory_allocation_handler(process)
        print(process)
        sys.exit(1)
    else:
        target, process = dbg.attach_to_name("wine")

    return target, process



# Loop to call a handler on process stop.
def breakpoint_handle_loop(target, process, save_on_exit=False):
    def handler(process, event):
        pc = process.threads[0].frame[0].pc
        if pc in handlers:
            handlers[pc](process)

    try:
        process.loop_callback(handler)
    except KeyboardInterrupt:
        pass

    if save_on_exit:
        print("Exiting, trying to do things")
        process.stop()
        time.sleep(5)


def run_track_things(args):
    # Create the target and process
    target, process = get_target_process()

    # Map of breakpoints to use
    breakpoints["track_going_into_function"] = (0x6ff6cd50, track_going_into_function, True, True)
    breakpoints["track_return_from_function"] = (0x6ff6cd8a, track_return_from_function, False, None)

    for name, (addr, f, create, enable) in breakpoints.items():
        handlers[addr] = f
        if create:
            bp = target.breakpoint_by_address(addr)
            bp.SetEnabled(enable)

    # Go into the loop
    breakpoint_handle_loop(target, process, save_on_exit=True)


#https://stackoverflow.com/a/312464
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def as_hex(z):
    return " ".join(f"{v:0>2X}" for v in z)

# Dump a block of memory in 4 byte chunks and interpret them as signed and unsigned 32 bit integers.
def hexdump(d):
    rows = []
    for i, chunk in enumerate(chunks(d, 4)):
        offset = i * 4
        row = []
        row.append(f'#{i*4:0>8X}    ')

        if len(chunk) != 4:
            row.append(as_hex(chunk))
        else:
            row.append(as_hex(chunk))
            unsigned = struct.unpack("<I", chunk)[0]
            signed = struct.unpack("<i", chunk)[0]
            row.append(f'{signed: >20}')
            row.append(f'{unsigned: >20}')

        rows.append(row)

    s = ""
    for r in rows:
        s += "".join(r)
        s += "\n"
    print(s)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")

    track_things_parser = subparsers.add_parser("track_things", help="Track things.")
    track_things_parser.set_defaults(func=run_track_things)

    args = parser.parse_args()


    # no command
    if (args.command is None):
        parser.print_help()
        parser.exit()
        sys.exit(1)

    args.func(args)
    sys.exit()

