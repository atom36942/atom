import os, importlib, inspect

pkg_dir = os.path.dirname(__file__)

for f in os.listdir(pkg_dir):
    if f.endswith(".py") and f != "__init__.py":
        modname = f[:-3]  # strip ".py"
        module = importlib.import_module(f".{modname}", package=__name__)
        for name, obj in module.__dict__.items():
            if inspect.isfunction(obj):
                globals()[name] = obj
