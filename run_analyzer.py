import ast
from core.models import AnalysisReport
from optimization.rules.range_len_rule import RangeLenRule

class PyOptixEngine:
    def __init__(self):
        self.rules = []
        
    def register_rule(self, rule):
        self.rules.append(rule)
        
    def analyze_file(self, file_path: str) -> AnalysisReport:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            
        tree = ast.parse(source)
        report = AnalysisReport(file_path=file_path)
        
        for rule in self.rules:
            findings = rule.detect(tree, file_path)
            report.findings.extend(findings)
            
        return report

if __name__ == "__main__":
    # Initialize engine and register our first rule
    engine = PyOptixEngine()
    engine.register_rule(RangeLenRule())
    
    # Run analysis on the dummy target
    target_file = "dummy_target.py"
    print(f"🚀 Running PyOptiX Analysis on {target_file}...\n")
    report = engine.analyze_file(target_file)
    
    if not report.findings:
        print("✅ No inefficiencies found.")
    else:
        print(f"⚠️  Found {len(report.findings)} inefficiencies:")
        for finding in report.findings:
            print(f"  [{finding.rule_id}] Line {finding.line_number}: {finding.description}")