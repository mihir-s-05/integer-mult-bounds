#!/usr/bin/env python3
"""Opt-in native Windows audit of the pinned Git blob reader's pipe lifetime.

Prepared for Mihir Srivastava with substantial OpenAI Codex assistance.
Apache-2.0. Builds on JoyboyBrian's POSIX reader fixtures and ywz65's native
process-handle / Job Object controls. See README.md for scope and attribution.
"""
import argparse
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
import time
import types
from unittest.mock import patch

SOURCE_SHA256 = "84a45190a6a96c20993a0d4a1045fbf24de660d2e6fef8f8a447bb3d1aa78db6"
BASE = "32890bc5de034ab8fc93ac88ead7279a6a416d04"
RESPONSE_SECONDS = 0.5
OBSERVATION_SECONDS = 0.75
OUTER_SECONDS = 30
PAYLOAD = b"\0\xff\r\n"
SCRIPT = Path(__file__).resolve()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(path)


def wait_for(predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while not predicate():
        require(time.monotonic() < deadline, "fixture readiness/observation timed out")
        time.sleep(0.005)


def python_argv():
    return [sys.executable, "-I", "-B"] + (["-O"] if sys.flags.optimize else [])


def load_source(path):
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == SOURCE_SHA256,
            "source differs from the audited main; reassess instead of silently repinning")
    module = types.ModuleType("pinned_research_package")
    module.__file__ = str(path)
    # Execute the checked bytes directly: -B alone still permits reading .pyc.
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


class ProcessHandle:
    """Keep the native process object, avoiding a PID-reuse observation race."""

    def __init__(self, pid):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.api.WaitForSingleObject.restype = wintypes.DWORD
        self.api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.TerminateProcess.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        # SYNCHRONIZE plus PROCESS_TERMINATE, used only on this fixture's PIDs.
        self.handle = self.api.OpenProcess(0x00100001, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def alive(self):
        status = self.api.WaitForSingleObject(self.handle, 0)
        require(status in (0, 258), "native process observation failed")
        return status == 258

    def stop(self):
        if self.alive() and not self.api.TerminateProcess(self.handle, 1):
            error = ctypes.get_last_error()
            # A job may already have requested termination. Keep the actual
            # process handle and wait for completion instead of treating an
            # in-flight termination's AccessDenied as a surviving process.
            if self.api.WaitForSingleObject(self.handle, 5000) != 0:
                raise ctypes.WinError(error)
        require(self.api.WaitForSingleObject(self.handle, 5000) == 0,
                "fixture process did not stop")

    def close(self):
        require(self.api.CloseHandle(self.handle), "CloseHandle failed")


def holder(directory):
    write_json(directory / "holder.json", {"pid": os.getpid()})
    wait_for(lambda: (directory / "release").exists(), 60)


def leader(directory, phase, inheritance):
    child = None
    if inheritance != "direct":
        retain = inheritance == "retained"
        child = subprocess.Popen(
            python_argv() + [str(SCRIPT), "_holder", str(directory)],
            stdin=sys.stdin if retain else subprocess.DEVNULL,
            stdout=sys.stdout if retain else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        wait_for(lambda: (directory / "holder.json").exists())
    write_json(directory / "leader-ready.json", {"holder": child.pid if child else None})
    wait_for(lambda: (directory / "observed").exists())
    if phase != "write":
        while sys.stdin.buffer.read(1) not in (b"\0", b"\n", b""):
            pass
        reply = b"a" * 40 + b" blob 4\n" + PAYLOAD + b"\n"
        length = {"header": 0, "payload": len(reply) - 3,
                  "terminator": len(reply) - 1, "success": len(reply)}[phase]
        sys.stdout.buffer.write(reply[:length])
        sys.stdout.buffer.flush()
    if inheritance == "direct":
        wait_for(lambda: (directory / "release").exists(), 60)
    # Deliberately leave the ready ordinary child holding the selected handles.
    # os._exit avoids a fixture-only Popen ResourceWarning at normal interpreter exit.
    os._exit(0)


def worker(source, directory, phase, inheritance):
    package = load_source(source)
    package.GIT_BLOB_RESPONSE_TIMEOUT = RESPONSE_SECONDS
    real_popen, real_stop = subprocess.Popen, package._stop_git_blob_process
    children = []

    def start(argv, **kwargs):
        require(argv == ["git", "cat-file", "--batch", "-z"], "unexpected launch")
        process = real_popen(python_argv() + [str(SCRIPT), "_leader", str(directory),
                                            phase, inheritance], **kwargs)
        children.append(process)
        wait_for(lambda: (directory / "leader-ready.json").exists())
        ready = json.loads((directory / "leader-ready.json").read_text())
        write_json(directory / "ready.json", {"worker": os.getpid(),
                   "leader": process.pid, "holder": ready["holder"]})
        # The reader's timer starts only after all process handles are observed.
        wait_for(lambda: (directory / "observed").exists())
        return process

    def stop(process):
        real_stop(process)
        write_json(directory / "deadline.json", {
            "time": time.monotonic(), "leader_returncode": process.wait(timeout=2)})

    package._stop_git_blob_process = stop
    result = {}
    try:
        with patch.object(package.subprocess, "Popen", side_effect=start):
            request = "x" * 2_000_000 if phase == "write" else "HEAD:fixture"
            values = list(package.git_blobs(directory, [request]))
            result["exact_binary_reply"] = values == [("a" * 40, PAYLOAD)]
    except Exception as error:
        result["error"] = type(error).__name__
    result["launches"] = len(children)
    result["leader_returncodes"] = [child.poll() for child in children]
    write_json(directory / "result.json", result)
    # Do not let the outer job clean descendants before the audit observes them.
    wait_for(lambda: (directory / "finish").exists())


def exercise(package, source, phase, inheritance):
    outcome, errors, handles = [], [], {}
    with tempfile.TemporaryDirectory(prefix="git pipe lifetime ") as temporary:
        directory = Path(temporary)
        argv = python_argv() + [str(SCRIPT), "_worker", str(source), temporary,
                                phase, inheritance]

        def guarded():
            try:
                outcome.append(package.run_windows_command(
                    argv, directory, OUTER_SECONDS, os.environ.copy()))
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=guarded)
        thread.start()
        try:
            wait_for(lambda: (directory / "ready.json").exists() or not thread.is_alive())
            require((directory / "ready.json").exists(), "worker failed before readiness")
            ready = json.loads((directory / "ready.json").read_text())
            for role, pid in ready.items():
                if pid is not None:
                    handles[role] = ProcessHandle(pid)
            require(all(handle.alive() for handle in handles.values()),
                    "fixture did not reach the live, observed boundary")
            (directory / "observed").touch()
            blocked = inheritance == "retained" and phase != "success"
            if blocked:
                wait_for(lambda: (directory / "deadline.json").exists()
                         or (directory / "result.json").exists())
                require((directory / "deadline.json").exists(),
                        "reader completed before the expected deadline observation")
                deadline = json.loads((directory / "deadline.json").read_text())
                time.sleep(OBSERVATION_SECONDS)
                post_deadline = time.monotonic() - deadline["time"]
                require(not (directory / "result.json").exists(),
                        "pinned reader no longer has the expected held-pipe limitation")
                require(deadline["leader_returncode"] == 0,
                        "leader did not exit normally before the deadline")
                result = {"blocked_after_deadline": True,
                          "observed_seconds_after_stop": round(post_deadline, 6)}
            else:
                wait_for(lambda: (directory / "result.json").exists())
                result = json.loads((directory / "result.json").read_text())
                expected = ({"exact_binary_reply": True} if phase == "success" else
                            {"error": "TimeoutExpired" if inheritance == "direct" else "ValueError"})
                require(all(result.get(k) == v for k, v in expected.items()),
                        "unexpected control result: " + repr(result))
                require(result["launches"] == 1, "unexpected protocol retry")
            before = {role: handle.alive() for role, handle in handles.items()}
            require(before["worker"] and not before["leader"], "incorrect leader/worker lifetime")
            if "holder" in before:
                require(before["holder"], "holder stopped before audit observation")
            receipt = {"phase": phase, "inheritance": inheritance,
                       "ready_before_request": True, "before_teardown_alive": before,
                       "reader": result}
            # All scientific/behavioral observations above precede any teardown.
            if blocked:
                handles["worker"].stop()
            else:
                (directory / "finish").touch()
            thread.join(OUTER_SECONDS + 12)
            require(not thread.is_alive(), "outer job did not finish")
            require(not errors, "outer job failed: " + repr(errors))
            require(outcome == [1 if blocked else 0], "unexpected guarded worker status")
            wait_for(lambda: not any(handle.alive() for handle in handles.values()), 5)
            after = {role: handle.alive() for role, handle in handles.items()}
            require(not any(after.values()), "owned fixture survived outer job cleanup")
            receipt["after_outer_job_alive"] = after
            receipt["worker_finish"] = "observer termination" if blocked else "normal release"
            return receipt
        finally:
            # Last-resort fixture teardown is never counted as a passing observation.
            (directory / "finish").touch()
            (directory / "release").touch()
            try:
                for handle in handles.values():
                    handle.stop()
                thread.join(OUTER_SECONDS + 12)
                require(not thread.is_alive(), "outer cleanup thread survived final teardown")
            finally:
                for handle in handles.values():
                    handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=SCRIPT.parents[3] / "scripts/research_package.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(os.name == "nt", "native Windows is required; this is not a portable replay")
    source = args.source.resolve()
    package = load_source(source)
    cases = [(phase, inheritance) for phase in ("header", "payload", "terminator", "write")
             for inheritance in ("retained", "redirected")]
    cases += [("header", "direct"), ("success", "retained")]
    receipts = []
    for phase, inheritance in cases:
        receipts.append(exercise(package, source, phase, inheritance))
        print("CHECK", phase, inheritance, flush=True)
    write_json(args.output, {
        "status": "CONFIRMED_PINNED_WINDOWS_READER_LIMITATION",
        "base": BASE, "source_sha256": SOURCE_SHA256,
        "probe_sha256": sha256(SCRIPT.read_bytes()).hexdigest(),
        "python": sys.version, "platform": platform.platform(),
        "optimized": sys.flags.optimize, "response_seconds": RESPONSE_SECONDS,
        "post_stop_observation_seconds": OBSERVATION_SECONDS,
        "outer_guard_seconds": OUTER_SECONDS, "cases": receipts,
        "scope": "Controlled Python subprocesses replace Git; outer job cleanup is not reader cleanup."})
    print("CONFIRMED_PINNED_WINDOWS_READER_LIMITATION cases=10", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_holder":
        holder(Path(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "_leader":
        leader(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif len(sys.argv) > 1 and sys.argv[1] == "_worker":
        worker(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5])
    else:
        main()
