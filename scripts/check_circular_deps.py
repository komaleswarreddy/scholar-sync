#!/usr/bin/env python3
"""
Circular Dependency Checker

Analyzes import statements to detect potential circular dependencies.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict, deque

def find_python_files(root_dir: str = ".") -> List[Path]:
    """Find all Python files in the project."""
    root = Path(root_dir)
    python_files = []
    
    for path in root.rglob("*.py"):
        if any(skip in str(path) for skip in ["__pycache__", ".venv", "venv", "node_modules", ".git", "scripts"]):
            continue
        python_files.append(path)
    
    return python_files

def path_to_module(path: Path) -> str:
    """Convert file path to module name."""
    parts = path.parts
    # Remove .py extension
    module_parts = list(parts[:-1]) + [parts[-1].replace('.py', '')]
    # Remove __init__ and use parent
    if module_parts[-1] == '__init__':
        module_parts = module_parts[:-1]
    return '.'.join(module_parts)

def parse_imports(file_path: Path) -> Set[str]:
    """Parse all imports from a file."""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])  # Top-level module
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level == 0:  # Absolute import
                        imports.add(node.module.split('.')[0])
                    # Relative imports are handled differently
    except:
        pass
    
    return imports

def build_dependency_graph() -> Tuple[Dict[str, Set[str]], Dict[str, str]]:
    """Build dependency graph from imports."""
    python_files = find_python_files()
    graph = defaultdict(set)
    file_to_module = {}
    
    for file_path in python_files:
        module = path_to_module(file_path)
        file_to_module[str(file_path)] = module
        
        imports = parse_imports(file_path)
        
        # Only track project modules
        project_prefixes = ['config', 'packages', 'apps']
        for imp in imports:
            if any(imp.startswith(prefix) for prefix in project_prefixes):
                graph[module].add(imp)
    
    return graph, file_to_module

def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Find cycles in the dependency graph using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node: str):
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, set()):
            # Only check project modules
            if any(neighbor.startswith(prefix) for prefix in ['config', 'packages', 'apps']):
                dfs(neighbor)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles

def check_import_structure():
    """Check import structure for issues."""
    print("=" * 60)
    print("Circular Dependency Analysis")
    print("=" * 60)
    print()
    
    graph, file_to_module = build_dependency_graph()
    
    print(f"Analyzing {len(graph)} modules...")
    print()
    
    # Find cycles
    cycles = find_cycles(graph)
    
    if cycles:
        print(f"✗ Found {len(cycles)} potential circular dependencies:")
        print()
        for i, cycle in enumerate(cycles, 1):
            print(f"Cycle {i}:")
            print("  → ".join(cycle))
            print()
    else:
        print("✓ No circular dependencies detected!")
        print()
    
    # Check for problematic patterns
    print("=" * 60)
    print("Import Structure Analysis")
    print("=" * 60)
    print()
    
    # Check for cross-package imports
    cross_package_imports = []
    for module, deps in graph.items():
        module_parts = module.split('.')
        for dep in deps:
            dep_parts = dep.split('.')
            if len(module_parts) > 1 and len(dep_parts) > 1:
                # Check if they're in different top-level packages
                if module_parts[0] != dep_parts[0]:
                    cross_package_imports.append((module, dep))
    
    if cross_package_imports:
        print(f"⚠️  Found {len(cross_package_imports)} cross-package imports:")
        print("   (These are OK but worth reviewing)")
        for module, dep in cross_package_imports[:10]:
            print(f"   {module} → {dep}")
        if len(cross_package_imports) > 10:
            print(f"   ... and {len(cross_package_imports) - 10} more")
        print()
    else:
        print("✓ No problematic cross-package imports")
        print()
    
    return len(cycles) == 0

def main():
    success = check_import_structure()
    
    print("=" * 60)
    if success:
        print("✓ Dependency analysis passed!")
    else:
        print("⚠️  Potential issues found. Review cycles above.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

