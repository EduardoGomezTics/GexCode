import ast
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class Finding:
    rule_id: str
    file_path: str
    line_number: int
    description: str
    original_node: Any
    risk_level: str = "Safe"

@dataclass
class Optimization:
    finding: Finding
    optimized_node: Any
    explanation: str

@dataclass
class AnalysisReport:
    file_path: str
    findings: List[Finding] = field(default_factory=list)

@dataclass
class BenchmarkResult:
    original_time_ms: float
    optimized_time_ms: float
    iterations: int = 1

    @property
    def speedup(self) -> float:
        if self.optimized_time_ms > 0:
            return round(self.original_time_ms / self.optimized_time_ms, 2)
        return 1.0