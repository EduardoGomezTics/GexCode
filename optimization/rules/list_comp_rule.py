import ast
from core.models import Finding, Optimization
from optimization.base_rule import OptimizationRule

class ListCompRule(OptimizationRule):
    id = "OPT_003"
    description = "Inefficient list appending in loop. Use list comprehension instead."
    risk_level = "Safe"

    def detect(self, tree: ast.AST, file_path: str) -> list[Finding]:
        findings = []
        
        # We need to look at elements within a block (body of FunctionDef, Module, For, If, etc.)
        for node in ast.walk(tree):
            if hasattr(node, 'body') and isinstance(node.body, list):
                self._check_block(node.body, findings, file_path)
            if hasattr(node, 'orelse') and isinstance(node.orelse, list):
                self._check_block(node.orelse, findings, file_path)
            if hasattr(node, 'finalbody') and isinstance(node.finalbody, list):
                self._check_block(node.finalbody, findings, file_path)
                
        return findings

    def _check_block(self, body: list, findings: list, file_path: str):
        for i in range(len(body) - 1):
            stmt1 = body[i]
            stmt2 = body[i+1]
            
            # Check if stmt1 is an assignment to an empty list
            if isinstance(stmt1, ast.Assign) and len(stmt1.targets) == 1:
                target = stmt1.targets[0]
                if isinstance(target, ast.Name) and isinstance(stmt1.value, ast.List) and len(stmt1.value.elts) == 0:
                    list_var_name = target.id
                    
                    # Check if stmt2 is a For loop
                    if isinstance(stmt2, ast.For):
                        # Validate that the last statement is an append to list_var_name
                        if len(stmt2.body) == 0: continue
                        last_stmt = stmt2.body[-1]
                        
                        # All preceding statements must be simple assignments
                        valid = True
                        for stmt in stmt2.body[:-1]:
                            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
                                valid = False
                                break
                        if not valid: continue
                        
                        if isinstance(last_stmt, ast.Expr):
                            expr = last_stmt.value
                            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
                                if expr.func.attr == 'append' and isinstance(expr.func.value, ast.Name) and expr.func.value.id == list_var_name:
                                    # Found the pattern!
                                    finding = Finding(
                                        rule_id=self.id,
                                        file_path=file_path,
                                        line_number=stmt2.lineno,
                                        description=self.description,
                                        original_node=stmt2,
                                        risk_level=self.risk_level
                                    )
                                    finding.node_to_delete = stmt1
                                    findings.append(finding)

    class Inliner(ast.NodeTransformer):
        def __init__(self, mappings):
            self.mappings = mappings
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and node.id in self.mappings:
                return self.mappings[node.id]
            return node

    def transform(self, finding: Finding) -> Optimization:
        for_node = finding.original_node
        assign_node = finding.node_to_delete
        
        list_var_name = assign_node.targets[0].id
        
        # Build mappings from previous assignments
        mappings = {}
        for stmt in for_node.body[:-1]:
            mappings[stmt.targets[0].id] = stmt.value
            
        # The value being appended
        append_call = for_node.body[-1].value
        append_arg = append_call.args[0]
        
        # Inline the assignments into the append argument
        if mappings:
            append_arg = self.Inliner(mappings).visit(append_arg)
        
        # Construct the comprehension
        comp = ast.ListComp(
            elt=append_arg,
            generators=[
                ast.comprehension(
                    target=for_node.target,
                    iter=for_node.iter,
                    ifs=[],
                    is_async=0
                )
            ]
        )
        
        new_assign = ast.Assign(
            targets=[ast.Name(id=list_var_name, ctx=ast.Store())],
            value=comp
        )
        
        opt = Optimization(
            finding=finding,
            optimized_node=new_assign,
            explanation=f"Replaced {list_var_name} = [] and loop with list comprehension."
        )
        opt.nodes_to_remove = [assign_node]
        return opt
