import ast
from optimization.rules.string_count_rule import StringCountRule

def test_transformation():
    # 1. Parse the target
    target_path = "examples/test_string_count.py"
    with open(target_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    
    # 2. Run detection
    rule = StringCountRule()
    findings = rule.detect(tree, target_path)
    
    if not findings:
        print("No findings to transform.")
        return
        
    finding = findings[0]
    
    # 3. Apply transformation
    optimization = rule.transform(finding)
    
    # 4. Visually compare the unparsed AST nodes
    print("--- ORIGINAL NODE ---")
    print(ast.unparse(finding.original_node))
    print("\n--- OPTIMIZED NODE ---")
    print(ast.unparse(optimization.optimized_node))
    print(f"\n💡 Explanation: {optimization.explanation}")

if __name__ == "__main__":
    test_transformation()