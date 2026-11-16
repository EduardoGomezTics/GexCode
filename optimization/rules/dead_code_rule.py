import ast
from core.models import Finding, Optimization
from optimization.base_rule import OptimizationRule

class DeadCodeRule(OptimizationRule):
    id = "OPT_004"
    description = "Dead code detected: Variable is assigned but never read"
    risk_level = "Medium"

    def detect(self, tree: ast.AST, file_path: str) -> list[Finding]:
        findings = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._analyze_function(node, findings, file_path)
                
        return findings

    def _analyze_function(self, func_node: ast.FunctionDef, findings: list, file_path: str):
        # 1. Collect all genuine reads
        loaded_vars = set()
        for child in ast.walk(func_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                loaded_vars.add(child.id)
                
        # 2. Collect all assignments (Assign, AugAssign) by variable
        assignments_by_var = {}
        for stmt in func_node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                    assignments_by_var.setdefault(target.id, []).append(stmt)
            elif isinstance(stmt, ast.AugAssign):
                target = stmt.target
                if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                    assignments_by_var.setdefault(target.id, []).append(stmt)
                    
        # 3. For any variable that has assignments but NO genuine loads, flag ALL its assignment statements as dead!
        for var_name, stmts in assignments_by_var.items():
            if var_name not in loaded_vars and not var_name.startswith('_'):
                finding = Finding(
                    rule_id=self.id,
                    file_path=file_path,
                    line_number=stmts[0].lineno,
                    description=f"{self.description} ({var_name})",
                    original_node=stmts[0],
                    risk_level=self.risk_level
                )
                finding.nodes_to_remove = stmts
                findings.append(finding)

    def transform(self, finding: Finding) -> Optimization:
        opt = Optimization(
            finding=finding,
            optimized_node=ast.Pass(), # Not used because it will be removed
            explanation=finding.description
        )
        opt.nodes_to_remove = getattr(finding, 'nodes_to_remove', [finding.original_node])
        return opt
