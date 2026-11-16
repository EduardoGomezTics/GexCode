import ast
import sys

def test_idempotency(file_path: str):
    print(f"🔍 Testing idempotency for: {file_path}")
    
    # 1. Read the original source code
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_source = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Could not find {file_path}. Make sure you are in the Gex directory.")
        sys.exit(1)

    try:
        # 2. Parse the original source into an AST
        original_tree = ast.parse(original_source)
        
        # 3. Unparse the AST back into a Python string
        # Note: This strips comments and normalizes indentation
        unparsed_source = ast.unparse(original_tree)
        
        # 4. Parse the newly generated string back into a second AST
        new_tree = ast.parse(unparsed_source)
        
        # 5. Compare the structural dumps of both trees
        original_dump = ast.dump(original_tree)
        new_dump = ast.dump(new_tree)
        
        if original_dump == new_dump:
            print("✅ SUCCESS: The AST remains identical after unparsing.")
            print("The engine can safely read and write code without breaking logic.")
        else:
            print("❌ FAILURE: The AST structure changed during the round-trip.")
            sys.exit(1)

    except SyntaxError as e:
        print(f"❌ FAILURE: SyntaxError generated during unparsing: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FAILURE: Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_idempotency("examples/test_string_count.py")