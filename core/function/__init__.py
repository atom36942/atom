import os
import importlib

# Automatically discover and import all modules in all subfolders recursively.
# This eliminates the need for __init__.py files in every subfolder.
def _import_recursive(package_path, package_name):
    for root, dirs, files in os.walk(package_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Calculate the relative module path (e.g., 'database.read')
                rel_path = os.path.relpath(os.path.join(root, file), package_path)
                module_name = rel_path[:-3].replace(os.path.sep, ".")
                
                # Import the leaf module
                module = importlib.import_module(f".{module_name}", package_name)
                
                # Flatten the module's public attributes into the package namespace
                for attr_name in dir(module):
                    if not attr_name.startswith("_"):
                        globals()[attr_name] = getattr(module, attr_name)

# Start recursive import from the current directory
_import_recursive(__path__[0], __package__)

# Cleanup internal helpers to maintain a clean namespace
del os, importlib, _import_recursive