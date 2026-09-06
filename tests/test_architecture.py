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
        self.assertEqual(len(modules), 27, "classify every swingbot module when adding one")
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
            if module.name not in {"data.py", "alpaca_paper.py"}:
                self.assertFalse(
                    imports & network_imports,
                    f"{module.name}: network-capable imports are restricted to the two approved adapters: "
                    f"{imports & network_imports}",
                )

    def test_broker_mutations_are_called_only_from_approval_workflow(self) -> None:
        package = Path(__file__).parents[1] / "src/swingbot"
        mutators = {"submit_entry", "close_position", "cancel_order"}
        calls: list[tuple[str, str]] = []
        for module in sorted(package.glob("*.py")):
            if not module.name.startswith("paper_"):
                continue
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in mutators:
                        calls.append((module.name, node.func.attr))
        self.assertEqual(
            sorted(calls),
            sorted(
                [
                    ("paper_workflow.py", "cancel_order"),
                    ("paper_workflow.py", "close_position"),
                    ("paper_workflow.py", "submit_entry"),
                ]
            ),
        )

    def test_authoritative_state_writes_are_isolated(self) -> None:
        package = Path(__file__).parents[1] / "src/swingbot"
        callers: set[str] = set()
        for module in sorted(package.glob("*.py")):
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "_append_state"
                ):
                    callers.add(module.name)
        self.assertEqual(callers, {"paper_reconcile.py", "paper_workflow.py"})

    def test_every_public_workflow_operation_is_process_serialized(self) -> None:
        module = Path(__file__).parents[1] / "src/swingbot/paper_workflow.py"
        tree = ast.parse(module.read_text(encoding="utf-8"))
        workflow = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "PaperWorkflow"
        )
        public = {
            node.name
            for node in workflow.body
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")
        }
        serialized = {
            node.name
            for node in workflow.body
            if isinstance(node, ast.FunctionDef)
            and any(
                isinstance(decorator, ast.Name) and decorator.id == "_serialized"
                for decorator in node.decorator_list
            )
        }
        self.assertEqual(serialized, public)


if __name__ == "__main__":
    unittest.main()
