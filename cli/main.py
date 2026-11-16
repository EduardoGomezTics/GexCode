import argparse
import sys
import os
import ast
from optimization.rules.range_len_rule import RangeLenRule
from optimization.rules.string_count_rule import StringCountRule
from optimization.rules.list_comp_rule import ListCompRule
from optimization.rules.dead_code_rule import DeadCodeRule

# In a real application, you would import these from a dedicated runner module, 
# but we will inline the core logic here to connect it to our existing engine.
def get_engine_and_target(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' not found.")
        sys.exit(1)
        
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    rules = [RangeLenRule(), StringCountRule(), ListCompRule(), DeadCodeRule()]
    findings = []
    rule = None
    for r in rules:
        findings = r.detect(tree, file_path)
        if findings:
            rule = r
            break
            
    return tree, rule, findings

def cmd_analyze(file_path):
    print(f"🔍 Analyzing {file_path}...")
    _, _, findings = get_engine_and_target(file_path)
    
    if not findings:
        print("✅ Code looks good! No inefficiencies detected.")
        return

    print(f"⚠️  Found {len(findings)} inefficiencies:")
    for f in findings:
        print(f"  [{f.rule_id}] Line {f.line_number}: {f.description}")

def cmd_optimize(file_path):
    print(f"⚡ Optimizing {file_path}...")
    tree, rule, findings = get_engine_and_target(file_path)
    
    if not findings:
        print("✅ Nothing to optimize.")
        return

    finding = findings[0]
    optimization = rule.transform(finding)
    
    # We use a simple import here for the ASTReplacer we built earlier
    # In practice, ASTReplacer should live in core/utils.py
    from ast import NodeTransformer
    class ASTReplacer(NodeTransformer):
        def __init__(self, old, new):
            self.old = old
            self.new = new
        def visit(self, node):
            if node is self.old: return self.new
            return super().generic_visit(node)

    replacer = ASTReplacer(finding.original_node, optimization.optimized_node)
    optimized_tree = replacer.visit(tree)
    ast.fix_missing_locations(optimized_tree)
    
    output_file = file_path.replace(".py", "_optimized.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(ast.unparse(optimized_tree))
        
    print(f"✨ Applied: {optimization.explanation}")
    print(f"💾 Optimized file saved as: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        prog="pyoptix",
        description="PyOptiX: A static analyzer and AST-based optimizer for Python."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # Command: analyze
    parser_analyze = subparsers.add_parser("analyze", help="Detect inefficiencies without modifying code")
    parser_analyze.add_argument("file", help="Path to the Python file to analyze")

    # Command: optimize
    parser_optimize = subparsers.add_parser("optimize", help="Apply optimizations and generate an optimized file")
    parser_optimize.add_argument("file", help="Path to the Python file to optimize")

    # Command: benchmark (Placeholder routing to our pipeline script)
    parser_benchmark = subparsers.add_parser("benchmark", help="Run full pipeline: analyze, optimize, validate, and benchmark")
    parser_benchmark.add_argument("file", help="Path to the Python file to benchmark")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args.file)
    elif args.command == "optimize":
        cmd_optimize(args.file)
    elif args.command == "benchmark":
        # Call the pipeline we built in the previous step
        # Note: Ensure run_pipeline.py is importable or move its logic to a core runner.
        print("🚀 Launching full Benchmark Pipeline...")
        import subprocess
        subprocess.run([sys.executable, "run_pipeline.py", args.file])

if __name__ == "__main__":
    main()