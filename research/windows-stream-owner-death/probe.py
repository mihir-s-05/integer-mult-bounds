"""Source-bound, native owner-death observations for PR5463's stream adapter.

Mihir Srivastava with substantial OpenAI Codex assistance; Apache-2.0.
The unchanged adapter and gate retain ywz65 and their successor authors' credit.
Only the two explicitly named counterfactuals alter a native operation.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
CASES = ("before-event-open", "before-assign", "before-release", "running",
         "live-owner", "early-release-control", "no-kill-control")


class AuditFailure(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise AuditFailure(message)


def publish(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(path)


def wait_file(path, seconds=15):
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise AuditFailure("timed out awaiting " + path.name)
        time.sleep(0.01)
    return json.loads(path.read_bytes())


def load_sources():
    manifest = json.loads((PACKAGE / "SOURCES.json").read_bytes())
    rows = {row["path"]: row for row in manifest["files"]}
    paths = {
        "reader": (ROOT / "scripts/research_package.py", rows["scripts/research_package.py"]),
        "adapter": (PACKAGE / "vendor/owned_pipe.py",
                    manifest["vendored_predecessor"]),
    }
    modules, hashes = {}, {}
    for name, (path, row) in paths.items():
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(digest == row["sha256"], "source hash mismatch: " + name)
        if name == "adapter":
            blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            require(blob == row["git_blob"], "vendored Git blob mismatch")
        module = types.ModuleType("owner_audit_" + name)
        module.__file__ = str(path)
        exec(compile(data, str(path), "exec"), module.__dict__)
        modules[name], hashes[name] = module, digest
    return modules, hashes


class Hook:
    """Keep ctypes signature assignment on the original function."""
    def __init__(self, function, callback):
        object.__setattr__(self, "function", function)
        object.__setattr__(self, "callback", callback)

    def __getattr__(self, name):
        return getattr(self.function, name)

    def __setattr__(self, name, value):
        setattr(self.function, name, value)

    def __call__(self, *args):
        return self.callback(self.function, *args)


class Proxy:
    def __init__(self, api, hooks):
        self.api, self.hooks = api, hooks
        self.cache = {}

    def __getattr__(self, name):
        if name not in self.cache:
            function = getattr(self.api, name)
            self.cache[name] = Hook(function, self.hooks[name]) if name in self.hooks else function
        return self.cache[name]


def patch_kernel(module, hooks):
    real = ctypes.WinDLL
    facade = types.SimpleNamespace(**{name: getattr(ctypes, name) for name in dir(ctypes)})
    facade.WinDLL = lambda *a, **k: Proxy(real(*a, **k), hooks)
    module.ctypes = facade
    return facade


def python_command(*arguments, isolated_site=False):
    flags = ["-I", "-B"] + (["-O"] if sys.flags.optimize else [])
    if isolated_site:
        flags.append("-S")
    return [sys.executable, *flags, str(Path(__file__).resolve()), *map(str, arguments)]


def child_mode(mode, directory, *arguments):
    directory = Path(directory)
    case = directory.name
    if mode == "leaf":
        publish(directory / "leaf.json", {"pid": os.getpid()})
        while True:
            time.sleep(1)
    if mode == "target":
        leaf = subprocess.Popen(python_command("leaf", directory), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_file(directory / "leaf.json")
        publish(directory / "target.json", {"pid": os.getpid(), "leaf": leaf.pid})
        leaf.wait()
        return

    modules, _ = load_sources()
    reader, adapter = modules["reader"], modules["adapter"]
    if mode == "gate":
        event, argv = arguments

        def before_open(function, *args):
            if case == "before-event-open":
                publish(directory / "gate-before-open.json", {"pid": os.getpid()})
                wait_file(directory / "allow-open.json")
            return function(*args)

        def before_wait(function, *args):
            require(args[1] == 30000, "original gate timeout changed")
            publish(directory / "gate-wait.json", {"pid": os.getpid(), "timeout_ms": args[1]})
            result = function(*args)
            publish(directory / "gate-wait-result.json", {"result": result})
            return result

        # Imports in the unchanged gate resolve to this facade, with original
        # native functions and arguments (apart from observation-only callbacks).
        facade = patch_kernel(adapter, {"OpenEventW": before_open,
                                       "WaitForSingleObject": before_wait})
        sys.modules["ctypes"] = facade
        sys.argv = ["-c", event, argv]
        try:
            exec(compile(reader._WINDOWS_GATE, "<unchanged-WINDOWS_GATE>", "exec"),
                 {"__name__": "__main__"})
        except BaseException as exc:
            publish(directory / "gate-outcome.json", {"type": type(exc).__name__,
                    "winerror": getattr(exc, "winerror", None), "message": str(exc)})
            raise
        return

    require(mode == "owner", "unknown worker mode")
    real_popen = adapter.REAL_POPEN
    native = Native()
    state = {}

    def launch_gate(argv, **kwargs):
        require(argv[:4] == [sys.executable, "-I", "-S", "-c"]
                and argv[4] == reader._WINDOWS_GATE, "unexpected predecessor gate invocation")
        process = real_popen(python_command("gate", directory, *argv[5:], isolated_site=True), **kwargs)
        state["gate"] = process
        publish(directory / "gate.json", {"pid": process.pid})
        wait_file(directory / ("gate-before-open.json" if case == "before-event-open" else "gate-wait.json"))
        return process

    def create_event(function, *args):
        event = function(*args)
        state["event"] = event
        return event

    def cut(job, label):
        process = state["gate"]
        member = native.member(int(process._handle), job)
        publish(directory / "cut.json", {"owner": os.getpid(), "gate": process.pid,
                "gate_in_private_job": member, "cut": label})
        wait_file(directory / "continue.json", seconds=90)

    def assign(function, job, handle):
        state["job"] = job
        if case == "early-release-control":
            native.checked(native.set_event(state["event"]))
            wait_file(directory / "target.json")
            cut(job, "before-assign")
        elif case in ("before-event-open", "before-assign"):
            cut(job, "before-assign")
        return function(job, handle)

    def set_event(function, event):
        if case in ("before-release", "live-owner"):
            cut(state["job"], "before-release")
        return function(event)

    def limits(function, job, info_class, pointer, size):
        if case == "no-kill-control":
            require(info_class == 9 and pointer._obj.Basic.Flags == 0x2000,
                    "unexpected original job limits")
            pointer._obj.Basic.Flags = 0  # Deliberate counterfactual, never production.
        return function(job, info_class, pointer, size)

    adapter.REAL_POPEN = launch_gate
    patch_kernel(adapter, {"CreateEventW": create_event, "AssignProcessToJobObject": assign,
                           "SetEvent": set_event, "SetInformationJobObject": limits})
    with adapter.OwnedPopen(python_command("target", directory), reader._WINDOWS_GATE,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        target = wait_file(directory / "target.json")
        if case != "live-owner":
            cut(state["job"], "running")
        else:
            publish(directory / "running.json", target)
            wait_file(directory / "finish.json")
    publish(directory / "owner-complete.json", {"pid": os.getpid()})


class Native:
    def __init__(self):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)

        def function(name, result, *arguments):
            fn = getattr(self.api, name)
            fn.restype, fn.argtypes = result, arguments
            return fn

        h, b, d = wintypes.HANDLE, wintypes.BOOL, wintypes.DWORD
        self.open = function("OpenProcess", h, d, b, d)
        self.wait = function("WaitForSingleObject", d, h, d)
        self.kill = function("TerminateProcess", b, h, wintypes.UINT)
        self.close = function("CloseHandle", b, h)
        self.get_exit = function("GetExitCodeProcess", b, h, ctypes.POINTER(d))
        self.in_job = function("IsProcessInJob", b, h, h, ctypes.POINTER(b))
        self.set_event = function("SetEvent", b, h)

    def checked(self, result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    def acquire(self, pid):
        return self.checked(self.open(0x00100000 | 0x1000 | 1, False, pid))

    def alive(self, handle):
        result = self.wait(handle, 0)
        require(result in (0, 258), "invalid process wait result")
        return result == 258

    def exited(self, handle, seconds):
        return self.wait(handle, round(seconds * 1000)) == 0

    def exit_code(self, handle):
        value = wintypes.DWORD()
        self.checked(self.get_exit(handle, ctypes.byref(value)))
        return value.value

    def member(self, handle, job):
        value = wintypes.BOOL()
        self.checked(self.in_job(handle, job, ctypes.byref(value)))
        return bool(value.value)


def validate_observation(case, observation):
    """Production acceptance predicates also reject both deliberate mutants."""
    require(not observation["alive_after"]["owner"], "owner has not completed")
    require(observation["target_marker_after"] == observation["target_started"],
            "target appeared after the recorded cut")
    if case in ("before-event-open", "before-assign", "early-release-control"):
        require(not observation["gate_in_private_job"], "pre-assignment cut was already owned")
        require(not observation["target_started"], "requested command ran before ownership")
        require(not observation["alive_after"]["gate"], "unassigned gate did not retire")
    else:
        require(observation["gate_in_private_job"], "post-assignment gate was not owned")
        require(not any(observation["alive_after"].values()), "owned process survived owner completion")


def one_case(case, root):
    directory = root / case
    directory.mkdir()
    native, handles = Native(), {}
    result = None
    with (directory / "owner.stderr").open("wb") as errors:
        owner = subprocess.Popen(python_command("owner", directory), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=errors)
        try:
            handles["owner"] = native.acquire(owner.pid)
            cut = wait_file(directory / "cut.json")
            require(cut["owner"] == owner.pid, "owner identity mismatch")
            handles["gate"] = native.acquire(cut["gate"])
            require(all(native.alive(h) for h in handles.values()), "cut process already exited")
            before = {}
            if case == "live-owner":
                time.sleep(0.3)
                require(not (directory / "target.json").exists(), "closed live-owner gate spawned")
                require(all(native.alive(h) for h in handles.values()), "live control died before release")
                before["closed_gate_observation_seconds"] = 0.3
                publish(directory / "continue.json", {})
                wait_file(directory / "running.json")
            if (directory / "target.json").exists():
                target = wait_file(directory / "target.json")
                handles["target"] = native.acquire(target["pid"])
                handles["leaf"] = native.acquire(target["leaf"])
                require(all(native.alive(h) for h in handles.values()), "target cut was not live")
            target_started = "target" in handles
            require(target_started == (case in ("running", "live-owner", "early-release-control", "no-kill-control")),
                    "unexpected target readiness at cut")
            started = time.monotonic()
            if case == "live-owner":
                publish(directory / "finish.json", {})
            else:
                # Abrupt native termination: no Python finally/context cleanup runs.
                native.checked(native.kill(handles["owner"], 91))
            require(native.exited(handles["owner"], 15), "owner did not terminate")
            if case == "before-event-open":
                publish(directory / "allow-open.json", {})
            if case == "before-assign":
                before["gate_alive_after_owner_death"] = native.alive(handles["gate"])
                require(before["gate_alive_after_owner_death"], "gate did not retain its open event")
                require(native.exited(handles["gate"], 40), "original 30-second gate did not retire")
            elif case in ("early-release-control", "no-kill-control"):
                time.sleep(0.3)
            else:
                for name, handle in handles.items():
                    require(native.exited(handle, 10), "process did not stop: " + name)
            result = {"case": case, "cut": cut["cut"], "gate_in_private_job": cut["gate_in_private_job"],
                      "target_started": target_started,
                      "target_marker_after": (directory / "target.json").exists(),
                      "alive_after": {name: native.alive(h) for name, h in handles.items()},
                      "exit_codes": {name: native.exit_code(h) for name, h in handles.items()},
                      "observation_before_fixture_teardown": True,
                      "observation_seconds": round(time.monotonic() - started, 3), **before}
            if case == "before-event-open":
                result["gate_outcome"] = wait_file(directory / "gate-outcome.json")
                require(result["gate_outcome"]["winerror"] == 2, "expected missing event after owner death")
            elif case == "before-assign":
                result["gate_outcome"] = wait_file(directory / "gate-outcome.json")
                result["gate_wait_result"] = wait_file(directory / "gate-wait-result.json")["result"]
                require(result["gate_wait_result"] == 258
                        and result["gate_outcome"]["type"] == "RuntimeError"
                        and result["gate_outcome"]["message"] == "replay ownership gate was not released",
                        "gate did not exit through its unchanged timeout guard")
            if not target_started:
                require(not result["target_marker_after"], "target started after the owner died")
            try:
                validate_observation(case, result)
            except AuditFailure as exc:
                if case not in ("early-release-control", "no-kill-control"):
                    raise
                result["counterfactual_rejected"] = str(exc)
            else:
                require(case not in ("early-release-control", "no-kill-control"),
                        "acceptance predicates missed a deliberate counterfactual")
        finally:
            # Observations above, cleanup below. Never credit these kills to the adapter.
            # Recover already published identities if a readiness assertion failed.
            for name, filename, key in (("gate", "gate.json", "pid"),
                                       ("target", "target.json", "pid"),
                                       ("leaf", "leaf.json", "pid")):
                path = directory / filename
                if name not in handles and path.exists():
                    try:
                        handles[name] = native.acquire(json.loads(path.read_bytes())[key])
                    except OSError:
                        pass  # Exited before handle acquisition; outer guard remains.
            for name in ("owner", "gate", "target", "leaf"):
                handle = handles.get(name)
                if handle and native.alive(handle):
                    native.checked(native.kill(handle, 92))
            for handle in handles.values():
                require(native.exited(handle, 10), "fixture teardown failed")
                native.checked(native.close(handle))
            owner.wait(timeout=10)
    require(result is not None, "case produced no observation")
    result["teardown_all_retained_processes_stopped"] = True
    return result


def run():
    _, hashes = load_sources()
    require(os.name == "nt", "native Windows is required; no portable pass substitutes for this audit")
    with tempfile.TemporaryDirectory(prefix="stream-owner-death-") as temporary:
        observations = []
        for case in CASES:
            observations.append(one_case(case, Path(temporary)))
            print("PASS_CASE", case, flush=True)
    return {"schema": "windows-stream-owner-death/v1", "source_sha256": hashes,
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "platform": sys.platform, "windows_version": list(sys.getwindowsversion()),
            "python": sys.version, "optimized": sys.flags.optimize,
            "cases": observations, "status": "PASS_WINDOWS_STREAM_OWNER_DEATH"}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("owner", "gate", "target", "leaf"):
        child_mode(*sys.argv[1:])
    else:
        receipt = run()
        if len(sys.argv) == 3 and sys.argv[1] == "--receipt":
            Path(sys.argv[2]).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        else:
            require(len(sys.argv) == 1, "usage: probe.py [--receipt PATH]")
        print(receipt["status"], flush=True)
