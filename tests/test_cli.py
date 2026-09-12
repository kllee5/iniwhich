import contextlib
import io
import json
import os
import tempfile
import unittest

from iniwhich.cli import main


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            returncode = main(argv)
        return returncode, out.getvalue()


class TraceCommandTests(CliTestCase):
    def test_text_output_and_exit_code_when_key_resolves(self):
        base = self._write("base.ini", "[db]\nhost = localhost\nport = 5432\n")
        prod = self._write("prod.ini", "[db]\nhost = db.internal.example\n")

        returncode, output = self._run(["db", "host", base, prod])

        self.assertEqual(returncode, 0)
        self.assertIn(f"{base}: db.host = localhost", output)
        self.assertIn(f"winner: {prod} -> db.host = db.internal.example", output)

    def test_json_output_matches_trace_result_shape(self):
        base = self._write("base.ini", "[db]\nhost = localhost\n")

        returncode, output = self._run(["db", "host", base, "--json"])

        self.assertEqual(returncode, 0)
        payload = json.loads(output)
        self.assertEqual(payload["section"], "db")
        self.assertEqual(payload["key"], "host")
        self.assertEqual(payload["winner"], {"file": base, "value": "localhost"})

    def test_exit_code_is_one_when_key_never_set(self):
        cache = self._write("cache.ini", "[cache]\nhost = 127.0.0.1\n")

        returncode, _ = self._run(["db", "host", cache])

        self.assertEqual(returncode, 1)

    def test_no_files_given_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["db", "host"])
        self.assertEqual(ctx.exception.code, 2)

    def test_version_flag_prints_version_and_exits_zero(self):
        from iniwhich import __version__

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, out.getvalue())


class FilesFromTests(CliTestCase):
    def test_reads_precedence_list_from_file(self):
        base = self._write("base.ini", "[db]\nhost = localhost\n")
        prod = self._write("prod.ini", "[db]\nhost = db.internal.example\n")
        listfile = self._write("stack.txt", f"{base}\n{prod}\n")

        returncode, output = self._run(["db", "host", "--files-from", listfile])

        self.assertEqual(returncode, 0)
        self.assertIn(f"winner: {prod} -> db.host = db.internal.example", output)

    def test_files_and_files_from_together_is_a_usage_error(self):
        base = self._write("base.ini", "[db]\nhost = localhost\n")
        listfile = self._write("stack.txt", f"{base}\n")

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["db", "host", base, "--files-from", listfile])
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_files_from_path_is_a_usage_error(self):
        missing = os.path.join(self.tmpdir.name, "does-not-exist.txt")

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["db", "host", "--files-from", missing])
        self.assertEqual(ctx.exception.code, 2)

    def test_files_from_listing_no_files_is_a_usage_error(self):
        listfile = self._write("stack.txt", "# nothing but comments\n\n")

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["db", "host", "--files-from", listfile])
        self.assertEqual(ctx.exception.code, 2)


class ShowAllSectionsTests(CliTestCase):
    def test_text_output_groups_by_section(self):
        base = self._write("base.ini", "[db]\nhost = localhost\nport = 5432\n")
        prod = self._write("prod.ini", "[db]\nhost = db.internal.example\n")

        returncode, output = self._run(["--show-all-sections", base, prod])

        self.assertEqual(returncode, 0)
        self.assertIn("[db]", output)
        self.assertIn(f"host -> {prod} = db.internal.example", output)
        self.assertIn(f"port -> {base} = 5432", output)

    def test_json_output_is_a_list_of_trace_results(self):
        base = self._write("base.ini", "[db]\nhost = localhost\n")

        returncode, output = self._run(["--show-all-sections", base, "--json"])

        self.assertEqual(returncode, 0)
        payload = json.loads(output)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["winner"], {"file": base, "value": "localhost"})

    def test_does_not_swallow_file_paths_as_section_and_key(self):
        # regression check for the argparse-shape workaround in main(): with
        # --show-all-sections there is no section/key positional to eat the
        # first two file paths.
        base = self._write("base.ini", "[db]\nhost = localhost\n")
        prod = self._write("prod.ini", "[cache]\nhost = 127.0.0.1\n")

        returncode, output = self._run(["--show-all-sections", base, prod])

        self.assertEqual(returncode, 0)
        self.assertIn("[db]", output)
        self.assertIn("[cache]", output)

    def test_exit_code_is_one_when_nothing_is_found(self):
        empty = self._write("empty.ini", "")

        returncode, _ = self._run(["--show-all-sections", empty])

        self.assertEqual(returncode, 1)


if __name__ == "__main__":
    unittest.main()
