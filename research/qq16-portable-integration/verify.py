#!/usr/bin/env python3
"""Replay the complete retained PR4790 certificate with one path-name adapter.

Mihir Srivastava with substantial OpenAI Codex assistance. Apache-2.0.
The original construction, verifier and receipt are credited to JoyboyBrian
and the retained QQ16/physical-controller predecessors.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
import tarfile
import tempfile
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREDECESSOR = ROOT / 'research/qq16-protected-return-caller'
ARCHIVE = 'research/physical-gaussian-leaf/inputs/pr3087.tar'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def module(name, path):
    result = types.ModuleType(name)
    result.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), result.__dict__)
    return result


def authenticate():
    rows = json.loads((HERE / 'SOURCES.json').read_bytes())['files']
    inputs = [r for r in rows if r['usage'] == 'input']
    need(len(inputs) == len({r['path'] for r in inputs}), 'unique portable input closure')
    for row in inputs:
        path = ROOT / row['path']
        need(path.is_file() and not path.is_symlink(), 'regular input: ' + row['path'])
        raw = path.read_bytes()
        need(sha(raw) == row['sha256'], 'source integrity: ' + row['path'])
        need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
             == row['git_blob'], 'source Git blob: ' + row['path'])
    return len(inputs)


def retained_verifier():
    raw = (ROOT / ARCHIVE).read_bytes()
    for name in ('inputs/pr3055.tar', 'inputs/pr2899.tar', 'inputs/pr2809.tar',
                 'inputs/pr2753/verify.py'):
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
            members = [m for m in archive.getmembers() if m.name == name]
            need(len(members) == 1 and members[0].isfile(), 'one retained archive member')
            raw = archive.extractfile(members[0]).read()
    return raw


def case(name):
    authenticate()
    adapter = module('portable_auth_adapter', HERE / 'adapter.py')
    original = module('retained_return_verifier', PREDECESSOR / 'verify.py')
    with adapter.portable_loader() as loads:
        result = original.case(name)
    need(loads == [adapter.SOURCE_SHA256], 'exactly one adapted PR2753 load per case')
    return result


def boundary_controls():
    """Exercise the actual original authentication guards on a small file tree."""
    adapter = module('portable_auth_controls', HERE / 'adapter.py')
    raw = retained_verifier()
    original = types.ModuleType('original_pr2753_controls')
    original.__file__ = str(HERE / 'retained-pr2753.py')
    exec(compile(raw, original.__file__, 'exec'), original.__dict__)
    adapted = types.ModuleType('portable_pr2753_controls')
    adapted.__file__ = original.__file__
    exec(adapter.portable_code(raw, adapted.__file__), adapted.__dict__)
    controls = {}

    def reject(label, action, expected):
        try:
            action()
        except ValueError as error:
            need(str(error) == expected, 'wrong rejection boundary for ' + label + ': ' + str(error))
            controls[label] = str(error)
        else:
            raise ValueError('accepted negative control: ' + label)

    with tempfile.TemporaryDirectory(prefix='qq16-inventory-control-') as td:
        root = Path(td).resolve()
        here = root / 'fixture'

        def put(path, content):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return {'sha256': sha(content), 'git_blob': hashlib.sha1(
                b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()}

        sources = {'files': [dict(path=name, usage='input', **put(root / name, name.encode()))
                             for name in original.LIVE_INPUTS]}
        predecessor = {'head': 'a53fdf4bcbe33c6732f0bec1badc8c023380f9d1',
                       'files': {name: put(here / 'predecessor' / name, name.encode())
                                 for name in original.FROZEN_FILES}}
        evidence = {'files': [dict(path=name, commit=commit, **put(here / name, name.encode()))
                              for name, commit in original.EVIDENCE_FILES.items()]}
        manifest = {'inputs': list(original.LIVE_INPUTS)}
        kwargs = dict(sources=sources, predecessor=predecessor, manifest=manifest,
                      here=here, root=root, evidence=evidence)
        expected = dict(live_inputs=len(original.LIVE_INPUTS), frozen_files=len(original.FROZEN_FILES),
                        frozen_proofs=len(original.EVIDENCE_FILES), predecessor_head=predecessor['head'])
        need(adapted.authenticate(**kwargs) == expected, 'adapted real authentication positive control')
        if sys.platform == 'win32':
            reject('original_windows_inventory', lambda: original.authenticate(**kwargs),
                   'no omitted or extra predecessor files')
        else:
            need(original.authenticate(**kwargs) == expected, 'original POSIX positive control')

        extra = here / 'predecessor' / 'unlisted.py'
        extra.write_bytes(b'unlisted')
        reject('extra_file', lambda: adapted.authenticate(**kwargs), 'no omitted or extra predecessor files')
        extra.unlink()
        nested = here / 'predecessor' / 'vendor/controller.py'
        saved = nested.read_bytes()
        nested.unlink()
        reject('missing_nested_file', lambda: adapted.authenticate(**kwargs), 'no omitted or extra predecessor files')
        nested.write_bytes(saved + b'changed')
        reject('changed_predecessor_bytes', lambda: adapted.authenticate(**kwargs),
               'pinned bytes changed: vendor/controller.py')
        nested.write_bytes(saved)
        live = root / original.LIVE_INPUTS[0]
        saved_live = live.read_bytes()
        live.write_bytes(saved_live + b'changed')
        reject('changed_live_bytes', lambda: adapted.authenticate(**kwargs),
               'pinned bytes changed: ' + original.LIVE_INPUTS[0])
        live.write_bytes(saved_live)
        row = predecessor['files']['vendor/controller.py']
        saved_blob = row['git_blob']
        row['git_blob'] = '0' * 40
        reject('forged_git_blob', lambda: adapted.authenticate(**kwargs),
               'pinned Git blob changed: vendor/controller.py')
        row['git_blob'] = saved_blob
        omitted = manifest['inputs'].pop()
        reject('omitted_invalidation_input', lambda: adapted.authenticate(**kwargs),
               'exact replay invalidation inventory')
        manifest['inputs'].append(omitted)
        removed = predecessor['files'].pop('vendor/controller.py')
        reject('omitted_predecessor_pin', lambda: adapted.authenticate(**kwargs),
               'exact predecessor source inventory')
        predecessor['files']['vendor/controller.py'] = removed
        need(adapted.authenticate(**kwargs) == expected, 'restored positive authentication')

    reject('changed_adapter_source', lambda: adapter.portable_code(raw + b'\n', 'mutant'),
           'exact PR2753 verifier bytes before portability adaptation')
    # A POSIX literal backslash must not be silently turned into a directory.
    names = original.FROZEN_FILES
    need([PureWindowsPath(n).as_posix() for n in names] == list(names)
         and [PurePosixPath(n).as_posix() for n in names] == list(names),
         'all frozen inventory names have equal cross-platform serialization')
    need(PurePosixPath('vendor\\controller.py').as_posix() != 'vendor/controller.py',
         'POSIX literal backslash is not normalized into a directory separator')
    controls.pop('original_windows_inventory', None)
    return {'frozen_inventory_names': len(names), 'original_authentication_counts': expected,
            'rejections': controls, 'literal_posix_backslash_distinct': True}


def compute():
    count = authenticate()
    controls = boundary_controls()
    original = module('retained_return_compute', PREDECESSOR / 'verify.py')
    dispatched = []

    def run(command, **kwargs):
        # Preserve original cases, isolation, optimization, cache and timeouts;
        # change only the entry point so each child installs the explicit adapter.
        prefix = [sys.executable, '-I', '-B'] + (['-O'] if sys.flags.optimize else [])
        need(command[:len(prefix)] == prefix and len(command) == len(prefix) + 5,
             'original isolated case command')
        need(command[-3] == str(PREDECESSOR / 'verify.py') and command[-2] == '--case'
             and command[-1] in original.CASE_NAMES and command[-5] == '-X'
             and command[-4].startswith('pycache_prefix='), 'original case launch boundary')
        changed = list(command)
        changed[-3] = str(HERE / 'verify.py')
        dispatched.append(command[-1])
        return subprocess.run(changed, **kwargs)

    original.subprocess = types.SimpleNamespace(run=run)
    result = original.compute()
    need(tuple(dispatched) == original.CASE_NAMES, 'all six original cases dispatched once in order')
    expected = json.loads((PREDECESSOR / 'RESULT.json').read_bytes())
    need(canonical(result) == canonical(expected), 'complete typed original PR4790 receipt equality')
    return {'status': 'PASS_QQ16_PORTABLE_INTEGRATION', 'live_inputs': count,
            'adapted_source_sha256': sha(retained_verifier()),
            'original_receipt_canonical_sha256': sha(canonical(result).encode()),
            'cases': dispatched, 'completed_generations_per_successful_case': 2,
            'actual_child_returns_per_successful_case': 24,
            'finite_matched_saving_RWM': result['finite_matched_saving_RWM'],
            'boundary_controls': controls,
            'scope': 'Portability and reproduction of the complete original reduced fixture; no new scientific claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('fixed', 'adopt', 'stale-engines', 'stale-external',
                                         'output-alias', 'service-stop'))
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.case:
        need(not args.write and not args.json, 'case only emits original JSON')
        print(canonical(case(args.case)))
        return
    result = compute()
    if args.write:
        (HERE / 'RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n',
                                         encoding='utf-8', newline='\n')
    else:
        need(canonical(result) == canonical(json.loads((HERE / 'RESULT.json').read_bytes())),
             'complete portable receipt equality')
    print(canonical(result) if args.json else result['status'])


if __name__ == '__main__':
    main()
