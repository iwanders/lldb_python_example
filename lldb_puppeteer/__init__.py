
import lldb
from . import monkeypatch
from .exception import LLDBError
from .util import *
import time
import struct

# SBPlatform objects can be created and then used to connect to a remote platform which allows the SBPlatform to be used to get a list of the current processes on the remote host, attach to one of those processes, install programs on the remote system, attach and launch processes, and much more.
# https://lldb.llvm.org/python_reference/lldb.SBPlatform-class.html
# But searching 'process' or 'list' doesn't find any methods?
# Platform process list just doesn't exist in the api:
# ci = dbg.GetCommandInterpreter()
# res = lldb.SBCommandReturnObject()
# invocation = ci.HandleCommand("platform process list", res)
# print(res)
# https://github.com/llvm/llvm-project/blob/27e8c50a4c34c6124622c17202ffb5cc4d8d1ebd/lldb/source/Target/Platform.cpp#L983-L991
#  https://github.com/llvm/llvm-project/blob/27e8c50a4c34c6124622c17202ffb5cc4d8d1ebd/lldb/source/API/SBPlatform.cpp

# https://github.com/llvm-mirror/lldb/blob/master/examples/python/process_events.py
# This one also doesn't work.
# print(dbg.FindTargetWithProcessID(14214))

"""
    A helper class to make it easier to work with async lldb interaction.
"""
class Debugger:
    def __init__(self, async=True):
        self.dbg = lldb.SBDebugger.Create()
        self.dbg.SetAsync(async)
        self.remote = False

    def get_platforms(self):
        entries = []
        platforms = self.dbg.GetNumAvailablePlatforms()
        for i in range(platforms):
            s = self.dbg.GetAvailablePlatformInfoAtIndex(i)
            entries.append(s.json())
        return entries

    def set_platform(self, platform_name):
        if not platform_name in [z["name"] for z in self.get_platforms()]:
            raise LLDBError(f"Could not find {platform_name}.")
        self.dbg.SetCurrentPlatform(platform_name)


    def connect(self, host, port):
        self.remote = True
        options = lldb.SBPlatformConnectOptions(f"connect://{host}:{port}")
        active_p = self.dbg.GetSelectedPlatform()
        # print(active_p.GetName())
        if not active_p.ConnectRemote(options):
            raise LLDBError(f"Failed to connect.")

    def cmd(self, v):
        return self.dbg.cmd(v)

    def _attach_method(self, method):
        listener = self.dbg.GetListener()
        error = lldb.SBError()
        target = self.dbg.GetDummyTarget()
        process = method(target, listener, error)
        if not process:
            raise LLDBError("Failed to attach (wrong pid/name? or lldb-server address hardcoded? use "
                            " strace, stat(\"/usr/bin/lldb-server-13.0.1\", 0x7ffc2d2bd228) = -1 "
                            f"ENOENT (No such file or directory) ): {error}")
        event = lldb.SBEvent()
        if self.remote:
            res = listener.WaitForEvent(5, event)
            if not res:
                raise LLDBError(f"Failed to attach.")
        return Target(target), Process(process, listener)

    def attach_to_pid(self, pid):
        return self._attach_method(lambda t, l, e: t.AttachToProcessWithID(l, pid, e))

    def attach_to_name(self, name, wait_for=False):
        return self._attach_method(lambda t, l, e: t.AttachToProcessWithName(l, name, wait_for, e))

    def load_core_file(self, core_path):
        # target = self.dbg.GetDummyTarget()
        err = lldb.SBError()
        # process = target.LoadCore(core_path, err)
        target = self.dbg.CreateTarget(core_path)
        if not target:
            raise LLDBError(f"failed to create target: {err}")

        process = target.LoadCore(core_path, err)
        
        if not process:
            raise LLDBError(f"failed to load core: {err}")
        return Target(target), Process(process, None)
        

    def __str__(self):
        return f"<Debugger {str(self.dbg)}>"

    # Magic method to dispatch anything we don't provide to the debugger itself.
    def __getattr__(self, attr):
        if attr in self.__class__.__dict__:
            return getattr(self, attr)
        else:
            return getattr(self.dbg, attr)



# print('Event data flavor:', event.GetDataFlavor())
class Process:
    def __init__(self, process, listener):
        self.process = process
        self.listener = listener
        if (listener):
            self.start() # Kick it from the 'connected' state to something sane.

    def __str__(self):
        return f"<Process {str(self.process)}>"

    def _wait_on_event(self, action=""):
        event = lldb.SBEvent()
        res = self.listener.WaitForEvent(5, event)
        # print(f"Got {event} for action {action}")
        if not res:
            raise LLDBError(f"Failed awaiting event during action {action}.")

    def stop(self):
        # if self.state != "stopped":
        res = self.process.Stop()
        if not res:
            raise LLDBError(f"Failed to stop the process.")
        self._wait_on_event("stop")

    def start(self):
        if self.state == "running":
            return # nothing to do
        res = self.process.Continue()
        if not res:
            raise LLDBError(f"Failed to continue the process.")
        self._wait_on_event("continue")

    def resume(self):
        return self.start()

    def continue_until_event(self, timeout=1):
        self.start()

        # Now, go into a blocking loop until some event happens.
        event = lldb.SBEvent()
        res = self.listener.WaitForEvent(timeout, event)
        if not res:
            return None
        return event
            
    def __del__(self):
        # Trying to detach gracefully, else we take the attached process with us?
        # print("Shutdown, detaching")
        if self.process:
            self.process.Detach()

    @property
    def state(self):
        return state_type_to_str(self.process.GetState())

    def _wait_on_state(self, state, timeout = 15):
        s = time.time()
        current_state = self.state
        while not current_state == state:
            time.sleep(0.01)
            if time.time() - s > timeout:
                raise LLDBError(f"Timeout reached waiting for state {state}, last state was {current_state}.")
            current_state = self.state
                

    """
        Something to get a quick 'where are we'...
    """
    def print_bt(self):
        if self.listener and self.state != "stopped":
            self.stop()
            self._wait_on_state("stopped")

        # Now the process must be stopped.
        thread = self.process.GetThreadAtIndex (0)
        if not thread:
            print("No thread with index 0")
        print(thread)

        if len(thread.frames) == 0:
            print("No frame.")
            return
            
        for frame in thread.frames:
            print(frame)

    # Magic method to dispatch anything we don't provide to the debugger itself.
    def __getattr__(self, attr):
        if attr in self.__class__.__dict__:
            return getattr(self, attr)
        else:
            return getattr(self.process, attr)

    def loop_callback(self, f, duration=float("inf"), dt = 0):
        z = time.time()
        while (time.time() - z < duration):
            res = self.continue_until_event(dt)
            if res:
                f(process=self, event=res)
            self.start()

    def read_memory(self, size, offset):
        error = lldb.SBError()
        content = self.process.ReadMemory(offset, size, error)
        if not error.Success():
            raise LLDBError(f"Failed to read memory at 0x{offset:0>16x} of size 0x{size:0>16x}")
        return bytes(content)

    def unpack_from(self, spec, offset):
        size = struct.calcsize(spec)
        new_bytes = self.read_memory(size, offset)
        return struct.unpack(spec, new_bytes)

class Target:
    def __str__(self):
        return f"<Target {str(self.target)}>"

    def __init__(self, target):
        self.target = target

    def __getattr__(self, attr):
        if attr in self.__class__.__dict__:
            return getattr(self, attr)
        else:
            return getattr(self.target, attr)

