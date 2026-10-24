# Native Windows Git blob pipe-lifetime audit

The shared Git blob reader at canonical main
`32890bc5de034ab8fc93ac88ead7279a6a416d04` can remain blocked after its response
deadline fires on native Windows. A ready ordinary descendant retains a pipe
after the direct child exits. The reader's Windows stop operation only kills
that direct child. This audit supplies a bounded reproducer for the explicitly
unverified boundary left by [PR #5185](https://github.com/CrocSwap/integer-mult-bounds/pull/5185)
and [PR #5358](https://github.com/CrocSwap/integer-mult-bounds/pull/5358).

The result is tooling evidence with a controlled Python process standing in for
`git cat-file`. It does not demonstrate an actual Git/promisor-helper hang.
Production code, frozen inputs and the selected conditional result are unchanged.

## Observed boundary

The probe sets the response interval to 0.5 seconds **after readiness**. In each
held-pipe case it observes the completed stop callback, confirms the direct
child's exit code is zero, then waits another 0.75 seconds. The worker and holder
are still alive and the reader has not returned. This is a measured finite
failure of the configured response deadline, not a wall-clock timing guarantee
for arbitrary hosts or an empirical claim of an infinite hang.

| Fixture | Reader result before teardown | Ordinary descendant |
| --- | --- | --- |
| Inherited stdout, no response header | Still blocked after stop callback | Alive |
| Inherited stdout, only two of four payload bytes | Still blocked after stop callback | Alive |
| Inherited stdout, omitted final newline | Still blocked after stop callback | Alive |
| Inherited stdin, 2,000,000-character request | Still blocked after stop callback | Alive |
| Same four leaders, descendant stdin/stdout redirected to `DEVNULL` | `ValueError`, one launch, leader exit zero | Alive, holding neither source pipe |
| No descendant; direct child itself stalls | `TimeoutExpired`, one launch | Absent |
| Full valid response with an inheriting descendant | Exact OID and `00 ff 0d 0a` bytes returned | Alive |

Redirecting the handles changes the blocked result while retaining the ordinary
descendant and leader behavior. The direct-child control checks the existing
deadline's intended scope. Successful binary transport does not establish
descendant cleanup. All conditions use explicit exceptions and remain active
when Python assertions are disabled.

## Observation and containment

`probe.py` loads the SHA256-authenticated source bytes directly with `compile`
and `exec`, avoiding source-adjacent bytecode. Only the worker's `Popen` for the
exact NUL batch command is replaced with a real Python leader. The leader starts
a real holder with explicit inherited or redirected standard handles. Every
process is alive and represented by a retained native handle before the observer
releases the readiness gate. This avoids mistaking missing readiness or PID reuse
for a lifetime result. Header and payload processing still use the unchanged
reader.

The timeout observer calls the original stop function before recording its
completion. A normal leader exit is checked both through the retained process
handle and through its `Popen` exit status. Completed reader cases pause after
writing their result so teardown cannot conceal a surviving holder. The blocked
cases are stopped by the observer only **after** the failure observation.

The existing `run_windows_command` Job Object owns the whole fixture from before
the worker starts, with a separate 30-second outer guard. After observing the
failure, the observer terminates the blocked worker; the job then stops its
remaining descendants. Successful/control workers are released normally. Every
retained process handle must signal termination before the case passes. A final
fallback teardown is outside the evidence path and cannot turn a failed
observation into a pass. The outer job's cleanup is never attributed to the blob
reader, and the probe does not wait for that outer deadline in its passing cases.

Windows termination is asynchronous; the native process handle is the completion
check. See Microsoft's [TerminateProcess contract](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess)
and [TerminateJobObject contract](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject).
The implementation follows the retained handle-observation practice in
`tests/test_research_windows_job.py`.

## Sources and reproduction

The sole executable repository input is `scripts/research_package.py`:

- Base commit: `32890bc5de034ab8fc93ac88ead7279a6a416d04`.
- Git blob: `48fe9feb4699c09e95505d95c327ea998ac8b3a7`.
- SHA256: `84a45190a6a96c20993a0d4a1045fbf24de660d2e6fef8f8a447bb3d1aa78db6`.

The probe fails before launching fixtures if these source bytes change. Future
reader repairs require a reassessed probe and expectations; this is a historical
audit, not a test requiring future production code to preserve the limitation.

Run from the repository root on native Windows with Python 3.12:

```powershell
python -W error -B docs/research/windows-git-pipe-audit/probe.py --output normal.json
python -O -W error -B docs/research/windows-git-pipe-audit/probe.py --output optimized.json
```

The expected terminal status is
`CONFIRMED_PINNED_WINDOWS_READER_LIMITATION cases=10`. A success here confirms
the scoped limitation and its controls. It is not a production repair.
Each JSON receipt records all ten cases, the probe/source hashes, interpreter,
platform, optimization setting and both sides of teardown. Timing fields are
measurements, so regenerated receipts need not be byte-identical.

To replay without a repository or Git, copy `probe.py` and the exact pinned
`scripts/research_package.py` into a temporary directory, and pass the source
explicitly:

```powershell
python -I -O -W error -B probe.py --source research_package.py --output result.json
```

This opt-in native Windows audit has no generic Linux `VERIFY.json` registration.
It neither skips the native experiment and calls that success nor starts Windows
process experiments in ordinary documentation CI.

## Validation

Local environment: Windows 11 build 26300, CPython 3.12.0 x64. The final receipt
files accompany this note. Normal and optimized runs are reported separately;
no hosted native Windows execution or independent human acceptance is claimed.

| Run | Evidence |
| --- | --- |
| [Normal Python](NORMAL.json) | All ten cases confirm their stated outcomes and complete outer-job teardown. |
| [Optimized Python](OPTIMIZED.json) | The same ten cases pass with `-O` propagated through the worker, leader and holder. |
| [Closed snapshot, optimized](CLOSED-SNAPSHOT.json) | The same ten cases pass from just the probe and pinned reader, with no `.git` and an empty `PATH`. |
| [Snapshot and rejection checks](VALIDATION.json) | Both snapshot files and their inventory are unchanged afterward. An appended comment in a copied reader rejects with exit 1 before any observation output or receipt. |

The closed-snapshot run and source-drift control together took 59.938 seconds on
this host. The JSON receipts retain every generated field and are indented for
review; timings are not normalized or excluded. These are direct native checks,
not a registered package replay. The current selected metadata baseline is a
separate orientation check and provides no mathematical evidence for this result.

The first fixture revision detected the held-pipe behavior but checked handles
too soon after asynchronous job termination. Its teardown failed and is not
counted as a complete pass. An initial optimized run also failed its eight-second
startup gate during concurrent checkout work; the final gate allows 20 seconds
for readiness while retaining the same 0.5-second measured response interval.
Neither unsuccessful attempt produced the retained success receipt.

## Task, overlap and attribution

Task `portable-replay`, priority revision 7. Scope is **changed** from the card's
canonical-payload comparison to the explicit native Windows source-reader
handoff. Portable independent verification depends on both exact source bytes
and a source reader that terminates. The session stops at the ready-descendant
fixture and precise production-repair handoff; it does not reserve that repair.
The [canonical claim and result](https://github.com/CrocSwap/integer-mult-bounds/discussions/4681#discussioncomment-19170424)
retain coordination history.

Initial overlap covered 331 open PR bodies and 4,726 Discussion records with
complete remote pagination. The #4681 handoffs, #5358, #5185 and native Windows
job tests were read. Local note coverage was initially sparse and was expanded
before the final check. Search coverage is evidence about the inspected corpus,
not a novelty guarantee or a search of every historical diff.

Brian / JoyboyBrian supplies #4738's response deadlines and #5185's POSIX
descendant fixtures; this audit retains that failure-model lineage. Nick
Petalas supplies the #2752 fallback. Mihir Srivastava's #4686/#5358 provide the
Windows closed-pipe and installed-Git evidence. ywz65 supplies the native process
handle and Job Object controls reused as the outer containment/observation
pattern; Paul Romeo supplies their POSIX counterpart. Douglas Colkitt, Woklerx,
Arham Tahir and the retained source-reader contributors keep their original
credit. Prepared for Mihir Srivastava with substantial OpenAI Codex assistance,
one agent. New work is Apache-2.0.

## Open next questions

The next useful step is a Windows ownership boundary around the **streaming Git
reader**, established before its child can spawn descendants. A candidate must
release retained pipes on timeout, malformed response, successful exhaustion
and early generator close, while preserving one-blob streaming, exact bytes,
the first-request/no-response/exit-129 fallback and pauses between yielded blobs.
Use this fixture's readiness gates and retained handles to distinguish reader
cleanup from test teardown; extend it to consumer suspension and legacy fallback.
The existing whole-command job wrapper alone does not provide an in-process
streaming-reader interface.

Separate remaining obligations include actual Git/promisor helper behavior,
other Windows/Python versions, escaped or privileged children, abrupt termination
of the outer audit process, separate `git()` calls and `git_source_rows`.
No selected cold replay, supplier admission, mathematical proof, new kappa or
selected-frontier change follows from this tooling audit.
