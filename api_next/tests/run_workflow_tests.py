#!/usr/bin/env python3
# Copyright (c) 2025, API Industrial Services Inc. and contributors
# For license information, please see license.txt

"""
Job Workflow Engine Test Runner
===============================

Comprehensive test runner for the Job Workflow Engine with TDD approach.
Supports multiple test execution modes, coverage reporting, and performance analysis.

Usage:
    python run_workflow_tests.py [options]

Examples:
    # Run all workflow tests
    python run_workflow_tests.py

    # Run only unit tests
    python run_workflow_tests.py --category unit

    # Run performance tests with detailed reporting
    python run_workflow_tests.py --category performance --detailed

    # Run specific test file
    python run_workflow_tests.py --file test_job_workflow_engine.py

    # Generate coverage report
    python run_workflow_tests.py --coverage --html-report

    # Run smoke tests (quick validation)
    python run_workflow_tests.py --smoke
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path


class WorkflowTestRunner:
    """Main test runner for workflow engine tests."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.app_dir = self.test_dir.parent.parent
        self.coverage_threshold = 80.0
        
    def run_tests(self, args):
        """Execute tests based on provided arguments."""
        start_time = time.time()
        
        print("=" * 80)
        print("API_Next Job Workflow Engine Test Suite")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test directory: {self.test_dir}")
        print(f"Coverage threshold: {self.coverage_threshold}%")
        print("-" * 80)
        
        # Build pytest command
        cmd = self._build_pytest_command(args)
        
        print(f"Command: {' '.join(cmd)}")
        print("-" * 80)
        
        try:
            # Execute tests
            result = subprocess.run(cmd, cwd=self.app_dir, capture_output=False)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print("-" * 80)
            print(f"Test execution completed in {duration:.2f} seconds")
            
            if result.returncode == 0:
                print("✅ All tests passed!")
                
                if args.coverage:
                    self._display_coverage_summary()
                    
                if args.performance_report:
                    self._generate_performance_report()
                    
            else:
                print("❌ Some tests failed!")
                
            return result.returncode
            
        except KeyboardInterrupt:
            print("\n❌ Test execution interrupted by user")
            return 130
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return 1
    
    def _build_pytest_command(self, args):
        """Build pytest command based on arguments."""
        cmd = ["python", "-m", "pytest"]
        
        # Base options
        cmd.extend([
            "--verbose",
            "--tb=short",
            "--disable-warnings"
        ])
        
        # Coverage options
        if args.coverage:
            cmd.extend([
                "--cov=api_next.workflows",
                "--cov=api_next.job_management.doctype.job_order",
                "--cov-report=term-missing",
                f"--cov-fail-under={self.coverage_threshold}",
                "--cov-branch"
            ])
            
            if args.html_report:
                cmd.extend(["--cov-report=html:htmlcov"])
                
            if args.xml_report:
                cmd.extend(["--cov-report=xml:coverage.xml"])
        
        # Test selection
        if args.category:
            cmd.extend(["-m", args.category])
        elif args.smoke:
            cmd.extend(["-m", "smoke"])
        elif args.quick:
            cmd.extend(["-m", "not slow"])
        
        # Specific test file
        if args.file:
            test_file = self.test_dir / args.file
            cmd.append(str(test_file))
        else:
            cmd.append(str(self.test_dir))
        
        # Performance options
        if args.durations:
            cmd.extend(["--durations", str(args.durations)])
        
        # Parallel execution
        if args.parallel:
            cmd.extend(["-n", "auto"])
        
        # Output options
        if args.quiet:
            cmd.extend(["-q"])
        elif args.detailed:
            cmd.extend(["-v", "-s"])
        
        # JUnit XML output for CI
        if args.junit:
            cmd.extend(["--junitxml=test-results.xml"])
        
        return cmd
    
    def _display_coverage_summary(self):
        """Display coverage summary if coverage report exists."""
        coverage_file = self.app_dir / ".coverage"
        if coverage_file.exists():
            print("\n📊 Coverage Summary:")
            try:
                subprocess.run(["python", "-m", "coverage", "report", "--show-missing"], 
                             cwd=self.app_dir, check=True)
            except subprocess.CalledProcessError:
                print("Could not generate coverage report")
    
    def _generate_performance_report(self):
        """Generate performance analysis report."""
        print("\n⚡ Performance Report:")
        print("Performance metrics available in test output above")
        print("Look for timing information and performance test results")
    
    def _validate_environment(self):
        """Validate test environment before running tests."""
        print("🔍 Validating test environment...")
        
        # Check if we're in a Frappe environment
        try:
            import frappe
            print("✅ Frappe framework available")
        except ImportError:
            print("❌ Frappe framework not available")
            return False
        
        # Check if required test dependencies are available
        try:
            import pytest
            import coverage
            print("✅ Test dependencies available")
        except ImportError as e:
            print(f"❌ Missing test dependency: {e}")
            return False
        
        # Check if API_Next app is installed
        try:
            from api_next.workflows.job_order_workflow import JobOrderWorkflow
            print("✅ API_Next workflow engine available")
        except ImportError:
            print("❌ API_Next workflow engine not available")
            return False
        
        return True
    
    def setup_test_environment(self):
        """Set up test environment."""
        print("🔧 Setting up test environment...")
        
        # Ensure test database is available
        os.environ.setdefault("FRAPPE_SITE", "test_site")
        
        # Set testing flag
        os.environ["TESTING"] = "1"
        
        print("✅ Test environment configured")
    
    def cleanup_test_environment(self):
        """Clean up after tests."""
        print("🧹 Cleaning up test environment...")
        
        # Remove test files if needed
        temp_files = [
            self.app_dir / "test-results.xml",
            self.app_dir / ".coverage"
        ]
        
        for temp_file in temp_files:
            if temp_file.exists() and not args.keep_artifacts:
                temp_file.unlink()
                print(f"Removed {temp_file}")
        
        print("✅ Cleanup completed")


def create_test_report_template():
    """Create HTML test report template."""
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>API_Next Workflow Engine Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .metric { background-color: #e9ecef; padding: 15px; border-radius: 5px; flex: 1; text-align: center; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .coverage { color: #007bff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Job Workflow Engine Test Report</h1>
        <p>Generated on: {datetime}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Tests Run</h3>
            <p class="count">{total_tests}</p>
        </div>
        <div class="metric">
            <h3>Passed</h3>
            <p class="passed">{passed_tests}</p>
        </div>
        <div class="metric">
            <h3>Failed</h3>
            <p class="failed">{failed_tests}</p>
        </div>
        <div class="metric">
            <h3>Coverage</h3>
            <p class="coverage">{coverage_percent}%</p>
        </div>
    </div>
    
    <div class="details">
        <h2>Test Categories</h2>
        <ul>
            <li>Unit Tests: Individual component testing</li>
            <li>Integration Tests: End-to-end workflow scenarios</li>
            <li>Security Tests: Permission and validation checks</li>
            <li>Performance Tests: Load and response time validation</li>
            <li>Edge Case Tests: Boundary conditions and error states</li>
        </ul>
    </div>
</body>
</html>
    """
    return template


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Job Workflow Engine Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection options
    parser.add_argument(
        "--category", "-c",
        choices=["unit", "integration", "api", "workflow", "security", "performance", "edge_case"],
        help="Run specific test category"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Run specific test file"
    )
    
    parser.add_argument(
        "--smoke", "-s",
        action="store_true",
        help="Run quick smoke tests only"
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true", 
        help="Skip slow tests"
    )
    
    # Coverage options
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--xml-report",
        action="store_true",
        help="Generate XML coverage report"
    )
    
    # Output options
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Detailed test output"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    parser.add_argument(
        "--junit",
        action="store_true",
        help="Generate JUnit XML for CI systems"
    )
    
    # Performance options
    parser.add_argument(
        "--durations",
        type=int,
        default=10,
        help="Show N slowest test durations"
    )
    
    parser.add_argument(
        "--performance-report",
        action="store_true",
        help="Generate detailed performance report"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep test artifacts after completion"
    )
    
    # Environment options
    parser.add_argument(
        "--no-setup",
        action="store_true",
        help="Skip test environment setup"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = WorkflowTestRunner()
    
    try:
        # Validate environment
        if not runner._validate_environment():
            sys.exit(1)
        
        # Setup test environment
        if not args.no_setup:
            runner.setup_test_environment()
        
        # Run tests
        exit_code = runner.run_tests(args)
        
        # Cleanup
        runner.cleanup_test_environment()
        
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()