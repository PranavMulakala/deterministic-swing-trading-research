import ast
from pathlib import Path
import unittest


class ArchitectureTests(unittest.TestCase):
    def test_decision_path_has_no_network_or_llm_imports(self) -> None:
        package = Path(__file__).parents[1] / "src/swingbot"
        modules = sorted(package.glob("*.py"))
        llm_imports = {"openai", "anthropic", "langchain", "litellm"}
        network_imports = {
            "aiohttp", "ftplib", "http", "httpx", "requests", "socket", "subprocess",
            "urllib", "websockets",
        }
        self.assertEqual(len(modules), 14, "classify every swingbot module when adding one")
        for module in modules:
            tree = ast.parse(module.read_text(encoding="utf-8"))
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(
                        node.func.id, {"__import__", "eval", "exec"},
                        f"{module.name}: dynamic execution/import is prohibited",
                    )
            self.assertFalse(
                imports & llm_imports,
                f"{module.name}: LLM imports are prohibited: {imports & llm_imports}",
            )
            if module.name != "data.py":
                self.assertFalse(
                    imports & network_imports,
                    f"{module.name}: network-capable imports are restricted to data.py: "
                    f"{imports & network_imports}",
                )


if __name__ == "__main__":
    unittest.main()
