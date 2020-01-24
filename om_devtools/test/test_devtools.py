
import unittest
import subprocess
import io

import numpy as np

import openmdao.api as om
from openmdao.utils.testing_utils import use_tempdirs


@use_tempdirs
class DumpIdxsTestCase(unittest.TestCase):
    def test_dump_idxs(self):
        p = om.Problem()
        model = p.model
        model.add_subsystem('indeps', om.IndepVarComp('x', val=np.ones(5)))

        csizes = [3, 4, 1, 6, 2]

        for i, size in enumerate(csizes):
            model.add_subsystem('C%d' % i, om.ExecComp('y=2.*x', x=np.ones(size), y=np.ones(size)))

        p.setup()

        from om_devtools.dist_idxs import dump_dist_idxs

        f = io.StringIO()
        dump_dist_idxs(p, stream=f)
        lines = f.getvalue().splitlines()

        expected = [
            'C4.y     19',
            'C3.y     13     14 C4.x',
            'C2.y     12      8 C3.x',
            'C1.y      8      7 C2.x',
            'C0.y      5      3 C1.x',
            'indeps.x  0      0 C0.x',
        ]

        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                self.assertEqual(expected[i], line)



if __name__ == "__main__":
    unittest.main()
