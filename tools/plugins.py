"""Dynamic Plugin & Tool System for JARVIS (7.7)."""

import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PLUGINS_DIR = BASE_DIR / "plugins"
PLUGINS_DIR.mkdir(exist_ok=True)


class PluginManager:
    """Discovers and executes user-extensible Python plugins in the plugins/ directory."""

    def __init__(self, plugins_dir=None):
        self.plugins_dir = Path(plugins_dir) if plugins_dir else PLUGINS_DIR
        self.plugins_dir.mkdir(exist_ok=True)
        self.tools = {}  # name -> {name, description, usage, func, module}
        self.errors = []
        self.reload()

    def reload(self):
        self.tools.clear()
        self.errors.clear()

        for py_file in sorted(self.plugins_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{py_file.stem}", str(py_file))
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "register_tools") and callable(module.register_tools):
                    registered = module.register_tools() or {}
                    for tool_name, meta in registered.items():
                        clean_name = tool_name.strip().lower()
                        if isinstance(meta, dict) and callable(meta.get("func")):
                            self.tools[clean_name] = {
                                "name": clean_name,
                                "description": meta.get("description", "Custom plugin tool"),
                                "usage": meta.get("usage", f"/plugin {clean_name} <args>"),
                                "func": meta["func"],
                                "module": py_file.name,
                            }
            except Exception as err:
                self.errors.append(f"{py_file.name}: {err}")

    def list_tools(self) -> list[dict]:
        return list(self.tools.values())

    def run_tool(self, name: str, arg_text: str = "") -> str:
        key = (name or "").strip().lower()
        if key not in self.tools:
            available = ", ".join(sorted(self.tools.keys())) or "(none)"
            raise KeyError(f"Plugin tool '{key}' not found. Available: {available}")
        return str(self.tools[key]["func"](arg_text))


plugin_manager = PluginManager()

