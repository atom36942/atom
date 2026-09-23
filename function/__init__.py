"""Discover and export func_* functions from modules in this shared folder.

Add a Python module here to expose its functions through ``from function import
*`` and Atom's app.state registration. Module names beginning with an underscore
are private. Import dependencies from their defining modules, not this package,
because package exports are assembled only after all modules have loaded.
"""

from importlib import import_module as _import_module
from inspect import isfunction as _isfunction
from pkgutil import iter_modules as _iter_modules


def _discover_functions():
    exports = {}
    owners = {}
    for info in sorted(_iter_modules(__path__), key=lambda item: item.name):
        if info.ispkg or info.name.startswith("_"):
            continue
        module = _import_module(f"{__name__}.{info.name}")
        for name, value in vars(module).items():
            # Imported helpers belong to their defining module, not this one.
            if not name.startswith("func_") or not _isfunction(value) or value.__module__ != module.__name__:
                continue
            if name in exports:
                raise ImportError(
                    f"Duplicate function '{name}': defined in "
                    f"{owners[name]} and {module.__file__}"
                )
            exports[name] = value
            owners[name] = module.__file__
    return exports


_exports = _discover_functions()
__all__ = sorted(_exports)
globals().update(_exports)
del _exports
