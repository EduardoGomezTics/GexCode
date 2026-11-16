import ast
from abc import ABC, abstractmethod
from core.models import Finding, Optimization

class OptimizationRule(ABC):
    """
    Strict contract for any optimization rule in PyOptiX.
    Ensures detection, transformation, and validation are decoupled.
    """
    
    # Mandatory metadata for every rule that inherits from this class
    id: str = "BASE_RULE"
    description: str = "Default description"
    risk_level: str = "Safe"

    @abstractmethod
    def detect(self, tree: ast.AST, file_path: str) -> list[Finding]:
        """
        Scans the Abstract Syntax Tree (AST).
        Must return a list of Findings without modifying the original tree.
        """
        pass

    @abstractmethod
    def transform(self, finding: Finding) -> Optimization:
        """
        Takes a detected Finding and generates a new optimized AST node.
        Returns an Optimization object that the main engine will apply.
        """
        pass

    def validate(self, original_code: str, optimized_code: str) -> bool:
        """
        Optional semantic validation. By default assumes the transformation
        is safe. Complex rules can override this method to compile 
        the bytecode or perform extra static validations.
        """
        try:
            # A quick base validation: ensure the new code compiles
            ast.parse(optimized_code)
            return True
        except SyntaxError:
            return False