import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check import REQUIRED, inventory, main


class PortabilityTests(unittest.TestCase):
    def test_no_secret_values_paths_or_external_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in REQUIRED:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SECRET_FILE_CONTENT")
            env = {"CODESPACES": "true", "FREELLM_API_KEY": "SECRET_ENV_VALUE"}
            with patch("subprocess.run", side_effect=AssertionError("process")), patch(
                "socket.socket", side_effect=AssertionError("network")
            ), patch("builtins.open", side_effect=AssertionError("file read")), patch(
                "pathlib.Path.open", side_effect=AssertionError("file read")
            ):
                result = inventory(root, env, lambda _: "/private/tool/location")
            rendered = json.dumps(result)
            for hidden in (tmp, "SECRET", "/private/tool/location"):
                self.assertNotIn(hidden, rendered)
            self.assertEqual(set(result["project_files"].values()), {"present"})
            self.assertEqual(result["environment"], "codespaces")

    def test_missing_tools_and_files_are_reported_not_claimed_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inventory(Path(tmp), {}, lambda _: None)
            self.assertFalse(any(result["tools_on_path"].values()))
            self.assertEqual(set(result["project_files"].values()), {"missing"})
            self.assertGreaterEqual(len(result["next_steps"]), 3)

    def test_symlink_parent_is_not_treated_as_portable_file(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            (Path(outside) / "launcher.py").write_text("private")
            (root / "tools").mkdir()
            (root / "tools/freellmapi").symlink_to(outside, target_is_directory=True)
            result = inventory(root, {}, lambda _: None)
            self.assertEqual(result["project_files"]["tools/freellmapi/launcher.py"], "symlink_review")

    def test_invalid_root_errors_without_printing_input_path(self):
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            status = main(["--root", "/nonexistent-private-project-name"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue()), {"error": "project_root_unavailable"})


if __name__ == "__main__":
    unittest.main()
