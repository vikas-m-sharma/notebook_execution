from typing import Any

from app.dependencies.exceptions import DependencyResolutionError, DependencyValidationError
from app.dependencies.validator import DependencyValidator


class DependencyResolver:
    """Resolver for validating and normalizing notebook dependency package specifications."""

    @classmethod
    def resolve_requirements(cls, packages: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Validate and resolve a list of package specification dicts.

        Input structure:
        [
            {"package_name": "pandas", "version_specifier": "==2.2.3"},
            {"package_name": "requests", "version_specifier": ">=2.31"}
        ]
        or simple strings passed as package_name.
        """
        if not isinstance(packages, list):
            raise DependencyResolutionError("Packages requirement input must be a list.")

        resolved_map: dict[str, dict[str, str]] = {}

        for item in packages:
            if isinstance(item, str):
                # Simple string format like "pandas==2.2.3" or "pandas"
                parts = item.split("==", 1)
                pkg_name = parts[0]
                version_spec = f"=={parts[1]}" if len(parts) > 1 else None
            elif isinstance(item, dict):
                pkg_name = item.get("package_name")
                version_spec = item.get("version_specifier")
            else:
                raise DependencyResolutionError(f"Invalid package specifier format: {item}")

            if not pkg_name:
                raise DependencyValidationError("", "Missing required 'package_name' in dependency list.")

            valid_name = DependencyValidator.validate_package_name(pkg_name)
            valid_spec = DependencyValidator.validate_version_specifier(version_spec)

            canonical_name = valid_name.lower().replace("_", "-")

            if canonical_name in resolved_map:
                existing_spec = resolved_map[canonical_name]["version_specifier"]
                if existing_spec and valid_spec and existing_spec != valid_spec:
                    raise DependencyResolutionError(
                        f"Conflicting version constraints for package '{valid_name}': '{existing_spec}' vs '{valid_spec}'."
                    )

            resolved_map[canonical_name] = {
                "package_name": valid_name,
                "version_specifier": valid_spec or "",
                "requirement": DependencyValidator.format_requirement(valid_name, valid_spec),
            }

        return list(resolved_map.values())
