# Job Workflow Engine Test Infrastructure

## Overview

This comprehensive test infrastructure is designed to achieve >80% code coverage for the API_Next Job Workflow Engine using Test-Driven Development (TDD) principles. The infrastructure includes unit tests, integration tests, security tests, performance tests, and edge case validation.

## Test Suite Structure

```
api_next/tests/
├── conftest.py                      # Pytest configuration and fixtures
├── pytest.ini                      # Pytest settings and markers
├── run_workflow_tests.py           # Comprehensive test runner
├── test_workflow_helpers.py        # Test utilities and helpers
├── test_job_workflow_engine.py     # Main workflow engine tests
├── test_job_workflow.py            # Legacy workflow tests  
├── test_*.py                        # Other test modules
├── fixtures/
│   └── job_order_data.json         # Test data fixtures
└── README_TEST_INFRASTRUCTURE.md   # This documentation
```

## Test Categories

### 1. Unit Tests (`@pytest.mark.unit`)
- Individual component testing
- Workflow phase configuration validation
- Transition validation logic
- Business rule validation
- Error handling and edge cases

### 2. Integration Tests (`@pytest.mark.integration`)
- End-to-end workflow scenarios
- Complete workflow execution paths
- Multi-phase transitions
- Database transaction handling
- External service integration

### 3. Security Tests (`@pytest.mark.security`)
- Role-based access control validation
- Permission enforcement testing
- SQL injection prevention
- XSS attack prevention
- Privilege escalation testing
- Data validation security

### 4. Performance Tests (`@pytest.mark.performance`)
- Single operation performance benchmarking
- Bulk operation load testing
- Memory usage monitoring
- Concurrent access testing
- Response time validation

### 5. Edge Case Tests (`@pytest.mark.edge_case`)
- Boundary condition testing
- Invalid input handling
- Corrupted state recovery
- Extreme value processing
- Concurrent modification handling

## Quick Start

### Running All Tests
```bash
cd apps/api_next/api_next/tests
python run_workflow_tests.py --coverage --html-report
```

### Running Specific Test Categories
```bash
# Unit tests only
python run_workflow_tests.py --category unit

# Integration tests
python run_workflow_tests.py --category integration

# Security tests
python run_workflow_tests.py --category security

# Performance tests
python run_workflow_tests.py --category performance
```

### Running with Coverage
```bash
# Generate HTML coverage report
python run_workflow_tests.py --coverage --html-report

# Generate XML coverage report (for CI)
python run_workflow_tests.py --coverage --xml-report --junit
```

### Quick Smoke Tests
```bash
# Run quick validation tests
python run_workflow_tests.py --smoke

# Skip slow tests
python run_workflow_tests.py --quick
```

## Test Data Management

### Fixtures System
The test infrastructure uses a comprehensive fixture system with realistic test data:

- **Test Scenarios**: Pre-defined job order scenarios (minimal, complete, urgent, cancelled)
- **Workflow Data**: Phase transition rules, validation requirements, permission matrices
- **Edge Cases**: Invalid data, security payloads, performance test data
- **User Roles**: Complete user role definitions with permissions

### Using Fixtures in Tests
```python
from api_next.tests.test_workflow_helpers import (
    create_test_job_order, create_complete_job_order,
    workflow_data, workflow_assertions
)

# Create test job order from scenario
job_order = create_test_job_order("complete_job_order")

# Use workflow assertions
workflow_assertions.assert_transition_succeeded(result, "Estimation")
```

### Builder Pattern for Custom Test Data
```python
from api_next.tests.test_workflow_helpers import JobOrderBuilder

job_order = (JobOrderBuilder()
    .from_scenario("minimal_job_order")
    .with_workflow_state("Planning")
    .with_materials(count=5, total_cost=10000.0)
    .with_labor(count=3, total_hours=120.0)
    .with_documents(count=3)
    .build())
```

## Mock System

The infrastructure includes comprehensive mocking for external dependencies:

### Notification Mocking
```python
with workflow_mocks.mock_notifications() as mocks:
    # Test workflow transitions without sending actual notifications
    result = JobOrderWorkflow.execute_transition(job_order, "Estimation")
    assert mocks["sendmail"].called
```

### Database Transaction Mocking
```python
with workflow_mocks.mock_database_operations() as db_mocks:
    # Test transaction handling
    result = JobOrderWorkflow.execute_transition(job_order, "Planning")
    db_mocks["begin"].assert_called_once()
    db_mocks["commit"].assert_called_once()
```

### User Role Mocking
```python
with workflow_mocks.mock_user_roles(["Project Manager", "Employee"]):
    # Test with specific roles
    result = JobOrderWorkflow.validate_transition(job_order, "Submission", "Planning")
```

## Performance Monitoring

### Performance Measurement
```python
from api_next.tests.test_workflow_helpers import workflow_performance

with workflow_performance.measure_operation("transition_validation"):
    result = JobOrderWorkflow.validate_transition(job_order, "Submission", "Estimation")

# Get performance metrics
avg_time = workflow_performance.get_average_execution_time("transition_validation")
slowest = workflow_performance.get_slowest_operations(5)
```

### Performance Thresholds
- Single transition validation: < 100ms
- Bulk operations (20 items): < 2 seconds
- Complex workflow scenarios: < 1 second
- Memory growth under load: < 20%

## Security Testing

### SQL Injection Testing
```python
from api_next.tests.test_workflow_helpers import workflow_security

# Test with malicious payloads
payloads = workflow_security.get_sql_injection_payloads()
for payload in payloads:
    malicious_job = workflow_security.create_malicious_job_order(
        "sql_injection", "job_title"
    )
    # Verify system handles malicious input safely
```

### Privilege Escalation Testing
```python
# Test privilege escalation prevention
is_vulnerable = workflow_security.test_privilege_escalation(
    low_privilege_roles=["Employee"],
    high_privilege_operation=lambda: JobOrderWorkflow.validate_transition(
        job_order, "Submission", "Planning"
    )
)
assert not is_vulnerable, "Privilege escalation vulnerability detected"
```

## Custom Assertions

The infrastructure provides workflow-specific assertions:

```python
from api_next.tests.test_workflow_helpers import workflow_assertions

# Assert successful transition
workflow_assertions.assert_transition_succeeded(result, "Estimation")

# Assert validation failure
workflow_assertions.assert_validation_failed(result, "Missing required fields")

# Assert workflow state
workflow_assertions.assert_workflow_state(job_order, "Planning")

# Assert performance threshold
workflow_assertions.assert_performance_threshold(0.05, 0.1, "validation")

# Assert required fields
workflow_assertions.assert_required_fields_present(job_order, ["customer_name", "job_type"])
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Job Workflow Engine Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          cd apps/api_next/api_next/tests
          python run_workflow_tests.py --coverage --xml-report --junit
      - name: Upload coverage
        uses: codecov/codecov-action@v1
        with:
          file: ./coverage.xml
```

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh '''
                    cd apps/api_next/api_next/tests
                    python run_workflow_tests.py --coverage --xml-report --junit
                '''
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'test-results.xml'
                    publishCoverageReport coverageReportPattern: 'coverage.xml'
                }
            }
        }
    }
}
```

## Coverage Requirements

The test infrastructure enforces minimum coverage thresholds:

- **Overall Coverage**: 80% minimum
- **Branch Coverage**: Enabled for all conditional logic
- **Workflow Engine Core**: 95% minimum coverage
- **Business Logic**: 90% minimum coverage
- **Edge Cases**: 100% coverage for error handling

### Coverage Report Locations
- **Terminal**: Displayed during test execution
- **HTML Report**: `htmlcov/index.html`
- **XML Report**: `coverage.xml` (for CI systems)

## Test Execution Strategies

### Local Development
```bash
# Quick smoke tests during development
python run_workflow_tests.py --smoke

# Run tests for specific file you're working on
python run_workflow_tests.py --file test_job_workflow_engine.py --detailed

# Full test suite with coverage
python run_workflow_tests.py --coverage --html-report
```

### Pre-commit Testing
```bash
# Run all tests except slow ones
python run_workflow_tests.py --quick --coverage

# Run only unit and integration tests
python run_workflow_tests.py --category unit
python run_workflow_tests.py --category integration
```

### Comprehensive Testing
```bash
# Full test suite with all reports
python run_workflow_tests.py \
    --coverage \
    --html-report \
    --xml-report \
    --junit \
    --performance-report \
    --detailed
```

## Troubleshooting

### Common Issues

1. **Frappe Not Available**
   - Ensure you're running from within a Frappe environment
   - Check that `bench` command is available
   - Verify API_Next app is installed

2. **Database Connection Issues**
   - Ensure test database is available
   - Check database permissions
   - Verify test site configuration

3. **Permission Errors**
   - Run tests as appropriate user
   - Check file permissions on test directory
   - Ensure Frappe user has necessary database privileges

4. **Coverage Too Low**
   - Check which files are not covered
   - Add tests for uncovered code paths
   - Verify test discovery is finding all test files

### Debug Mode
```bash
# Run with detailed output and no capture
python run_workflow_tests.py --detailed -s

# Run single test with debugging
pytest -xvs test_job_workflow_engine.py::TestJobWorkflowEngineCore::test_workflow_phase_configuration_completeness
```

## Best Practices

### Writing Tests
1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: Test names should describe the scenario
3. **Test One Thing**: Each test should verify one specific behavior
4. **Use Fixtures**: Leverage existing fixtures for consistent test data
5. **Mock External Dependencies**: Use mocks to isolate units under test

### Test Data
1. **Use Realistic Data**: Test data should mirror production scenarios
2. **Test Edge Cases**: Include boundary conditions and invalid inputs
3. **Maintain Fixtures**: Keep fixture data up-to-date with schema changes
4. **Document Test Scenarios**: Clearly describe what each scenario tests

### Performance Testing
1. **Set Clear Thresholds**: Define acceptable performance metrics
2. **Test Under Load**: Verify behavior with realistic data volumes
3. **Monitor Resource Usage**: Check memory and CPU consumption
4. **Document Performance Requirements**: Clearly state performance expectations

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Use appropriate test markers (`@pytest.mark.unit`, etc.)
3. Add comprehensive docstrings
4. Update fixtures if needed
5. Ensure new tests pass coverage requirements
6. Add performance benchmarks for new features

## Support

For issues with the test infrastructure:

1. Check the troubleshooting section above
2. Review test logs for specific error messages
3. Verify test environment setup
4. Consult the existing test examples for patterns

---

**Test Infrastructure Version**: 1.0  
**Last Updated**: 2025-01-09  
**Minimum Coverage Target**: 80%  
**Framework**: pytest + Frappe Test Runner