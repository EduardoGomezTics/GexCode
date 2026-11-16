import ast
import copy
from core.models import Finding, Optimization
from optimization.base_rule import OptimizationRule

class StringCountRule(OptimizationRule):
    id = "OPT_002"
    description = "Inefficient string counting in loop. Use .count() instead."
    risk_level = "Safe"

    def detect(self, tree: ast.AST, file_path: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if not isinstance(node.target, ast.Name):
                    continue
                iter_var = node.target.id
                
                # Check if body consists of only an If statement
                if len(node.body) == 1 and isinstance(node.body[0], ast.If):
                    if_node = node.body[0]
                    if self._check_if_chain(if_node, iter_var):
                        findings.append(Finding(
                            rule_id=self.id,
                            file_path=file_path,
                            line_number=node.lineno,
                            description=self.description,
                            original_node=node,
                            risk_level=self.risk_level
                        ))
        return findings

    def _check_if_chain(self, if_node, iter_var):
        if not isinstance(if_node, ast.If):
            return False
            
        # Check condition: iter_var == 'String'
        if not (isinstance(if_node.test, ast.Compare) and 
                len(if_node.test.ops) == 1 and isinstance(if_node.test.ops[0], ast.Eq) and
                isinstance(if_node.test.left, ast.Name) and if_node.test.left.id == iter_var):
            return False
            
        # Check body: numeric augassign
        if not (len(if_node.body) == 1 and isinstance(if_node.body[0], ast.AugAssign)):
            return False
            
        if if_node.orelse:
            if len(if_node.orelse) == 1 and isinstance(if_node.orelse[0], ast.If):
                return self._check_if_chain(if_node.orelse[0], iter_var)
            elif len(if_node.orelse) > 0:
                return False
                
        return True

    def transform(self, finding: Finding) -> Optimization:
        node = finding.original_node
        iterable_str = ast.unparse(node.iter)
        
        operations = []
        curr_if = node.body[0]
        while curr_if:
            literal = ast.unparse(curr_if.test.comparators[0])
            aug = curr_if.body[0]
            target = ast.unparse(aug.target)
            op = "+" if isinstance(aug.op, ast.Add) else "-" if isinstance(aug.op, ast.Sub) else None
            value = ast.unparse(aug.value)
            
            operations.append((target, op, literal, value))
            
            if curr_if.orelse and isinstance(curr_if.orelse[0], ast.If):
                curr_if = curr_if.orelse[0]
            else:
                curr_if = None
                
        lines = []
        for target, op, literal, value in operations:
            if op:
                if value == "1":
                    lines.append(f"{target} {op}= {iterable_str}.count({literal})")
                else:
                    lines.append(f"{target} {op}= {iterable_str}.count({literal}) * {value}")
                
        new_code = "\n".join(lines)
        new_ast = ast.parse(new_code).body
        
        return Optimization(
            finding=finding,
            optimized_node=new_ast,
            explanation="Replaced loop with .count() calls."
        )
