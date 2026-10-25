"""Opt-in Windows stream lifetime for the source-pinned Git-reader experiment.

The native structures, gate and ownership protocol are adapted from ywz65's
run_windows_command in the frozen research_package.py. Its notice and exact
source are retained beside this module. Streaming interface by Mihir Srivastava
with substantial OpenAI Codex assistance; Apache-2.0.
"""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import threading
import time
import uuid

REAL_POPEN = subprocess.Popen


@contextmanager
def windows_pipe(argv, gate, **kwargs):
    """Yield a gated process and an idempotent, thread-safe whole-job stop.

    Only the job handle owner may release the gate. The requested command's
    stdin/stdout are inherited through the gate without Python-level copying.
    """
    class BasicLimits(ctypes.Structure):
        _fields_ = [("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64),
                    ("Flags", wintypes.DWORD), ("MinWorkingSet", ctypes.c_size_t),
                    ("MaxWorkingSet", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD),
                    ("Scheduling", wintypes.DWORD)]

    class IOCounts(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("Basic", BasicLimits), ("IO", IOCounts),
                    ("ProcessMemory", ctypes.c_size_t), ("JobMemory", ctypes.c_size_t),
                    ("PeakProcessMemory", ctypes.c_size_t), ("PeakJobMemory", ctypes.c_size_t)]

    class Accounting(ctypes.Structure):
        _fields_ = [(name, ctypes.c_int64) for name in
                    ("UserTime", "KernelTime", "PeriodUserTime", "PeriodKernelTime")] + [
                    (name, wintypes.DWORD) for name in
                    ("PageFaults", "TotalProcesses", "ActiveProcesses", "TerminatedProcesses")]

    api = ctypes.WinDLL("kernel32", use_last_error=True)

    def native(name, result, *arguments):
        fn = getattr(api, name)
        fn.restype, fn.argtypes = result, arguments
        return fn

    handle, dword, boolean = wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL
    create_job = native("CreateJobObjectW", handle, ctypes.c_void_p, wintypes.LPCWSTR)
    set_info = native("SetInformationJobObject", boolean, handle, ctypes.c_int, ctypes.c_void_p, dword)
    assign = native("AssignProcessToJobObject", boolean, handle, handle)
    terminate = native("TerminateJobObject", boolean, handle, wintypes.UINT)
    query = native("QueryInformationJobObject", boolean, handle, ctypes.c_int,
                   ctypes.c_void_p, dword, ctypes.c_void_p)
    create_event = native("CreateEventW", handle, ctypes.c_void_p, boolean, boolean, wintypes.LPCWSTR)
    set_event = native("SetEvent", boolean, handle)
    close = native("CloseHandle", boolean, handle)

    def checked(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return ok

    job = checked(create_job(None, None))
    event, process, assigned = None, None, False
    stopped = False
    lock = threading.Lock()

    def stop():
        nonlocal stopped
        with lock:
            if stopped:
                return
            checked(terminate(job, 1))
            deadline = time.monotonic() + 10
            while True:
                state = Accounting()
                checked(query(job, 1, ctypes.byref(state), ctypes.sizeof(state), None))
                if not state.ActiveProcesses:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("owned Git process cleanup timed out")
                time.sleep(0.01)
            stopped = True

    try:
        limits = ExtendedLimits()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        checked(set_info(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        name = "Local\\research-git-stream-" + uuid.uuid4().hex
        event = checked(create_event(None, True, False, name))
        if ctypes.get_last_error() == 183:
            raise ValueError("Git ownership gate name already exists")
        process = REAL_POPEN([sys.executable, "-I", "-S", "-c", gate, name,
                              json.dumps(argv, ensure_ascii=False)], **kwargs)
        checked(assign(job, int(process._handle)))
        assigned = True
        checked(set_event(event))
        yield process, stop
    finally:
        try:
            if process is not None:
                if assigned:
                    stop()
                elif process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        finally:
            try:
                if process is not None:
                    # In the actual reader these are already closed. Setup
                    # failure can reach here before the reader owns any streams.
                    for stream in (process.stdin, process.stdout, process.stderr):
                        if stream is not None:
                            stream.close()
            finally:
                try:
                    if event:
                        checked(close(event))
                finally:
                    checked(close(job))


class OwnedPopen:
    """The Popen subset used by the frozen reader, with job-aware kill/exit.

    This is an experimental reader adapter, not a general subprocess replacement.
    The caller must use the context manager, as the actual reader does.
    """
    def __init__(self, argv, gate, **kwargs):
        self.context = windows_pipe(argv, gate, **kwargs)
        self.process, self.stop = self.context.__enter__()

    def __getattr__(self, name):
        return getattr(self.process, name)

    def kill(self):
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.context.__exit__(*exception)
