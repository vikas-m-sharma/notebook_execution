import importlib.metadata
import io
import os
import subprocess
import sys
import time
import traceback
from typing import Any

# Allowed environment variables for worker execution process
_ALLOWED_ENV_VARS = {
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "PYTHONPATH",
    "LANG",
    "LC_ALL",
    "HOMEPATH",
    "USERPROFILE",
    "USERNAME",
    "OS",
    "COMSPEC",
    "PATHEXT",
}


def _sanitize_worker_environment() -> None:
    """SEC-003: Strip all host secrets and database credentials from worker process environment."""
    for key in list(os.environ.keys()):
        if key.upper() not in _ALLOWED_ENV_VARS:
            os.environ.pop(key, None)


def _get_installed_package_version(package_name: str) -> str | None:
    """Helper retrieving installed package version via importlib.metadata."""
    canonical_name = package_name.strip().lower().replace("_", "-")
    try:
        return importlib.metadata.version(canonical_name)
    except Exception:
        # Try original name fallback
        try:
            return importlib.metadata.version(package_name.strip())
        except Exception:
            return None


def run_python_worker(conn) -> None:
    """Worker process main loop executing code and dependency requests received via IPC pipe."""
    # SEC-003: Immediately purge host environment variables (e.g. DATABASE_URL)
    _sanitize_worker_environment()

    # Isolated execution globals namespace for state persistence within child worker process
    globals_dict: dict[str, Any] = {
        "__name__": "__main__",
        "__doc__": None,
        "__package__": None,
    }

    while True:
        try:
            if not conn.poll(timeout=0.05):
                continue

            msg = conn.recv()
            if msg is None or msg.get("command") == "stop":
                break

            cmd = msg.get("command")

            if cmd == "execute":
                req_id = msg.get("request_id")
                code = msg.get("code", "")

                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                old_stdout = sys.stdout
                old_stderr = sys.stderr

                start_time = time.perf_counter()
                exec_status = "ok"
                tb_str = None

                try:
                    sys.stdout = stdout_capture
                    sys.stderr = stderr_capture

                    # Compile and execute code inside isolated worker process namespace
                    compiled = compile(code, "<notebook_cell>", "exec")
                    exec(compiled, globals_dict)

                except Exception:
                    exec_status = "error"
                    tb_str = traceback.format_exc()
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                stdout_text = stdout_capture.getvalue()
                stderr_text = stderr_capture.getvalue()

                response = {
                    "request_id": req_id,
                    "status": exec_status,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "traceback": tb_str,
                    "execution_time_ms": elapsed_ms,
                }
                conn.send(response)

            elif cmd == "install_packages":
                req_id = msg.get("request_id")
                requirements = msg.get("requirements", [])
                timeout = msg.get("timeout", 120.0)

                start_time = time.perf_counter()
                stdout_text = ""
                stderr_text = ""
                resolved_versions: dict[str, str] = {}
                install_status = "ok"
                tb_str = None

                try:
                    # Execute pip install as structured subprocess inside isolated worker environment
                    cmd_args = [sys.executable, "-m", "pip", "install"] + requirements
                    proc = subprocess.run(
                        cmd_args,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    stdout_text = proc.stdout or ""
                    stderr_text = proc.stderr or ""

                    if proc.returncode != 0:
                        install_status = "error"
                    else:
                        # Extract resolved versions for requested packages
                        for req in requirements:
                            pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].strip()
                            ver = _get_installed_package_version(pkg_name)
                            if ver:
                                resolved_versions[pkg_name] = ver

                except subprocess.TimeoutExpired as texc:
                    install_status = "timeout"
                    stderr_text = f"Pip installation timed out after {timeout} seconds."
                    tb_str = str(texc)
                except Exception as exc:
                    install_status = "error"
                    stderr_text = f"Pip installation exception: {exc}"
                    tb_str = traceback.format_exc()
                finally:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                conn.send({
                    "request_id": req_id,
                    "status": install_status,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "resolved_versions": resolved_versions,
                    "traceback": tb_str,
                    "execution_time_ms": elapsed_ms,
                })

            elif cmd == "verify_packages":
                req_id = msg.get("request_id")
                packages = msg.get("packages", [])
                satisfied = True
                resolved_versions: dict[str, str] = {}
                missing_or_invalid: list[str] = []

                for pkg_item in packages:
                    pkg_name = pkg_item.get("package_name", "").strip()
                    spec = pkg_item.get("version_specifier", "").strip()
                    ver = _get_installed_package_version(pkg_name)

                    if ver is None:
                        satisfied = False
                        missing_or_invalid.append(f"{pkg_name} (not installed)")
                    else:
                        resolved_versions[pkg_name] = ver
                        if spec.startswith("=="):
                            target_ver = spec[2:].strip()
                            if ver != target_ver:
                                satisfied = False
                                missing_or_invalid.append(
                                    f"{pkg_name} (installed {ver} does not match required {spec})"
                                )

                conn.send({
                    "request_id": req_id,
                    "status": "ok",
                    "satisfied": satisfied,
                    "resolved_versions": resolved_versions,
                    "missing_or_invalid": missing_or_invalid,
                })

        except (EOFError, KeyboardInterrupt):
            break
        except Exception as exc:
            try:
                conn.send({
                    "status": "error",
                    "stdout": "",
                    "stderr": str(exc),
                    "traceback": traceback.format_exc(),
                    "execution_time_ms": 0.0,
                })
            except Exception:
                pass
            break
