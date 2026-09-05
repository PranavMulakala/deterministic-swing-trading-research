import ast
from pathlib import Path
import unittest


class ArchitectureTests(unittest.TestCase):
    def test_decision_path_has_no_network_or_llm_imports(self) -> None:
        package = Path(__file__).parents[1] / "src/swingbot"
        forbidden = {"openai", "anthropic", "requests", "urllib", "socket", "httpx"}
        for name in ("strategy.py", "risk.py", "backtest.py"):
            tree = ast.parse((package / name).read_text(encoding="utf-8"))
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertFalse(imports & forbidden, f"{name}: forbidden imports {imports & forbidden}")


if __name__ == "__main__":
    unittest.main()
