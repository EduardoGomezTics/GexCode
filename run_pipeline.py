import ast
import subprocess
import timeit
import os
from core.models import BenchmarkResult

# Importamos todas las reglas creadas
from optimization.rules.range_len_rule import RangeLenRule
from optimization.rules.string_count_rule import StringCountRule
from optimization.rules.list_comp_rule import ListCompRule
from optimization.rules.dead_code_rule import DeadCodeRule

class ASTReplacer(ast.NodeTransformer):
    """Safely swaps or removes nodes in the full tree."""
    def __init__(self, original_node, optimized_node, nodes_to_remove=None):
        self.original_node = original_node
        self.optimized_node = optimized_node
        self.nodes_to_remove = nodes_to_remove or []

    def visit(self, node):
        # Si el nodo actual está en la lista de eliminación, lo borramos del árbol
        if node in self.nodes_to_remove:
            return None
        
        # Si encontramos el nodo exacto a transformar, lo intercambiamos
        if node is self.original_node and self.optimized_node is not None:
            return self.optimized_node
            
        return super().generic_visit(node)

def run_full_pipeline(file_path: str):
    print(f"⚙️  Starting PyOptiX Pipeline for: {file_path}")
    
    # --- 1 & 2. DETECTION & TRANSFORMATION (MULTI-PASS) ---
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # EL ORDEN IMPORTA: Ponemos DeadCodeRule primero
    rules = [DeadCodeRule(), StringCountRule(), ListCompRule(), RangeLenRule()]
    
    total_optimizations_applied = []
    
    while True:
        findings = []
        rule = None
        for r in rules:
            findings = r.detect(tree, file_path)
            if findings:
                rule = r
                break
        
        if not findings:
            break  # Romper el bucle cuando ya no haya ineficiencias

        finding = findings[0]
        print(f"\n🔍 Detected: {finding.description}")

        optimization = rule.transform(finding)
        total_optimizations_applied.append(optimization)
        
        # Obtenemos los nodos a eliminar (si la regla los generó)
        nodes_to_remove = getattr(optimization, 'nodes_to_remove', [])
        
        replacer = ASTReplacer(finding.original_node, optimization.optimized_node, nodes_to_remove)
        tree = replacer.visit(tree)
        ast.fix_missing_locations(tree)
    
    if not total_optimizations_applied:
        print("✅ No inefficiencies found. Exiting.")
        return

    optimized_file = file_path.replace(".py", "_optimized.py")
    with open(optimized_file, "w", encoding="utf-8") as f:
        f.write(ast.unparse(tree))
    
    print(f"\n✨ Total transformations applied: {len(total_optimizations_applied)}. Saved to: {optimized_file}")

    # --- 3. VALIDATION (Semantic Safety) ---
    print("\n🛡️  Running Sandbox Validation...")
    
    # Generamos la entrada masiva para pruebas de estrés
    movimientos = (b"R" * 1000000) + (b"L" * 1000000) + (b"F" * 1000000) + (b"B" * 1000000)
    mock_input = b"4000000\n" + movimientos + b"\n"
    
    orig_proc = subprocess.run(["python", file_path], input=mock_input, capture_output=True)
    opt_proc = subprocess.run(["python", optimized_file], input=mock_input, capture_output=True)
    
    if orig_proc.returncode != 0 or opt_proc.returncode != 0:
        print("❌ Error: One of the scripts crashed during execution!")
        return

    if orig_proc.stdout != opt_proc.stdout:
        print("❌ VALIDATION FAILED: The optimized code produces different output.")
        print(f"Original Output:\n{orig_proc.stdout}")
        print(f"Optimized Output:\n{opt_proc.stdout}")
        os.remove(optimized_file)
        return
        
    print("✅ Validation Passed: Outputs are 100% identical.")

    # --- 4. BENCHMARKING ---
    print("\n⏱️  Running Benchmark Engine...")
    iterations = 3
    
    def run_original():
        subprocess.run(["python", file_path], input=mock_input, capture_output=True)
        
    def run_optimized():
        subprocess.run(["python", optimized_file], input=mock_input, capture_output=True)

    orig_time = timeit.timeit(run_original, number=iterations)
    opt_time = timeit.timeit(run_optimized, number=iterations)

    result = BenchmarkResult(
        original_time_ms=(orig_time / iterations) * 1000,
        optimized_time_ms=(opt_time / iterations) * 1000,
        iterations=iterations
    )

    # --- 5. REPORTING ---
    print("\n📊 --- PYOPTIX ANALYSIS REPORT ---")
    print(f"File: {file_path}")
    
    explanations = [getattr(opt, 'explanation', 'Code optimized.') for opt in total_optimizations_applied]
    print(f"Applied ({len(explanations)} transformations):")
    for exp in explanations:
        print(f"  - {exp}")
        
    print(f"Original Time:  {result.original_time_ms:.2f} ms")
    print(f"Optimized Time: {result.optimized_time_ms:.2f} ms")
    
    if result.speedup > 1.0:
        print(f"🚀 Speedup: {result.speedup:.2f}x faster")
    else:
        print(f"⚠️  Speedup: {result.speedup:.2f}x (No improvement detected)")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "dummy_target.py"
    run_full_pipeline(target)