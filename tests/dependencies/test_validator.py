import pytest

from app.dependencies.exceptions import DependencyResolutionError, DependencyValidationError
from app.dependencies.resolver import DependencyResolver
from app.dependencies.validator import DependencyValidator


def test_validator_package_name_valid():
    """Verify package name validation accepts PyPI standard compliant package names."""
    valid_names = ["pandas", "numpy", "scikit-learn", "requests", "torch", "Pillow", "google-cloud-storage"]
    for name in valid_names:
        assert DependencyValidator.validate_package_name(name) == name


def test_validator_package_name_invalid_and_malicious():
    """Verify package validator rejects malicious shell injection attempts and invalid characters."""
    malicious_inputs = [
        "pandas; rm -rf /",
        "$(malicious_cmd)",
        "package && command",
        "requests|cat /etc/passwd",
        "package`id`",
        "pkg\ncommand",
        "invalid name",
        "",
    ]
    for invalid in malicious_inputs:
        with pytest.raises(DependencyValidationError):
            DependencyValidator.validate_package_name(invalid)


def test_validator_version_specifier_valid():
    """Verify version specifier validation accepts valid standard Python specifiers."""
    valid_specs = [
        ("==2.2.3", "==2.2.3"),
        (">=2.0", ">=2.0"),
        ("<=3.0", "<=3.0"),
        (">=2.0,<3.0", ">=2.0,<3.0"),
        ("2.2.3", "==2.2.3"),
        (None, None),
    ]
    for spec, expected in valid_specs:
        assert DependencyValidator.validate_version_specifier(spec) == expected


def test_validator_version_specifier_invalid():
    """Verify version specifier validator rejects shell metacharacters and invalid operators."""
    invalid_specs = [
        "==2.2; rm -rf /",
        "$(cmd)",
        "==2.0 | ls",
    ]
    for invalid in invalid_specs:
        with pytest.raises(DependencyValidationError):
            DependencyValidator.validate_version_specifier(invalid)


def test_resolver_valid_and_conflict_resolution():
    """Verify DependencyResolver resolves valid specifications and flags version conflicts."""
    packages = [
        {"package_name": "pandas", "version_specifier": "==2.2.3"},
        {"package_name": "requests", "version_specifier": ">=2.31"},
    ]
    resolved = DependencyResolver.resolve_requirements(packages)
    assert len(resolved) == 2

    # Conflict test
    conflicting_packages = [
        {"package_name": "pandas", "version_specifier": "==2.2.3"},
        {"package_name": "pandas", "version_specifier": "==2.1.0"},
    ]
    with pytest.raises(DependencyResolutionError):
        DependencyResolver.resolve_requirements(conflicting_packages)
