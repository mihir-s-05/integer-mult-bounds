# Independent exact-source review of PR4956

**No blocking defect found in the bounded portability/reproduction claim.**
Reviewed [PR4956](https://github.com/CrocSwap/integer-mult-bounds/pull/4956) at
`a3632acbab32202015f0c5ecd11360e92e9a0f10`, after first implementing the separate
AST/loader adapter in this package and reproducing the unchanged Linux baseline.
This review is by a separate OpenAI Codex session under the same contributor
account. It is not independent human review, formal verification, supplier
admission or authority to change the selected frontier.

## What was independently checked

1. Read the complete submitted verifier. Its before/after SHA256 gates bind
   exactly one byte replacement; its subprocess facade preserves the original
   six destinations, mode, fresh bytecode-cache isolation and 90-second bounds.
   No mathematical checks or expected receipt fields are removed.
2. Independently parse the original full PR2753 source, locate `authenticate`'s
   `physical` generator, replace its one element with `.as_posix()`, and compare
   the entire AST with the peer's transformed source. They are identical after
   discarding location metadata. The path representation is the only AST delta.
   This uses a different mechanism from the peer's byte-replacement hash check.
3. Export the exact peer commit with the official exporter and check the archive.
   The 148 payload files reproduce archive SHA256
   `b48b4d5e5a44b9a0e6bb694184f46c195117e4721fc9e93d211ee9442c77c7c4`,
   independently matching the author's reported export. Including the export
   receipt, the extracted tree contains 149 files. No Git checkout is present.
4. Run the peer's own verifier from that export on Windows/CPython 3.12.0 and
   Ubuntu on WSL/CPython 3.12.3, both normally and with `-O`. Every exported file
   is marked read-only on the Windows host; Git is absent from each test PATH.
   Every file's SHA256 is unchanged after each of the four runs. The Linux
   kernel is `6.6.114.1-microsoft-standard-WSL2`.
5. Compare all four complete JSON reports, then bind their original-receipt
   digest to the independent implementation's already reproduced full receipt:
   `1c9579c7e34614030922e51697b511db7bea0a3e4c3a652a54bed162e3e19a67`.

All four peer reports are identical. Every run executes `fixed`, `adopt`,
`stale-engines`, `stale-external`, `output-alias` and `service-stop`; both success
arms execute two generations and 24 actual child returns. All twelve peer
authentication/receipt controls reject, including omitted cleanup and
boolean/integer/float substitutions. The original receipt comparison is complete
and type-sensitive. The separate independent verifier's eight source controls
and its Git-free export corruption checks are recorded in
[COLD-EXPORT.json](COLD-EXPORT.json).

[PEER-REVIEW.json](PEER-REVIEW.json) records the exact head, archive hash, full
peer report and the four run results. Its wall times describe this loaded local
host; they are not performance comparisons. The registered hook for this audit
package does **not** automatically fetch or rerun the peer; the peer execution
above was an explicit review step.

## Reproduce the peer check

Fetch the public PR head, verify it still has the reviewed SHA, then use the
exact SHA for export even if the PR later advances:

```sh
git fetch https://github.com/CrocSwap/integer-mult-bounds.git refs/pull/4956/head
git rev-parse FETCH_HEAD
python3.12 scripts/export_research_package.py export \
  --ref a3632acbab32202015f0c5ecd11360e92e9a0f10 \
  --package research/qq16-portable-integration --output peer4956.tar.gz
python3.12 scripts/export_research_package.py check peer4956.tar.gz
```

Extract into a new directory. From that exported root, run on each system:

```sh
python3.12 -I -B -W error research/qq16-portable-integration/verify.py --json
python3.12 -I -O -B -W error research/qq16-portable-integration/verify.py --json
```

For the Git-free Windows runs this review used the absolute `python.exe` path
and set `PATH` to an empty directory. For Linux it used
`/usr/bin/env PATH=/nonexistent /usr/bin/python3` with the same flags. Compare
canonical JSON, not the platforms' line terminators. The peer's own original
aggregator still compares every scientific receipt field internally.

## Limits and attribution

This confirms the exact submitted implementation and finite evidence; it does
not derive a new mathematical construction. Both independent implementations
reuse the original PR4790 aggregator and reduced numerical fixtures. No
production O73/RootLayer run, new full-root census, finite-control price,
complete D* versus B* sign, all-size proof, CI verdict or new kappa is claimed.
Any later peer/source revision needs a new scope check. No GitHub approval,
merge, closure or selected-record edit was performed.

JoyboyBrian, Chris R / Clear1nsight, DavidAriasC, Mainzu, Jose Manuel, Tekalign
and the complete retained QQ16/native lineage keep their source and observation
credit. The earlier session's PR4956 supplies the repair being reviewed.
Independent review and corroboration by Mihir Srivastava with substantial
OpenAI Codex assistance. Apache-2.0.
