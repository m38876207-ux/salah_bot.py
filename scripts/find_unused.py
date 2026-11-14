"""Print possibly unused imports (simple static check, no deps)."""

import ast
import pathlib


def main() -> None:
    for path in sorted(pathlib.Path("salahbot").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported[alias.asname or alias.name.split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported[alias.asname or alias.name] = node.lineno
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for name, line in imported.items():
            if name not in used:
                print(f"{path}:{line}: unused import {name}")


if __name__ == "__main__":
    main()
