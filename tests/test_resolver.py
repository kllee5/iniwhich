import os
import tempfile
import unittest

from iniwhich.resolver import trace


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_last_file_to_set_key_wins(self):
        base = self._write("base.ini", "[db]\nhost = localhost\nport = 5432\n")
        prod = self._write("prod.ini", "[db]\nhost = db.internal.example\n")
        hotfix = self._write("hotfix.ini", "[db]\n")

        result = trace("db", "host", [base, prod, hotfix])

        self.assertEqual(result.winner.file, prod)
        self.assertEqual(result.winner.value, "db.internal.example")
        self.assertTrue(result.sources[0].found)
        self.assertTrue(result.sources[1].found)
        self.assertFalse(result.sources[2].found)

    def test_missing_section_counts_as_not_set(self):
        path = self._write("only-cache.ini", "[cache]\nhost = 127.0.0.1\n")

        result = trace("db", "host", [path])

        self.assertIsNone(result.winner)
        self.assertFalse(result.sources[0].found)
        self.assertIsNone(result.sources[0].error)

    def test_missing_file_is_reported_as_an_error_not_a_crash(self):
        missing = os.path.join(self.tmpdir.name, "does-not-exist.ini")

        result = trace("db", "host", [missing])

        source = result.sources[0]
        self.assertFalse(source.found)
        self.assertIsNotNone(source.error)
        self.assertIsNone(result.winner)

    def test_bad_syntax_is_reported_as_an_error_not_a_crash(self):
        broken = self._write("broken.ini", "this is not valid ini syntax\n[db\nhost = x\n")

        result = trace("db", "host", [broken])

        source = result.sources[0]
        self.assertFalse(source.found)
        self.assertIsNotNone(source.error)
        self.assertIsNone(result.winner)

    def test_error_file_does_not_block_a_later_winner(self):
        broken = self._write("broken.ini", "[db\nhost = x\n")
        good = self._write("good.ini", "[db]\nhost = fallback\n")

        result = trace("db", "host", [broken, good])

        self.assertEqual(result.winner.file, good)
        self.assertEqual(result.winner.value, "fallback")

    def test_percent_sign_does_not_trigger_interpolation_error(self):
        path = self._write("percent.ini", "[db]\nhost = 100%full\n")

        result = trace("db", "host", [path])

        self.assertEqual(result.winner.value, "100%full")

    def test_to_dict_omits_error_key_when_there_is_none(self):
        path = self._write("plain.ini", "[db]\nhost = localhost\n")

        result = trace("db", "host", [path])

        source_dict = result.to_dict()["sources"][0]
        self.assertNotIn("error", source_dict)

    def test_to_dict_includes_error_key_when_read_fails(self):
        missing = os.path.join(self.tmpdir.name, "gone.ini")

        result = trace("db", "host", [missing])

        source_dict = result.to_dict()["sources"][0]
        self.assertIn("error", source_dict)


if __name__ == "__main__":
    unittest.main()
