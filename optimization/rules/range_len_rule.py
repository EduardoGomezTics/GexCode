import ast
import copy
from core.models import Finding, Optimization
from optimization.base_rule import OptimizationRule

class RangeLenBodyTransformer(ast.NodeTransformer):
    """
    Walks the inside of the loop to replace list_name[index] with a new variable.
    Example: Replaces 'readings[i]' with 'item'.
    """
    def __init__(self, list_name: str, index_name: str, new_var_name: str):
        self.list_name = list_name
        self.index_name = index_name
        self.new_var_name = new_var_name

    def visit_Subscript(self, node: ast.Subscript):
        # Always visit children first in a transformer
        self.generic_visit(node)
        
        # Look for the pattern: list_name[index_name]
        if isinstance(node.value, ast.Name) and node.value.id == self.list_name:
            # Note: Python 3.9+ handles slices as direct nodes
            if isinstance(node.slice, ast.Name) and node.slice.id == self.index_name:
                # Replace the entire Subscript node with just a Name node
                return ast.Name(id=self.new_var_name, ctx=node.ctx)
        
        return node

class RangeLenRule(OptimizationRule):
    id = "OPT_001"
    description = "Inefficient use of range(len(...)). Use direct iteration instead."
    risk_level = "Safe"

    def detect(self, tree: ast.AST, file_path: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                iter_node = node.iter
                if isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name):
                    if iter_node.func.id == 'range' and len(iter_node.args) == 1:
                        inner_call = iter_node.args[0]
                        if isinstance(inner_call, ast.Call) and isinstance(inner_call.func, ast.Name):
                            if inner_call.func.id == 'len' and len(inner_call.args) == 1:
                                # Ensure the target and list are simple variables
                                if isinstance(node.target, ast.Name) and isinstance(inner_call.args[0], ast.Name):
                                    findings.append(Finding(
                                        rule_id=self.id,
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        description=self.description,
                                        original_node=node,
                                        risk_level=self.risk_level
                                    ))
        return findings

    def transform(self, finding: Finding) -> Optimization:
        # 1. Deep copy to avoid mutating the engine's original AST
        optimized_node = copy.deepcopy(finding.original_node)
        
        # 2. Extract variable names from the original structure
        index_name = optimized_node.target.id
        list_name = optimized_node.iter.args[0].args[0].id
        new_var_name = "item"  # A simple replacement name for now
        
        # 3. Rewrite the loop signature: from 'for i in range(len(readings)):' to 'for item in readings:'
        optimized_node.target = ast.Name(id=new_var_name, ctx=ast.Store())
        optimized_node.iter = ast.Name(id=list_name, ctx=ast.Load())
        
        # 4. Transform the inner body of the loop
        transformer = RangeLenBodyTransformer(list_name, index_name, new_var_name)
        optimized_node.body = [transformer.visit(stmt) for stmt in optimized_node.body]
        
        # 5. Critical: Re-sync AST line numbers for the newly generated nodes
        ast.fix_missing_locations(optimized_node)
        
        return Optimization(
            finding=finding,
            optimized_node=optimized_node,
            explanation=f"Replaced range(len({list_name})) with direct iteration over '{list_name}'."
        )