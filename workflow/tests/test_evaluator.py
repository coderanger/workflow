from unittest2 import TestCase

from workflow.interpreter import Evaluator

class EvaluatorTest(TestCase):
    def test_num(self):
        e = Evaluator.from_string('1')
        e()
        self.assertTrue(e.complete)
        self.assertEqual(e.return_value, 1)

    def test_add(self):
        e = Evaluator.from_string('1 + 2')
        e()
        self.assertTrue(e.complete)
        self.assertEqual(e.return_value, 3)
