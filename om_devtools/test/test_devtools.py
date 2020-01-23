"""Test the None."""

import unittest
import subprocess

import openmdao.api as om
from openmdao.utils.testing_utils import use_tempdirs

try:
    from parameterized import parameterized
except ImportError:
    from openmdao.utils.assert_utils import SkipParameterized as parameterized


def _test_func_name(func, num, param):
    return func.__name__ + '_' + '_'.join(param.args[0].split()[1:-1])


cmd_tests = [
    'openmdao compute_entry_points openmdao',
]


@use_tempdirs
class CmdlineTestCase(unittest.TestCase):
    @parameterized.expand(cmd_tests, name_func=_test_func_name)
    def test_cmd(self, cmd):
        # this only tests that a given command line tool returns a 0 return code. It doesn't
        # check the expected output at all.  The underlying functions that implement the
        # commands should be tested seperately.
        try:
            output = subprocess.check_output(cmd.split())
        except subprocess.CalledProcessError as err:
            self.fail("Command '{}' failed.  Return code: {}".format(
                cmd, err.returncode))


if __name__ == "__main__":
    unittest.main()
