import logging
from contextlib import contextmanager

from unittest_utils import RDLSourceTestCase
from systemrdl import warnings

# Distinctive substring of the DEFAULT_IN_FIELD diagnostic message.
DEFAULT_IN_FIELD_MSG = r"'default' property assignment has no effect inside a field's body"

FIXTURE = "rdl_src/default_in_field.rdl"
REG_SCOPE_FIXTURE = "rdl_src/default_in_reg_scope.rdl"


@contextmanager
def capture_log_messages():
    """
    Capture messages emitted by TestPrinter (which logs everything via
    ``logging.info``) without requiring at least one record to be present.

    ``TestCase.assertNoLogs`` would be simpler, but it is only available on
    Python 3.10+, whereas this project supports Python 3.7+.
    """
    records = []

    class _Handler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Handler()
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)
    try:
        yield records
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)


class TestDefaultInFieldSilent(RDLSourceTestCase):
    """No warning/error flags set (the out-of-the-box default)."""

    def test_default_in_field_is_silently_discarded(self):
        # The check is a no-op: compilation is silent and the discarded
        # 'default name' assignment leaves the fields with their auto-generated
        # instance names.
        with capture_log_messages() as records:
            top = self.compile([FIXTURE], "default_in_field")

        self.assertEqual(records, [])

        f1 = top.find_by_path("default_in_field.some_reg.f1")
        f2 = top.find_by_path("default_in_field.some_reg.f2")
        self.assertEqual(f1.get_property("name"), "f1")
        self.assertEqual(f2.get_property("name"), "f2")

    def test_prop_mod_default_in_field_is_silently_discarded(self):
        # The interrupt property-modifier form is likewise discarded silently.
        with capture_log_messages() as records:
            top = self.compile([FIXTURE], "default_prop_mod_in_field")

        self.assertEqual(records, [])

        f1 = top.find_by_path("default_prop_mod_in_field.some_reg.f1")
        self.assertFalse(f1.get_property("intr"))


class TestDefaultInFieldWarning(RDLSourceTestCase):
    def setUp(self):
        super().setUp()
        self.compiler_warning_flags = warnings.DEFAULT_IN_FIELD

    def test_default_in_field_warns(self):
        # A warning is emitted, but compilation still succeeds...
        with self.assertLogs() as cm:
            top = self.compile([FIXTURE], "default_in_field")

        messages = "\n".join(r.getMessage() for r in cm.records)
        self.assertRegex(messages, DEFAULT_IN_FIELD_MSG)

        # ...and the assignment is still discarded despite the warning.
        f1 = top.find_by_path("default_in_field.some_reg.f1")
        self.assertEqual(f1.get_property("name"), "f1")

    def test_prop_mod_default_in_field_warns(self):
        # The 'default level intr;' (property-modifier) form is also flagged.
        with self.assertLogs() as cm:
            self.compile([FIXTURE], "default_prop_mod_in_field")

        messages = "\n".join(r.getMessage() for r in cm.records)
        self.assertRegex(messages, DEFAULT_IN_FIELD_MSG)

    def test_reg_scope_default_not_flagged(self):
        # A legit 'default' at the reg scope must never be flagged. Compilation
        # is silent and the default still propagates to child fields.
        with capture_log_messages() as records:
            top = self.compile([REG_SCOPE_FIXTURE], "default_in_reg_scope")

        messages = "\n".join(r.getMessage() for r in records)
        self.assertNotRegex(messages, DEFAULT_IN_FIELD_MSG)

        f1 = top.find_by_path("default_in_reg_scope.some_reg.f1")
        f2 = top.find_by_path("default_in_reg_scope.some_reg.f2")
        self.assertTrue(f1.get_property("woclr"))
        self.assertTrue(f2.get_property("woclr"))


class TestDefaultInFieldError(RDLSourceTestCase):
    def setUp(self):
        super().setUp()
        self.compiler_error_flags = warnings.DEFAULT_IN_FIELD

    def test_default_in_field_errors(self):
        self.assertRDLCompileError(
            [FIXTURE],
            "default_in_field",
            DEFAULT_IN_FIELD_MSG
        )

    def test_prop_mod_default_in_field_errors(self):
        self.assertRDLCompileError(
            [FIXTURE],
            "default_prop_mod_in_field",
            DEFAULT_IN_FIELD_MSG
        )

    def test_reg_scope_default_not_flagged(self):
        # Even promoted to an error, the legit reg-scope default must not
        # trigger the check: if it (falsely) did, compilation would raise.
        top = self.compile([REG_SCOPE_FIXTURE], "default_in_reg_scope")
        f2 = top.find_by_path("default_in_reg_scope.some_reg.f2")
        self.assertTrue(f2.get_property("woclr"))
