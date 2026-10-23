from pathlib import Path
import difflib
import subprocess
import sys

import os
import shutil

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules",
    "build", "target", "dist", "__pycache__",
    ".idea", ".vscode", ".gradle", "bin",
}

SKIP_FILES = {
    ".env", ".npmrc", ".pypirc",
}

TEXT_EXTENSIONS = {
    ".java", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".json", ".xml", ".gradle", ".kts", ".properties",
    ".yaml", ".yml", ".feature", ".md", ".txt",
    ".toml", ".ini", ".cfg", ".html", ".css",
}


class ProjectTools:
    def __init__(self, project_root: str):
        self.root = Path(project_root).expanduser().resolve()

        if not self.root.is_dir():
            raise ValueError(f"Project folder does not exist: {self.root}")

    def _resolve_file(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("A non-empty relative path is required.")
        requested = Path(relative_path)
        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Use a relative path without '..'.")
        path = (self.root / requested).resolve()

        if not path.is_relative_to(self.root):
            raise ValueError("File must be inside the project folder.")

        relative = path.relative_to(self.root)

        if any(part in SKIP_DIRS for part in relative.parts):
            raise ValueError("Excluded project directory.")

        if path.name in SKIP_FILES or path.name.startswith(".env."):
            raise ValueError("Environment/credential file is excluded.")

        if not path.is_file():
            raise FileNotFoundError(f"File does not exist: {relative_path}")

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            raise ValueError("Unsupported text file type.")

        return path

    def _files(self, folder: Path):
        for path in sorted(folder.iterdir()):
            if path.is_symlink():
                continue

            if path.is_dir():
                if path.name not in SKIP_DIRS:
                    yield from self._files(path)

            elif (
                path.suffix.lower() in TEXT_EXTENSIONS
                and path.name not in SKIP_FILES
                and not path.name.startswith(".env.")
            ):
                yield path

    def list_files(self, limit: int = 200, relative_folder: str = ".") -> dict:
        if not 1 <= limit <= 2000:
            raise ValueError("limit must be between 1 and 2000.")

        files = []

        folder = (self.root / relative_folder).resolve()
        if not folder.is_relative_to(self.root) or not folder.is_dir():
            raise ValueError("Folder must exist inside the project root.")
        if any(part in SKIP_DIRS for part in folder.relative_to(self.root).parts):
            raise ValueError("Excluded project directory.")
        for path in self._files(folder):
            if len(files) == limit:
                return {"files": files, "truncated": True}

            files.append(path.relative_to(self.root).as_posix())

        return {"files": files, "truncated": False}


    def read_file(
        self,
        relative_path: str,
        start_line: int = 1,
        max_lines: int = 200,
    ) -> dict:
        if type(start_line) is not int or start_line < 1:
            raise ValueError("start_line must be a positive integer.")

        if type(max_lines) is not int or not 1 <= max_lines <= 500:
            raise ValueError("max_lines must be between 1 and 500.")

        path = self._resolve_file(relative_path)

        if path.stat().st_size > 1_000_000:
            raise ValueError("File exceeds the 1 MB reading limit.")

        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if lines and start_line > len(lines):
            raise ValueError(f"start_line exceeds total_lines ({len(lines)}).")
        selected = lines[start_line - 1:start_line - 1 + max_lines]

        return {
            "file": path.relative_to(self.root).as_posix(),
            "total_lines": len(lines),
            "start_line": start_line,
            "end_line": start_line + len(selected) - 1,
            "content": "\n".join(
                f"{number}: {line}"
                for number, line in enumerate(
                    selected, start=start_line
                )
            ),
            "truncated": start_line - 1 + len(selected) < len(lines),
        }


    def read_files(self, files: list[dict]) -> dict:
        """Read up to five focused file ranges in one tool call."""
        if not isinstance(files, list) or not 1 <= len(files) <= 5:
            raise ValueError("files must contain between 1 and 5 entries.")

        # Validate the whole request before reading.
        for item in files:
            if not isinstance(item, dict):
                raise ValueError("Each entry must be an object.")

            if set(item) - {"relative_path", "start_line", "max_lines"}:
                raise ValueError("Unknown file-read argument.")

            path = item.get("relative_path")
            start = item.get("start_line", 1)
            count = item.get("max_lines", 40)

            if not isinstance(path, str) or not path.strip():
                raise ValueError("Each entry requires relative_path.")

            if type(start) is not int or start < 1:
                raise ValueError("start_line must be a positive integer.")

            if type(count) is not int or not 1 <= count <= 80:
                raise ValueError("max_lines must be between 1 and 80.")

        results = []

        for item in files:
            try:
                result = self.read_file(
                    relative_path=item["relative_path"],
                    start_line=item.get("start_line", 1),
                    max_lines=item.get("max_lines", 40),
                )
                results.append(result)

            except (ValueError, OSError) as error:
                results.append({
                    "file": item["relative_path"],
                    "error": str(error),
                    "error_type": type(error).__name__,
                })

        return {"results": results}

    def search_text(self, query: str, limit: int = 50) -> dict:
        if not query.strip():
            raise ValueError("Search query must not be empty.")

        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500.")

        matches = []

        for path in self._files(self.root):
            if path.stat().st_size > 1_000_000:
                continue

            try:
                lines = path.read_text(
                    encoding="utf-8-sig"
                ).splitlines()
            except UnicodeDecodeError:
                continue

            for number, line in enumerate(lines, start=1):
                if query.casefold() in line.casefold():
                    if len(matches) == limit:
                        return {"matches": matches, "truncated": True}

                    matches.append({
                        "file": path.relative_to(self.root).as_posix(),
                        "line": number,
                        "text": line[:500],
                    })

        return {"matches": matches, "truncated": False}

    def replace_text(
        self,
        relative_path: str,
        old_text: str,
        new_text: str,
    ) -> dict:
        """Replace one exact match and display the applied diff."""

        if not isinstance(old_text, str) or not old_text:
            raise ValueError("old_text must be a non-empty string.")

        if not isinstance(new_text, str):
            raise ValueError("new_text must be a string.")

        path = self._resolve_file(relative_path)
        original_bytes = path.read_bytes()

        if len(original_bytes) > 1_000_000:
            raise ValueError("File exceeds the 1 MB editing limit.")

        has_bom = original_bytes.startswith(b"\xef\xbb\xbf")
        original = original_bytes.decode("utf-8-sig")

        crlf = "\r\n" in original
        normalised = original.replace("\r\n", "\n")
        old_text = old_text.replace("\r\n", "\n")
        new_text = new_text.replace("\r\n", "\n")

        matches = normalised.count(old_text)

        if matches != 1:
            raise ValueError(
                f"Expected one exact match; found {matches}. "
                "Read the file and provide a unique text block."
            )

        updated = normalised.replace(old_text, new_text, 1)

        if updated == normalised:
            return {"file": relative_path, "changed": False}

        diff = "".join(
            difflib.unified_diff(
                normalised.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )

        output = updated.replace("\n", "\r\n") if crlf else updated
        encoding = "utf-8-sig" if has_bom else "utf-8"
        updated_bytes = output.encode(encoding)

        if len(updated_bytes) > 1_000_000:
            raise ValueError("Updated file exceeds the 1 MB limit.")

        if path.read_bytes() != original_bytes:
            raise ValueError("File changed during editing; read it again.")

        path.write_bytes(updated_bytes)

        print("\nAPPLIED DIFF:")
        print(diff)

        return {
            "file": path.relative_to(self.root).as_posix(),
            "changed": True,
            "diff": diff,
        }

    def run_python_file(
        self,
        relative_path: str,
        timeout: int = 30,
    ) -> dict:
        if not isinstance(timeout, int) or not 1 <= timeout <= 60:
            raise ValueError("timeout must be between 1 and 60 seconds.")

        path = self._resolve_file(relative_path)

        if path.suffix.lower() != ".py":
            raise ValueError("This tool runs Python files only.")

        command = [sys.executable, str(path)]

        print("\nRUNNING:", command)

        try:
            result = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )

            return {
                "file": path.relative_to(self.root).as_posix(),
                "exit_code": result.returncode,
                "stdout": result.stdout[-12000:],
                "stderr": result.stderr[-12000:],
                "output_truncated": (
                    len(result.stdout) > 12000
                    or len(result.stderr) > 12000
                ),
                "timed_out": False,
            }

        except subprocess.TimeoutExpired as error:
            return {
                "file": path.relative_to(self.root).as_posix(),
                "stdout": self._timeout_text(error.stdout),
                "stderr": self._timeout_text(error.stderr),
                "output_truncated": len(error.stdout or b"") > 12000 or len(error.stderr or b"") > 12000,
                "exit_code": None,
                "timed_out": True,
                "error": f"Script exceeded {timeout} seconds.",
            }

    def create_file(
        self,
        relative_path: str,
        content: str,
    ) -> dict:
        """Create a new text file without overwriting an existing file."""

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("A non-empty relative path is required.")

        if not isinstance(content, str):
            raise ValueError("content must be a string.")

        requested = Path(relative_path)

        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Use a relative path without '..'.")

        if any(part in SKIP_DIRS for part in requested.parts):
            raise ValueError("Excluded project directory.")

        if (
            requested.name in SKIP_FILES
            or requested.name.startswith(".env.")
        ):
            raise ValueError("Environment/credential file is excluded.")

        if requested.suffix.lower() not in TEXT_EXTENSIONS:
            raise ValueError("Unsupported text file type.")

        # Reject existing symlinks along the requested path.
        current = self.root

        for part in requested.parts:
            current = current / part

            if current.is_symlink():
                raise ValueError("Symlink paths are excluded.")

        path = (self.root / requested).resolve()

        if not path.is_relative_to(self.root):
            raise ValueError("File must be inside the project folder.")

        data = content.encode("utf-8")

        if len(data) > 1_000_000:
            raise ValueError("Content exceeds the 1 MB limit.")

        if path.exists():
            raise ValueError(
                "File already exists. Use read_file and replace_text."
            )

        path.parent.mkdir(parents=True, exist_ok=True)

        # Exclusive creation prevents overwriting an existing file.
        with path.open("xb") as output:
            output.write(data)

        relative = path.relative_to(self.root).as_posix()

        print("\nCREATED FILE:", relative)

        return {
            "file": relative,
            "created": True,
            "size_bytes": len(data),
        }



    def run_command(
        self,
        command: list[str],
        timeout: int = 60,
    ) -> dict:
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(arg, str) and arg for arg in command)
        ):
            raise ValueError("command must be a non-empty list of strings.")

        if not isinstance(timeout, int) or not 1 <= timeout <= 300:
            raise ValueError("timeout must be between 1 and 300 seconds.")

        allowed = {"python", "mvn", "mvnw", "gradle", "gradlew", "npm"}
        tool = command[0]

        if tool not in allowed:
            raise ValueError(f"Supported commands: {sorted(allowed)}")

        if tool == "python":
            executable = sys.executable

        elif tool in {"gradlew", "mvnw"}:
            filename = tool + (".bat" if os.name == "nt" else "")
            wrapper = self.root / filename

            if not wrapper.is_file():
                raise ValueError(f"Project wrapper missing: {filename}")

            executable = str(wrapper)

        else:
            executable = shutil.which(tool)

            if not executable:
                raise ValueError(f"{tool} is not installed or not on PATH.")

        argv = [executable, *command[1:]]
        print("\nRUNNING:", argv)

        # Windows batch wrappers require cmd.exe.
        if os.name == "nt" and executable.lower().endswith((".bat", ".cmd")):
            if any(
                    any(char in arg for char in '&|<>^%!"\r\n')
                    for arg in argv
            ):
                raise ValueError("Unsupported Windows batch argument.")

            command_text = " ".join(f'"{arg}"' for arg in argv)
            cmd_executable = os.environ.get("COMSPEC", "cmd.exe")

            # Use a string so Python does not escape the cmd.exe quotes.
            argv = (
                    subprocess.list2cmdline([cmd_executable])
                    + ' /d /s /c "'
                    + command_text
                    + '"'
            )

        try:
            result = subprocess.run(
                argv,
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )

            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout[-12000:],
                "stderr": result.stderr[-12000:],
                "output_truncated": (
                    len(result.stdout) > 12000
                    or len(result.stderr) > 12000
                ),
                "timed_out": False,
            }

        except subprocess.TimeoutExpired as error:
            return {
                "command": command,
                "stdout": self._timeout_text(error.stdout),
                "stderr": self._timeout_text(error.stderr),
                "output_truncated": len(error.stdout or b"") > 12000 or len(error.stderr or b"") > 12000,
                "exit_code": None,
                "timed_out": True,
                "error": f"Command exceeded {timeout} seconds.",
            }

    @staticmethod
    def _timeout_text(value) -> str:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return (value or "")[-12000:]

    def inspect_browser_page(self, url: str, evidence_folder: str = "test-output/agent-web", limit: int = 20) -> dict:
        """Inspect a public page in an isolated browser; approval controls navigation/artifact creation."""
        from integrations.web.inspection import inspect_browser_page
        return inspect_browser_page(self, url, evidence_folder, limit)

    def validate_test_plan(self, plan_json: str = None, plan: dict = None) -> dict:
        """Check one native plan object or legacy JSON string; cases remain not run."""
        from agent.tools.test_plans import validate_test_plan
        return validate_test_plan(self, plan_json, plan=plan)

    def draft_test_observations(self, case_file: str, observations_file: str, case_id: str) -> dict:
        """Read saved case/observation files and return review-only defect drafts."""
        from agent.tools.test_observations import draft_test_observations
        return draft_test_observations(self, case_file, observations_file, case_id)

    def parse_test_results(self, relative_path: str, limit: int = 100) -> dict:
        """Read a results report, including reports in build/target output folders."""
        from agent.tools.test_results import parse_test_results
        return parse_test_results(self.root, relative_path, limit)

    def build_test_report(self, manifest_file: str, evidence_folder: str = "") -> dict:
        """Build review-only case/run/evidence Markdown; exporting needs a separate action."""
        from integrations.reporting.traceability import report_for_agent
        return report_for_agent(self.root, manifest_file, evidence_folder)

    def investigate_test_failure(self, relative_path: str, case_name: str, case_class: str = "", evidence_spans: list[dict] = None, run_file: str = "") -> dict:
        """Read one failed report case with bounded evidence; no repair or rerun executes."""
        from agent.tools.test_failures import investigate_test_failure
        return investigate_test_failure(self.root, relative_path, case_name, case_class, evidence_spans, run_file)

    def run_tests_and_parse(
        self,
        command: list[str],
        relative_report_folder: str,
        timeout: int = 300,
    ) -> dict:
        from agent.tools.test_results import run_tests_and_parse
        return run_tests_and_parse(self, command, relative_report_folder, timeout)

    def discover_feature_mappings(self, limit: int = 500) -> dict:
        from agent.tools.feature_mapping import discover_feature_mappings
        return discover_feature_mappings(self.root, limit=limit)
