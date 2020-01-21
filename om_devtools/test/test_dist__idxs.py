"""Test the None."""

import unittest

import numpy as np
from numpy.testing import assert_allclose

import openmdao.api as om
from openmdao.utils.assert_utils import assert_check_partials


class TestNone(unittest.TestCase):

    def test_basic(self):
        pass

    # for component classes ...
    # def test_partials(self):
        # p = om.Problem()

        # populate problem here...

        # partials = p.check_partials(method='fd', out_stream=None)
        # assert_check_partials(partials)


if __name__ == "__main__":
    unittest.main()
