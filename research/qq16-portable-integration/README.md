# Independent QQ16 Windows/Linux integration reproduction

This package independently reproduces the **complete retained PR4790 reduced
integration receipt** using one explicit in-memory path-serialization adapter.
The unchanged original replay passes on Linux and fails on native Windows
before any return executes. The adapted replay passes on Windows and Linux
with the same complete typed receipt. The original scientific algorithms,
source bytes, hash guards, ownership guards and expected receipt are retained.

This is complementary verification of the
[earlier parallel portability claim](https://github.com/CrocSwap/integer-mult-bounds/discussions/4744#discussioncomment-19137557),
which the completed overlap refresh surfaced after this session's own claim.
The scope was explicitly narrowed to independent cross-environment and
authentication evidence; this artifact is published as a Discussion finding,
without a competing repair PR. The two implementations share predecessor
code, fixtures and mathematical assumptions. This is a separate AI session,
not independent human or formal-kernel verification.

**Published-peer follow-up:** [PR4956](https://github.com/CrocSwap/integer-mult-bounds/pull/4956)
at `a3632acbab32202015f0c5ecd11360e92e9a0f10` has now also been independently
replayed on both systems in both modes. All four reports match. The complete
AST differs in exactly the intended expression. [PEER-REVIEW.md](PEER-REVIEW.md)
and [PEER-REVIEW.json](PEER-REVIEW.json) record that separate exact-source audit;
the registered commands below continue to check this independent implementation.

## Exact source and failure

Base: canonical main `cef4b52f2a59009865bf8eabde1be3f159063703`, priority revision 7.
Audited predecessor: JoyboyBrian's [PR4790](https://github.com/CrocSwap/integer-mult-bounds/pull/4790),
head `38dd6b59d50d346bb34fea02a4ee1ac8d282ebbf`, retained unchanged on this base.
All 136 predecessor live inputs plus six predecessor package files are pinned
as this package's 142 live inputs. The selected #4470 source-metadata baseline
passes; no selected file is changed.

The retained loader reaches the PR2753 verifier through:

```
physical-gaussian-leaf/inputs/pr3087.tar
  ! inputs/pr3055.tar ! inputs/pr2899.tar ! inputs/pr2809.tar
  ! inputs/pr2753/verify.py
```

That verifier's SHA256 is
`65126e788eeea10e830fc583cf4afe0bfc4d67495cbf8ac21de3507dbe624d56`.
Its `authenticate` function serializes the 50 predecessor paths using
`str(path.relative_to(here / 'predecessor'))`. On Windows, the 25 nested
`vendor/` names acquire backslashes and the exact POSIX inventory rejects with
`no omitted or extra predecessor files`. This is a source-name representation
mismatch; it does not establish a mathematical or ownership defect.
Mainzu had already identified this same frozen PR2753 mismatch and recorded a
local path-shim replay in
[selected-stock-rho-ledger](https://github.com/CrocSwap/integer-mult-bounds/blob/cef4b52f2a59009865bf8eabde1be3f159063703/research/selected-stock-rho-ledger/README.md#pr3385-replay-and-b1s-fit).
That observation is credited prior work, not a new diagnosis here.

[adapter.py](adapter.py) authenticates those exact bytes and replaces only the
generator element with `path.relative_to(here / 'predecessor').as_posix()`.
It verifies the exact AST location and reverses the edit to check equality of
the entire remaining AST. The original live inventory, invalidation inventory,
predecessor/proof inventories, file-type checks, SHA256 and Git blob checks
still execute. No archive, extracted source or guard is edited on disk.
All 50 manifest names have the same serialization under `PureWindowsPath` and
`PurePosixPath`; a literal POSIX backslash remains distinct from a separator.

The loader hook is confined to the named `frozen_caller_verifier` at the exact
`inputs/pr2753/verify.py` suffix in one isolated child process. Each case must
load it exactly once, with the pinned hash. The hook is restored on exit.
The parent executes the original PR4790 `compute()` unchanged and redirects
only its six subprocess entry points to this wrapper, preserving the original
case order, optimization flags, fresh cache namespaces and 90-second case limits.

## Evidence and reproduction

```sh
python3.12 -B scripts/research_package.py --package research/qq16-portable-integration
python3.12 -I -W error -B research/qq16-portable-integration/verify.py --json
python3.12 -I -O -W error -B research/qq16-portable-integration/verify.py --json
# Unchanged POSIX comparison, from the same pinned source closure:
python3.12 -I -W error -B research/qq16-protected-return-caller/verify.py
```

The original canonical typed receipt SHA256 is
`1c9579c7e34614030922e51697b511db7bea0a3e4c3a652a54bed162e3e19a67`.
Equality covers **every field**, including scalar JSON types. It is not a
projection onto the success flag or numerical totals.

- `fixed` and `adopt` each execute two nonconstant generations and 24 actual
  original-C returns: four producer, six service and two later producer calls
  per generation. All endpoints, borrowed inputs/descriptors, factory/root
  attachment checks, dirty retirement and final inventories match the receipt.
- All four original failure cases retain their recorded boundaries:
  `stale-engines`, `stale-external`, `output-alias` and `service-stop`, including
  the original cleanup observation before fixture recovery.
- The complete reduced-fixture saving is the **predecessor's**
  `(reads, writes, moves) = (61488, 24576, 49200)` with 8,046 record Tapes in each
  successful arm. No new saving or cost result is claimed.
- The actual adapted PR2753 authentication function runs on a separate small
  file fixture containing its full 11-live/50-frozen/4-proof inventory. Eight
  controls reject: extra file, missing nested file, changed live bytes, changed
  predecessor bytes, forged Git blob, omitted invalidation input, omitted
  predecessor pin, and changed verifier bytes before adaptation. These are
  authentication fixtures, not new mathematical input instances.

[RESULT.json](RESULT.json) is a platform-independent receipt. Ordinary runs
compare it without writing; only explicit `--write` regenerates it. The source
closure is self-contained for direct Git-free execution. Metadata/export tools
are separate from the mathematical replay. See [VALIDATION.json](VALIDATION.json)
for recorded environments, commands and publication checks.

## Scope and remaining limitations

This corroborates the original reduced physical composition and its existing
source-bound census comparisons. It does not run production O73/RootLayer
geometry, independently derive the entire census, price finite control, decide
the complete D* versus B* sign, establish all-size numerical/stock/precision
premises, admit a supplier or improve kappa. The selected conditional exponent
remains `60403/20000000`. No full historical suite, Lean, Docker or human proof
review is claimed. The frozen runner itself still fails on Windows without an
explicit adapter; it has not been silently modified.

Initial overlap covered all 315 open PR bodies, 4,037 Discussion records and
all 6,601 top-level notes at the base. It found the earlier parallel claim and
triggered the scope correction. Arbitrary closed diffs, nested source notes and
unpublished work are outside that search. The
[canonical claim and finding](https://github.com/CrocSwap/integer-mult-bounds/discussions/4744#discussioncomment-19137620)
retain the coordination history and publication status.

## Credit

JoyboyBrian supplies PR4790's original composition, verifier and receipt.
Chris R / Clear1nsight supplies #4166/#4167/#4172/#4177's caller, return exchange,
tariff and cleanup/cost lineage. DavidAriasC supplies PR2753's authentication
and logical caller; Jose Manuel supplies the physical controller/loader
lineage. Mainzu supplies the earlier Windows observation and local shim replay.
Tekalign's finite-role exchange work, Sagar Thakrar, ywz65, Ali Romman,
Arham Tahir and every retained source notice keep their predecessor credit.
The earlier parallel portability session has priority for its repair effort;
this artifact is corroborating evidence, not an originality claim.

New independent adapter, boundary fixtures and cross-environment reproduction:
Mihir Srivastava with substantial OpenAI Codex assistance. Apache-2.0.

## Open next questions

The structured questions are in [TASK.json](TASK.json). The exact published
peer adapter has now been corroborated, as recorded above. A future changed
loader or inventory needs a new source-bound adaptation check; the current
exact hash is intentionally restrictive. The scientific follow-up remains the
complete matched D* versus B* bill, including finite control and the unmatched
native/nonchild terms in the admitted nonterminal band. This portability result
supplies no missing cost.
