import re
from typing import Optional

from app.dependencies.exceptions import DependencyValidationError

# Strict regex matching valid PyPI / PEP 508 package names
PACKAGE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9_\-\.]*[a-zA-Z0-9])?$")

# Standard Python package version specifier operators
VERSION_SPECIFIER_REGEX = re.compile(
    r"^\s*(==|>=|<=|>|<|~=|!=)\s*([a-zA-Z0-9_\-\.\*]+)(\s*,\s*(==|>=|<=|>|<|~=|!=)\s*([a-zA-Z0-9_\-\.\*]+))*\s*$"
)

# Forbidden shell command characters in package names
FORBIDDEN_NAME_CHARS = {";", "&", "|", "$", "`", "\n", "\r", "\\", "/", "(", ")", "{", "}", "<", ">", "!", "=", " "}

# Forbidden shell command characters in version specifiers (allowing >, <, =)
FORBIDDEN_SPECIFIER_CHARS = {";", "&", "|", "$", "`", "\n", "\r", "\\", "/", "(", ")", "{", "}", "!"}


class DependencyValidator:
    """Validator ensuring package identifiers and version specifiers are safe and standard."""

    @classmethod
    def validate_package_name(cls, package_name: str) -> str:
        """Validate package name syntax and security constraints."""
        if not package_name or not isinstance(package_name, str):
            raise DependencyValidationError(
                str(package_name), "Package name must be a non-empty string."
            )

        name = package_name.strip()

        # Check for forbidden shell metacharacters
        for char in FORBIDDEN_NAME_CHARS:
            if char in name:
                raise DependencyValidationError(
                    name, f"Package name contains forbidden character '{char}'."
                )

        if not PACKAGE_NAME_REGEX.match(name):
            raise DependencyValidationError(
                name,
                "Package name must contain only alphanumeric characters, hyphens, underscores, or dots, and start/end with an alphanumeric character.",
            )

        return name

    @classmethod
    def validate_version_specifier(cls, specifier: Optional[str]) -> Optional[str]:
        """Validate standard Python version specifier syntax (e.g., '==2.2.3', '>=2.0,<3.0')."""
        if specifier is None or not specifier.strip():
            return None

        spec = specifier.strip()

        # Check for forbidden shell characters
        for char in FORBIDDEN_SPECIFIER_CHARS:
            if char in spec:
                raise DependencyValidationError(
                    spec, f"Version specifier contains forbidden character '{char}'."
                )

        # Allow simple version string without operator (assume ==)
        if re.match(r"^[0-9]+(\.[0-9a-zA-Z]+)*$", spec):
            spec = f"=={spec}"

        if not VERSION_SPECIFIER_REGEX.match(spec):
            raise DependencyValidationError(
                spec,
                "Version specifier must be a valid Python specifier (e.g. '==2.2.3', '>=2.0', '>=2.0,<3.0').",
            )

        return spec

    @classmethod
    def format_requirement(cls, package_name: str, version_specifier: Optional[str] = None) -> str:
        """Validate and format package_name and optional specifier into a clean requirement string."""
        valid_name = cls.validate_package_name(package_name)
        valid_spec = cls.validate_version_specifier(version_specifier)
        if valid_spec:
            return f"{valid_name}{valid_spec}"
        return valid_name
