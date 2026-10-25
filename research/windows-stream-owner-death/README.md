# Windows stream ownership when the owner dies during setup

This native audit resolves the **owner-death setup question** left open by
[PR #5463](https://github.com/CrocSwap/integer-mult-bounds/pull/5463), at
`991da9010925914ec64a5293286edb10a7910218`. In the tested unchanged adapter,
the requested command stays behind the ownership gate. However, **an unassigned
gate that already opened its event survives owner death until the existing
30-second wait expires**. Kill-on-close protects it only after job assignment.

This is a source-bound finite process audit, not a production repair or a general
crash-safety theorem. It supplies an acceptance boundary for later integration.
Production, frozen predecessors and the selected PR5413 result retain their
bytes. No new kappa or mathematical acceptance is claimed.

## Native observations

The observer retains native process handles before abruptly terminating the
owner with `TerminateProcess`. No Python finally/context cleanup runs in that
owner. Observations precede fixture teardown; PID existence is not used as a
substitute for observing the original process handle.

| Controlled cut | Private job membership | Result after owner death |
| --- | --- | --- |
| Gate spawned, before opening its event and before assignment | Gate outside job | After the observer permits the open, unchanged OpenEventW fails with native error 2. No requested command starts. |
| Gate opened its event and entered its wait; before assignment | Gate outside job | Gate remains alive immediately after owner death. The unchanged 30,000 ms wait returns WAIT_TIMEOUT (258), and the original guard raises RuntimeError. No requested command starts. |
| Assignment succeeded; before event release | Gate in job | Gate terminates; no requested command starts. |
| Gate released; requested process and child ready | Gate in job | Gate, requested process and child all terminate. |

The second row takes about **30 seconds** in the normal receipt. This is an
observation, not a scheduler-independent wall-clock bound. The source's literal
30,000 ms argument, native timeout result and original exception are checked.
A separate 40-second observation guard fails if the gate does not retire;
observer termination cannot count as a passing result.

Three further scenarios distinguish the mechanism:

- **Live owner:** an assigned gate stays closed for a 0.3-second observation.
  After release, the target and child start. Normal context exit stops all three.
- **Early-release counterfactual:** deliberately signal before assignment.
  The target starts without private job ownership, and all three processes
  survive owner death. The ordinary acceptance predicate rejects this case.
- **No-kill counterfactual:** deliberately clear only the native kill-on-close
  flag. The assigned gate, target and child survive owner death. The ordinary
  acceptance predicate rejects this case too.

Counterfactual survivors are stopped and waited for only after recording the
rejections. All seven scenarios preserve that observation/teardown distinction.

## Interpretation and instrumentation

The adapter creates a private job and event, starts the gate, assigns it, and
then signals the event. Its job cannot terminate an unassigned process. A gate
that already opened the event retains its own handle while waiting; a gate that
has not opened it loses the event when the owner's last handle closes.
This interpretation agrees with Microsoft's [job contract](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[assignment boundary](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
and [event lifetime](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-openeventw).
These documents motivate the interpretation; finite observations establish only
the recorded host and cuts.

Base: canonical main `32890bc5de034ab8fc93ac88ead7279a6a416d04`, priority 7.
[SOURCES.json](SOURCES.json) pins main-branch inputs and separately records the
vendored pending predecessor. The live
`scripts/research_package.py` supplies unchanged `_WINDOWS_GATE` text and the
outer guard. `vendor/owned_pipe.py` is a byte-identical PR5463 copy, SHA256
`01f597c8ecb955b2ef7faa8f0650e67c0eca5c0d5f6a817a181c536bef9c37aa`.
The verifier compiles authenticated source bytes directly, without loading
preexisting bytecode for those modules.

PR5463 is pending and its commit is not publication ancestry. Its exact adapter
bytes were fetched and compared before vendoring; the direct checker verifies
both their Git blob ID and SHA256 without requiring that pending commit in a
reviewer's checkout. The separate `vendored_predecessor` record is not a claim
that the registered Git-provenance row checker authenticated that commit's
history. This keeps a clean main-based checkout and the committed export
self-contained. The optional full-history preflight was not run in this
shallow checkout; no historical-ancestry acceptance is claimed.

Observation callbacks hold the named native call boundaries, record readiness,
and forward the original functions and arguments. An isolated `-I -S` observer
bootstrap executes the original gate text. Only the two named counterfactuals
alter event ordering or the native job-limit flag. Instrumentation changes
scheduling and startup overhead; this is not an uninstrumented crash-frequency
measurement. IsProcessInJob queries the specific private job, so an enclosing
job cannot be mistaken for adapter ownership.

A separate outer Job Object bounds the audit to 180 seconds, including failed
fixture startup. It closes after the worker's observations and teardown; its
cleanup is never credited to the tested adapter. Registered execution adds
another enclosing job, exercising nested ownership on this host.

## Reproduction and evidence

Python 3.12, standard library. Native receipts use Windows 11 build 26300 and
CPython 3.12.0. Run from the repository root:

```text
python -I -W error -B research/windows-stream-owner-death/verify.py --require-windows
python -I -W error -O -B research/windows-stream-owner-death/verify.py --require-windows
python -B scripts/research_package.py --package research/windows-stream-owner-death --check-only
python -B scripts/research_package.py --package research/windows-stream-owner-death
```

Each native mode prints `PASS_WINDOWS_STREAM_OWNER_DEATH cases=7 receipt_controls=5`.
The [normal](evidence/windows-normal.json) and [optimized](evidence/windows-optimized.json)
receipts bind reader, adapter and probe hashes and record liveness, native errors,
wait results, exit codes, timings and teardown. Timing and termination exit codes
are diagnostics, not portable acceptance constants. Termination is checked
through process handles.

Five receipt mutations reject a changed source hash, missing case, hidden surviving
child, cleanup substituted for observation, and erased pre-assignment survival.
Explicit checks remain active under `-O`.

On another OS, registered verification authenticates sources and checks the two
saved receipts and controls, printing **PASS_STORED_OWNER_DEATH_RECEIPTS_WINDOWS_NOT_RUN**.
This is stored-evidence integrity, not a fresh native replay. `--require-windows`
rejects reduced coverage. A checked export contains all direct replay inputs;
the same commands then work without a Git checkout.

## Coordination and credit

The [canonical claim](https://github.com/CrocSwap/integer-mult-bounds/discussions/4681#discussioncomment-19174028)
records the session's one pivot. The full refresh exposed earlier launch-error
claims [19174004](https://github.com/CrocSwap/integer-mult-bounds/discussions/4681#discussioncomment-19174004)
and [19174025](https://github.com/CrocSwap/integer-mult-bounds/discussions/4681#discussioncomment-19174025).
That duplicate implementation scope was released. The preliminary missing-executable
observation was shared as corroboration. This package takes the separate,
explicitly open owner-death question in PR5463.

Entry overlap covered 377 open PR bodies, 4,784 Discussion records and all 7,402
tracked local README/TASK/ledger notes after checkout completed. Reported pagination
and note inventory were complete; arbitrary diffs and unpublished work are outside
coverage. The selected metadata baseline passed; it is orientation, not a
mathematical replay.

The final refresh covered **379 open PRs** (06:28:55 UTC), **4,799 Discussion
records** (06:30:35 UTC), and all **7,402 tracked notes**, with complete reported
coverage and no warnings. Canonical main was unchanged. It surfaced the parallel
[owner-death audit in #1472](https://github.com/CrocSwap/integer-mult-bounds/discussions/1472#discussioncomment-19174060),
which also covers the shared command launcher. This package is published as a
**fork artifact and independent corroboration/handoff**, with no duplicate audit
PR or novelty claim for the common lifetime conclusion. Its narrower stream
adapter probe distinguishes both pre-assignment event states and retains two
explicit native counterfactuals. These are separate Codex-assisted sessions under
the same account, not independent human review.

Credit **ywz65 / #2469** for the pre-spawn gate and Job Object lifecycle and
**#2452** for retained-handle observation; **Mihir Srivastava / #5463** for the
adapter; **Brian / JoyboyBrian / #4738 and #5185** for deadlines and the lifetime
contract; **Nick Petalas / #2752** for source reading/fallback; and **Douglas
Colkitt** for the runner. Retain #5461 and the `7a9a2b67` audit, Windows successors
#4686/#5358/#5047, **Paul Romeo, yssite, Arham Tahir, Woklerx, Tekalign**, and all
source notices. Prepared for **Mihir Srivastava (@mihir-s-05)** with substantial
**OpenAI Codex** assistance, one agent. Apache-2.0. These are author-checked
results from a separate session, not independent human or formal-kernel review.

## Open next questions

1. **Must bootstrap retirement be prompt?** Specify the acceptable lifetime first.
   Then test atomic process/job creation or a parent-lifetime wait against the
   two pre-assignment cuts. Neither repair is implemented or proved here.
2. **What is the deployment contract?** Repeat these cuts on the intended host
   and bind an actual Git/helper invocation. Restrictive enclosing jobs,
   nonstandard process creation, breakaway attempts and every instruction-level
   crash interleaving remain untested. Launch-error repair and shared-runner
   adoption belong to coordinated successor work.

No full Git-reader protocol suite, selected cold replay, Lean, Docker, supplier
admission or multiplication-theorem audit is claimed. These controlled processes
do not establish a universal no-leak guarantee or an installed-Git incident.
