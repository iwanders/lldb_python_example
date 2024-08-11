
from .exception import LLDBError

import json
import lldb


def json_provider(self):
    stream = lldb.SBStream()
    self.GetAsJSON(stream)
    zz = json.loads(stream.GetData())
    return zz
lldb.SBStructuredData.json = json_provider

def commandrunner(self, args):
    ci = self.GetCommandInterpreter()
    res = lldb.SBCommandReturnObject()
    invocation = ci.HandleCommand(args, res)
    if res.Succeeded():
        return res
    else:
        raise LLDBError(f"Failed to evaluate {args}: {res.GetError()}")

lldb.SBDebugger.cmd = commandrunner


def event_string(z):
    stream = lldb.SBStream()
    z.GetDescription(stream)
    return "[" + stream.GetData() + "]"

lldb.SBEvent.__str__ = event_string


def breakpoint_by_address(self, addr):
    res = self.BreakpointCreateByAddress(addr)
    if not res:
        raise LLDBError(f"Failed to make breakpoint at 0x{addr:0>8x}")
    return res

lldb.SBTarget.breakpoint_by_address = breakpoint_by_address

def watchpoint_by_address(self, addr, size, read=False, write=True):
    #WatchAddress(self, *args)
    #WatchAddress(SBTarget self, lldb::addr_t addr, size_t size, bool read, bool write, SBError error) -> SBWatchpoint
    error = lldb.SBError()
    res = self.WatchAddress(addr, size, read, write, error)
    if not res or not error.Success():
        raise LLDBError(f"Failed to make watchpoint at 0x{addr:0>8x}")
    # Silence the default old value new value printing...
    # No-go... it's hardcoded atm; https://github.com/llvm/llvm-project/blob/5286656609418c766272ff78e62fda41671ef4cb/lldb/source/Target/StopInfo.cpp#L1001
    """
    print("Trying to silence old new value printing...")
    zzz = lldb.SBCommandReturnObject()
    deb = self.GetDebugger();
    deb.SetSelectedTarget(self)
    z = deb.GetCommandInterpreter().HandleCommand("watchpoint command add -s python -o '' %s" % res.GetID(), zzz)
    print(f"Res: {z}  {zzz}")
    """
    return res

lldb.SBTarget.watchpoint_by_address = watchpoint_by_address

