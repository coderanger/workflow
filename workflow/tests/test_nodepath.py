import ast

from unittest2 import TestCase

from workflow.interpreter import NodePath

class NodePathTest(TestCase):
    def test_empty(self):
        root = ast.parse('1')
        p = NodePath(root)
        self.assertIs(p(), root)

    def test_root(self):
        root = ast.parse('1')
        p = NodePath.from_string(root, '/')
        self.assertIs(p(), root)

    def test_expr0(self):
        root = ast.parse('1')
        p = NodePath.from_string(root, '/0')
        self.assertIs(p(), root.body[0])

    def test_add_expr0(self):
        root = ast.parse('1')
        p = NodePath(root)
        p += root.body[0]
        self.assertEqual(str(p), '/0')

    def test_expr0value(self):
        root = ast.parse('1')
        p = NodePath.from_string(root, '/0/')
        self.assertIs(p(), root.body[0].value)

    def test_add_expr0value(self):
        root = ast.parse('1')
        p = NodePath(root)
        p += root.body[0]
        p += root.body[0].value
        self.assertEqual(str(p), '/0/')

    def test_expr1(self):
        root = ast.parse('1\n2\n3')
        p = NodePath.from_string(root, '/1')
        self.assertIs(p(), root.body[1])

    def test_add_expr1(self):
        root = ast.parse('1\n2\n3')
        p = NodePath(root)
        p += root.body[1]
        self.assertEqual(str(p), '/1')

    def test_binop(self):
        root = ast.parse('1 + 2')
        p = NodePath.from_string(root, '/0//left')
        self.assertIs(p(), root.body[0].value.left)
        self.assertEqual(p().n, 1)

    def test_add_binop(self):
        root = ast.parse('1 + 2')
        p = NodePath(root)
        p += root.body[0]
        p += root.body[0].value
        p += root.body[0].value.right
        self.assertEqual(str(p), '/0//right')
        self.assertEqual(p().n, 2)

    def test_call(self):
        root = ast.parse('a(1, x=2, *y, **z)')
        p = NodePath.from_string(root, '/0//func')
        self.assertIs(p(), root.body[0].value.func)
        self.assertEqual(p().id, 'a')
        
        p = NodePath.from_string(root, '/0//args:0')
        self.assertIs(p(), root.body[0].value.args[0])
        self.assertEqual(p().n, 1)
        
        p = NodePath.from_string(root, '/0//keywords:0')
        self.assertIs(p(), root.body[0].value.keywords[0])
        self.assertEqual(p().arg, 'x')
        self.assertEqual(p().value.n, 2)
        
        p = NodePath.from_string(root, '/0//starargs')
        self.assertIs(p(), root.body[0].value.starargs)
        self.assertEqual(p().id, 'y')
        
        p = NodePath.from_string(root, '/0//kwargs')
        self.assertIs(p(), root.body[0].value.kwargs)
        self.assertEqual(p().id, 'z')

    def test_add_call(self):
        root = ast.parse('a(1, x=2, *y, **z)')
        p = NodePath(root)
        p += root.body[0]
        p += root.body[0].value
        p2 = p + root.body[0].value.func
        self.assertEqual(str(p2), '/0//func')
        self.assertEqual(p2().id, 'a')

        p2 = p + root.body[0].value.args[0]
        self.assertEqual(str(p2), '/0//args:0')
        self.assertEqual(p2().n, 1)
        
        p2 = p + root.body[0].value.keywords[0]
        self.assertEqual(str(p2), '/0//keywords:0')
        self.assertEqual(p2().arg, 'x')
        self.assertEqual(p2().value.n, 2)
        
        p2 = p + root.body[0].value.starargs
        self.assertEqual(str(p2), '/0//starargs')
        self.assertEqual(p2().id, 'y')
        
        p2 = p + root.body[0].value.kwargs
        self.assertEqual(str(p2), '/0//kwargs')
        self.assertEqual(p2().id, 'z')
