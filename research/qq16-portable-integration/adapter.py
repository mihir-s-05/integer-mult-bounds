"""One explicit in-memory portability edit to the authenticated PR2753 loader.

Mihir Srivastava with substantial OpenAI Codex assistance. Apache-2.0.
The authentication body and all physical/scientific code retain their authors.
"""
import ast
from contextlib import contextmanager
import hashlib
import importlib.abc
import importlib.util
from pathlib import Path

SOURCE_SHA256 = '65126e788eeea10e830fc583cf4afe0bfc4d67495cbf8ac21de3507dbe624d56'
OLD = "str(path.relative_to(here / 'predecessor'))"
NEW = "path.relative_to(here / 'predecessor').as_posix()"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def portable_code(raw, filename):
    """Keep every AST node except the single inventory-name serialization call."""
    need(hashlib.sha256(raw).hexdigest() == SOURCE_SHA256,
         'exact PR2753 verifier bytes before portability adaptation')
    tree = ast.parse(raw, filename=filename)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'authenticate']
    need(len(functions) == 1, 'one original authenticate function')
    assignments = [n for n in functions[0].body if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id == 'physical']
    need(len(assignments) == 1, 'one original physical inventory')
    value = assignments[0].value
    need(isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
         and value.func.id == 'sorted' and len(value.args) == 1
         and isinstance(value.args[0], ast.GeneratorExp), 'original inventory generator')
    generator = value.args[0]
    old = ast.parse(OLD, mode='eval').body
    need(ast.dump(generator.elt) == ast.dump(old), 'exact inventory-name expression')
    before = ast.dump(tree)
    generator.elt = ast.copy_location(ast.parse(NEW, mode='eval').body, generator.elt)
    # Reverse this one edit and compare the entire AST, including every guard.
    new = generator.elt
    generator.elt = old
    need(ast.dump(tree) == before, 'all other original AST nodes preserved')
    generator.elt = new
    ast.fix_missing_locations(tree)
    return compile(tree, filename, 'exec')


@contextmanager
def portable_loader():
    """Used only inside an isolated case process; never edit an extracted file."""
    original = importlib.util.spec_from_file_location
    loads = []

    class Loader(importlib.abc.Loader):
        def __init__(self, path):
            self.path = path

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            raw = self.path.read_bytes()
            code = portable_code(raw, str(self.path))
            module.__file__ = str(self.path)
            exec(code, module.__dict__)
            loads.append(SOURCE_SHA256)

    def spec(name, location=None, *args, **kwargs):
        if name != 'frozen_caller_verifier':
            return original(name, location, *args, **kwargs)
        need(not args and not kwargs, 'original explicit PR2809 loader API')
        path = Path(location)
        need(path.parts[-3:] == ('inputs', 'pr2753', 'verify.py'),
             'exact nested PR2753 loader location')
        return original(name, path, loader=Loader(path))

    importlib.util.spec_from_file_location = spec
    try:
        yield loads
    finally:
        importlib.util.spec_from_file_location = original
