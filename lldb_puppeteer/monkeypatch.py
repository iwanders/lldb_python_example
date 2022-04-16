
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