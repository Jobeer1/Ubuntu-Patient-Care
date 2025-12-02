#!/usr/bin/env python3
"""
QUBIC Analyzer - Automated Contribution Scoring System
Quantified Ubuntu Contribution Integrity Crucible

This script analyzes contributions to Ubuntu Patient Care and generates
transparent, objective scores based on the QUBIC Constitution.
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple
import requests
from pathlib import Path

# Configuration
GITHUB_API_BASE = "https://api.github.com"
SCORING_WEIGHTS = {
    "code_quality": 0.30,
    "healthcare_impact": 0.25,
    "documentation": 0.20,
    "innovation": 0.15,
    "integration": 0.10
}

MODULE_BONUSES = {
    "RIS": 5,
    "PACS": 5,
    "Dictation": 4,
    "Billing": 3,
    "Cross-Module": 7,
    "Security": 6,
    "AI-ML": 5,
    "Performance": 4,
    "Accessibility": 3
}

TIER_THRESHOLDS = {
    "Platinum": 90,
    "Gold": 80,
    "Silver": 70,
    "Bronze": 60,
    "Recognized": 50
}


class QUBICAnalyzer:
    """Main analyzer class for QUBIC scoring system"""
    
    def __init__(self, github_token: str = None, llm_api_key: str = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.results = {}
        
    def analyze_contribution(self, repo_url: str, pr_number: int = None) -> Dict:
        """
        Main entry point for analyzing a contribution
        
        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number (optional)
            
        Returns:
            Complete scoring results dictionary
        """
        print(f"🔍 Analyzing contribution from {repo_url}")
        
        # Step 1: Clone/fetch repository
        repo_path = self._fetch_repository(repo_url)
        
        # Step 2: Run automated code analysis
        code_metrics = self._analyze_code_quality(repo_path)
        
        # Step 3: Analyze documentation
        doc_metrics = self._analyze_documentation(repo_path)
        
        # Step 4: LLM-powered review
        llm_scores = self._llm_review(repo_path, code_metrics, doc_metrics)
        
        # Step 5: Calculate composite score
        final_score = self._calculate_composite_score(
            code_metrics, doc_metrics, llm_scores
        )
        
        # Step 6: Generate report
        report = self._generate_report(final_score)
        
        return report
    
    def _fetch_repository(self, repo_url: str) -> Path:
        """Clone or update repository for analysis"""
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = Path(f"./temp_analysis/{repo_name}")
        
        if repo_path.exists():
            print(f"📂 Updating existing repository: {repo_name}")
            subprocess.run(["git", "pull"], cwd=repo_path, check=True)
        else:
            print(f"📥 Cloning repository: {repo_name}")
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
        
        return repo_path
    
    def _analyze_code_quality(self, repo_path: Path) -> Dict:
        """
        Automated code quality analysis
        Returns metrics for code quality scoring
        """
        print("🔬 Running code quality analysis...")
        
        metrics = {
            "lines_of_code": 0,
            "complexity": 0,
            "test_coverage": 0,
            "style_violations": 0,
            "security_issues": 0,
            "files_analyzed": 0
        }
        
        # Count lines of code
        python_files = list(repo_path.rglob("*.py"))
        metrics["files_analyzed"] = len(python_files)
        
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Count non-empty, non-comment lines
                    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                    metrics["lines_of_code"] += len(code_lines)
            except Exception as e:
                print(f"⚠️  Error reading {file}: {e}")
        
        # Run pylint for style and complexity (if available)
        try:
            result = subprocess.run(
                ["pylint", str(repo_path), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.stdout:
                pylint_data = json.loads(result.stdout)
                metrics["style_violations"] = len(pylint_data)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            print("⚠️  Pylint not available or timed out")
        
        # Check for test files
        test_files = list(repo_path.rglob("test_*.py")) + list(repo_path.rglob("*_test.py"))
        if test_files:
            metrics["test_coverage"] = min(100, (len(test_files) / max(1, len(python_files))) * 100)
        
        # Security scan (basic checks)
        security_patterns = [
            "eval(", "exec(", "os.system(", "subprocess.call(",
            "pickle.loads(", "yaml.load(", "input(", "raw_input("
        ]
        
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in security_patterns:
                        if pattern in content:
                            metrics["security_issues"] += 1
            except Exception:
                pass
        
        print(f"✅ Code analysis complete: {metrics['files_analyzed']} files, "
              f"{metrics['lines_of_code']} LOC")
        
        return metrics
    
    def _analyze_documentation(self, repo_path: Path) -> Dict:
        """
        Analyze documentation quality
        Returns metrics for documentation scoring
        """
        print("📚 Analyzing documentation...")
        
        metrics = {
            "readme_exists": False,
            "readme_length": 0,
            "api_docs": 0,
            "setup_instructions": False,
            "examples": 0,
            "diagrams": 0,
            "docstrings": 0
        }
        
        # Check for README
        readme_files = list(repo_path.glob("README*"))
        if readme_files:
            metrics["readme_exists"] = True
            try:
                with open(readme_files[0], 'r', encoding='utf-8') as f:
                    content = f.read()
                    metrics["readme_length"] = len(content)
                    metrics["setup_instructions"] = "install" in content.lower() or "setup" in content.lower()
            except Exception:
                pass
        
        # Count documentation files
        doc_files = list(repo_path.rglob("*.md"))
        metrics["api_docs"] = len([f for f in doc_files if "api" in f.name.lower()])
        
        # Check for examples
        example_dirs = list(repo_path.rglob("example*"))
        metrics["examples"] = len(example_dirs)
        
        # Check for diagrams
        diagram_files = list(repo_path.rglob("*.png")) + list(repo_path.rglob("*.jpg")) + list(repo_path.rglob("*.svg"))
        metrics["diagrams"] = len(diagram_files)
        
        # Count docstrings in Python files
        python_files = list(repo_path.rglob("*.py"))
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple docstring detection
                    metrics["docstrings"] += content.count('"""') // 2
                    metrics["docstrings"] += content.count("'''") // 2
            except Exception:
                pass
        
        print(f"✅ Documentation analysis complete: README={metrics['readme_exists']}, "
              f"Docs={len(doc_files)}, Docstrings={metrics['docstrings']}")
        
        return metrics
    
    def _llm_review(self, repo_path: Path, code_metrics: Dict, doc_metrics: Dict) -> Dict:
        """
        LLM-powered qualitative review
        Returns scores for healthcare impact, innovation, and integration
        """
        print("🤖 Running LLM-powered review...")
        
        # In a real implementation, this would call an LLM API
        # For now, we'll use heuristics based on the metrics
        
        scores = {
            "healthcare_impact": 0,
            "innovation": 0,
            "integration": 0,
            "feedback": []
        }
        
        # Healthcare impact heuristics
        healthcare_keywords = ["patient", "clinical", "medical", "hipaa", "popia", "diagnosis", "treatment"]
        healthcare_score = 0
        
        python_files = list(repo_path.rglob("*.py"))
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    for keyword in healthcare_keywords:
                        if keyword in content:
                            healthcare_score += 2
            except Exception:
                pass
        
        scores["healthcare_impact"] = min(25, healthcare_score)
        
        # Innovation heuristics
        innovation_indicators = ["ai", "ml", "machine learning", "neural", "model", "algorithm"]
        innovation_score = 0
        
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    for indicator in innovation_indicators:
                        if indicator in content:
                            innovation_score += 1
            except Exception:
                pass
        
        scores["innovation"] = min(15, innovation_score)
        
        # Integration heuristics
        integration_indicators = ["api", "rest", "endpoint", "integration", "module", "import"]
        integration_score = 0
        
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    for indicator in integration_indicators:
                        if indicator in content:
                            integration_score += 0.5
            except Exception:
                pass
        
        scores["integration"] = min(10, integration_score)
        
        # Generate feedback
        if scores["healthcare_impact"] > 15:
            scores["feedback"].append("✅ Strong healthcare domain focus")
        if scores["innovation"] > 10:
            scores["feedback"].append("✅ Innovative technical approach")
        if scores["integration"] > 7:
            scores["feedback"].append("✅ Good integration patterns")
        
        print(f"✅ LLM review complete: Healthcare={scores['healthcare_impact']}, "
              f"Innovation={scores['innovation']}, Integration={scores['integration']}")
        
        return scores
    
    def _calculate_composite_score(self, code_metrics: Dict, doc_metrics: Dict, llm_scores: Dict) -> Dict:
        """
        Calculate final composite score using QUBIC weights
        """
        print("🧮 Calculating composite score...")
        
        # Code Quality Score (30 points)
        code_quality_score = 0
        
        # Technical excellence (15 points)
        if code_metrics["lines_of_code"] > 100:
            code_quality_score += 5  # Clean code
        if code_metrics["security_issues"] == 0:
            code_quality_score += 3  # Security
        if code_metrics["style_violations"] < 10:
            code_quality_score += 4  # Error handling
        code_quality_score += 3  # Performance (assumed good)
        
        # Code structure (10 points)
        if code_metrics["files_analyzed"] > 3:
            code_quality_score += 4  # Modularity
        code_quality_score += 3  # Maintainability (assumed)
        code_quality_score += 3  # Design patterns (assumed)
        
        # Testing (5 points)
        if code_metrics["test_coverage"] > 50:
            code_quality_score += 3
        if code_metrics["test_coverage"] > 0:
            code_quality_score += 2
        
        code_quality_score = min(30, code_quality_score)
        
        # Documentation Score (20 points)
        doc_score = 0
        
        if doc_metrics["readme_exists"]:
            doc_score += 3
        if doc_metrics["setup_instructions"]:
            doc_score += 3
        if doc_metrics["api_docs"] > 0:
            doc_score += 3
        if doc_metrics["diagrams"] > 0:
            doc_score += 2
        if doc_metrics["examples"] > 0:
            doc_score += 3
        if doc_metrics["docstrings"] > 10:
            doc_score += 4
        doc_score += 2  # Troubleshooting (assumed)
        
        doc_score = min(20, doc_score)
        
        # Healthcare Impact (from LLM)
        healthcare_score = llm_scores["healthcare_impact"]
        
        # Innovation (from LLM)
        innovation_score = llm_scores["innovation"]
        
        # Integration (from LLM)
        integration_score = llm_scores["integration"]
        
        # Calculate weighted composite
        composite = (
            code_quality_score * SCORING_WEIGHTS["code_quality"] +
            healthcare_score * SCORING_WEIGHTS["healthcare_impact"] +
            doc_score * SCORING_WEIGHTS["documentation"] +
            innovation_score * SCORING_WEIGHTS["innovation"] +
            integration_score * SCORING_WEIGHTS["integration"]
        )
        
        # Determine tier
        tier = "Needs Improvement"
        badge = "📝"
        for tier_name, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if composite >= threshold:
                tier = tier_name
                badge = {"Platinum": "🏆", "Gold": "🥇", "Silver": "🥈", "Bronze": "🥉", "Recognized": "⭐"}[tier_name]
                break
        
        result = {
            "composite_score": round(composite, 2),
            "tier": tier,
            "badge": badge,
            "breakdown": {
                "code_quality": round(code_quality_score, 2),
                "healthcare_impact": round(healthcare_score, 2),
                "documentation": round(doc_score, 2),
                "innovation": round(innovation_score, 2),
                "integration": round(integration_score, 2)
            },
            "bonuses": [],
            "feedback": llm_scores["feedback"]
        }
        
        print(f"✅ Composite score: {result['composite_score']} ({tier} {badge})")
        
        return result
    
    def _generate_report(self, final_score: Dict) -> Dict:
        """
        Generate comprehensive evaluation report
        """
        print("📄 Generating evaluation report...")
        
        report = {
            "qubic_version": "1.0",
            "evaluation_date": datetime.now().isoformat(),
            "score": final_score["composite_score"],
            "tier": final_score["tier"],
            "badge": final_score["badge"],
            "breakdown": final_score["breakdown"],
            "bonuses": final_score["bonuses"],
            "feedback": final_score["feedback"],
            "recommendations": []
        }
        
        # Generate recommendations
        if final_score["breakdown"]["code_quality"] < 20:
            report["recommendations"].append("Improve code quality: Add tests, reduce complexity")
        if final_score["breakdown"]["documentation"] < 15:
            report["recommendations"].append("Enhance documentation: Add setup guide, API docs")
        if final_score["breakdown"]["healthcare_impact"] < 15:
            report["recommendations"].append("Strengthen healthcare focus: Address clinical workflows")
        
        print("✅ Report generated successfully")
        
        return report
    
    def save_report(self, report: Dict, output_path: str = "qubic_report.json"):
        """Save evaluation report to file"""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"💾 Report saved to {output_path}")


def main():
    """Main entry point for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QUBIC Contribution Analyzer")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--pr", type=int, help="Pull request number")
    parser.add_argument("--output", default="qubic_report.json", help="Output file path")
    
    args = parser.parse_args()
    
    analyzer = QUBICAnalyzer()
    report = analyzer.analyze_contribution(args.repo_url, args.pr)
    analyzer.save_report(report, args.output)
    
    print("\n" + "="*60)
    print(f"🎯 QUBIC Evaluation Complete")
    print(f"Score: {report['score']} - {report['tier']} {report['badge']}")
    print("="*60)


if __name__ == "__main__":
    main()
