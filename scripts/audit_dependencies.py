"""Audit the complete lock, including upstream versions of official CPU wheels."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    requirements = []
    for line in (root / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "--")):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s\\]+)\s*\\?", line)
        if not match:
            raise ValueError(f"Expected an exact dependency pin: {line}")
        name, version = match.groups()
        if "+" in version:
            if name not in {"torch", "torchvision"} or not version.endswith("+cpu"):
                raise ValueError(f"No advisory mapping defined for {name}=={version}")
            # The CPU variant is distributed by PyTorch, not PyPI. Advisories
            # are recorded against the corresponding upstream public version.
            version = version.removesuffix("+cpu")
            print(f"Auditing official CPU build {name} against upstream {version}", flush=True)
        requirements.append(f"{name}=={version}")

    if not requirements:
        raise ValueError("No dependencies found to audit")
    with tempfile.TemporaryDirectory() as directory:
        audit_input = Path(directory) / "requirements.txt"
        audit_output = Path(directory) / "result.json"
        audit_input.write_text("\n".join(requirements) + "\n")
        result = subprocess.run([
            sys.executable, "-m", "pip_audit", "--disable-pip", "--no-deps",
            "-r", str(audit_input), "--format", "json", "--output", str(audit_output),
        ])
        if not audit_output.exists():
            return result.returncode or 1
        report = json.loads(audit_output.read_text())
        dependencies = report["dependencies"]
        skipped = [dependency for dependency in dependencies if "skip_reason" in dependency]
        vulnerable = [dependency for dependency in dependencies if dependency.get("vulns")]
        if skipped or vulnerable:
            print(json.dumps({"skipped": skipped, "vulnerable": vulnerable}, indent=2))
            return 1
        if len(dependencies) != len(requirements):
            raise ValueError("Audit did not return every locked dependency")
        if result.returncode:
            return result.returncode
        print(f"Audited {len(dependencies)} dependencies: no known vulnerabilities, no skipped packages")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
