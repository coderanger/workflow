import ast
import operator
import uuid

class NodePathError(Exception):
    pass


class NodePath(object):
    """The location of a node stored in a safe way."""

    def __init__(self, root, *parts):
        self.parts = parts
        self.root = root
        self._value = None

    def __str__(self):
        return '/' + ('/'.join(self.parts))
    
    def __eq__(self, other):
        return str(self) == str(other)
    
    def __hash__(self):
        return hash((self.parts, self.root))

    @classmethod
    def from_string(cls, root, path):
        if path == '/':
            parts = []
        else:
            parts = path.split('/')[1:]
        return cls(root, *parts)

    def __call__(self):
        if self._value is None:
            self._value = self.resolve(self.root, list(self.parts))
        return self._value

    def resolve(self, node, parts):
        while parts:
            part = parts.pop(0)
            fn = getattr(self, 'resolve_'+type(node).__name__, None)
            node = fn(node, part)
        return node

    def resolve_Module(self, node, part):
        n = int(part)
        if not (0 <= n < len(node.body)):
            raise NodePathError
        return node.body[n]

    def resolve_Expr(self, node, part):
        return node.value

    def resolve_BinOp(self, node, part):
        if part not in ('left', 'op', 'right'):
            raise NodePathError
        return getattr(node, part)

    def resolve_Call(self, node, part):
        if part == 'func':
            return node.func
        if part == 'starargs':
            return node.starargs
        if part == 'kwargs':
            return node.kwargs
        if ':' in part:
            part, i = part.split(':', 1)
            i = int(i)
            if part == 'args':
                return node.args[i]
            if part == 'keywords':
                return node.keywords[i]
        return NodePathError

    def resolve_All(self, node, part):
        n = int(part)
        if not (0 <= n < len(node.args)):
            raise NodePathError
        return node.args[n]
    
    resolve_Any = resolve_All

    def __add__(self, node):
        prev = self()
        fn = getattr(self, 'add_'+type(prev).__name__, None)
        if fn is None:
            raise TypeError('No add_ dispatch found for %s'%prev)
        ret = fn(prev, node)
        if ret is None:
            raise NodePathError
        return self._add(ret)
    
    def _add(self, part):
        return self.__class__(self.root, *(self.parts + (str(part),)))

    def add_Module(self, prev, node):
        for i, n in enumerate(prev.body):
            if n is node:
                return i

    def add_Expr(self, prev, node):
        return ''

    def add_BinOp(self, prev, node):
        if node is prev.left:
            return 'left'
        if node is prev.op:
            return 'op'
        if node is prev.right:
            return 'right'

    def add_Call(self, prev, node):
        if node is prev.func:
            return 'func'
        if node is prev.starargs:
            return 'starargs'
        if node is prev.kwargs:
            return 'kwargs'
        for i, n in enumerate(prev.args):
            if node is n:
                return 'args:%s'%i
        for i, n in enumerate(prev.keywords):
            if node is n:
                return 'keywords:%s'%i
    
    def add_Name(self, prev, node):
        return ''
    
    def add_All(self, prev, node):
        for i, n in enumerate(prev.args):
            if n is node:
                return i
    
    add_Any = add_All


class Parallel(ast.expr):
    _fields = ('args',)
    
    def __init__(self, args=None):
        if args is not None:
            self.args = args


class All(Parallel):
    pass


class Any(Parallel):
    pass


class AnyAllNodeTransformer(ast.NodeTransformer):
    """Transform invocations of the special functions any() and all() into
    custom nodes for further processing.
    """
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == 'all':
                return All(node.args)
            if node.func.id == 'any':
                return Any(node.args)
        return node


class Defer(object):
    """Token object to represent deferred values."""
    def __init__(self):
        self.id = uuid.uuid4().hex


class Evaluator(object):

    def __init__(self, code, complete_cb=None):
        self.code = code
        root = ast.parse(code)
        self.root = AnyAllNodeTransformer().visit(root)
        self.complete_cb = complete_cb
        self.running = True
        self.complete = False
        self.return_value = None
        self.defer = {}

    def __call__(self):
        root_path = NodePath(self.root)
        while self.running and not self.complete:
            self._found_value = False
            self._evaluate(self.root, root_path)
            if not self._found_value:
                self.running = False

    def _defer(self, node, path):
        d = Defer()
        self.defer[d.id] = {'path': path, 'complete': False}
        node._defed = d.id
        return d

    def defer_return(self, id, value):
        data = self.defer.get(id)
        if not data:
            return # Spam
        if data['complete']:
            return # Duplicate return
        node = data['path']()
        if not node:
            return # Something crazy
        node._value = value
        data['complete'] = True
        data['value'] = value
        print 'Got defer return for %s = %s'%(node, value)
        self.running = True
        self()

    def _evaluate(self, node, path):
        if hasattr(node, '_value') or hasattr(node, '_defer'):
            return # Already evaluated or waiting
        
        complete_all = True
        complete_any = False
        for child in ast.iter_child_nodes(node):
            self._evaluate(child, path + child)
            if not hasattr(child, '_value') or isinstance(child._value, Defer):
                complete_all = False
                if not isinstance(node, Parallel):
                    # For all nodes other than Any and All, force exection to be 
                    # linear by only expanding a child once all prior children
                    # are fully evaluated
                    break
            else:
                complete_any = True
        
        if complete_all or (isinstance(node, Any) and complete_any):
            # Everything has values, we can fully evaluate this node
            fn = getattr(self, 'eval_'+type(node).__name__)
            node._value = fn(node, path)
            if not isinstance(node._value, Defer):
                self._found_value = True

    def eval_Module(self, node, path):
        # We have hit the top level, completed
        self.return_value = node.body[-1]._value
        self.complete = True
        if self.complete_cb:
            self.complete_cb(self.return_value)
        return self.return_value

    def eval_Expr(self, node, path):
        return node.value._value

    def eval_Num(self, node, path):
        return node.n

    def eval_BinOp(self, node, path):
        return node.op._value(node.left._value, node.right._value)

    def eval_Add(self, node, path):
        return operator.add

    def eval_Call(self, node, path):
        args = [n._value for n in node.args]
        if node.starargs:
            args += node.starargs._value
        kwargs = dict((n.arg, n.value._value) for n in node.keywords)
        if node.kwargs:
            for k, v in node.kwargs._value.iteritems():
                if k in kwargs:
                    raise TypeError("%s() got multiple values for keyword argument '%s'"%(node.func._value.__name__, k))
                kwargs[k] = v
        kwargs['node'] = node
        kwargs['path'] = path
        return node.func._value(*args, **kwargs)

    def eval_Name(self, node, path):
        if node.id == 'add':
            def add(x, y, node, path):
                import xmlrpclib
                s = xmlrpclib.ServerProxy('http://localhost:5001/')
                d = self._defer(node, path)
                s.add('http://localhost:5000/', d.id, x, y)
                return d
            return add
        raise NameError
    
    def eval_Load(self, node, path):
        # Still not sure what this is for
        return

    def eval_All(self, node, path):
        return [n._value for n in node.args]

    def eval_Any(self, node, path):
        for child in node.args:
            if hasattr(child, '_value') and not isinstance(child._value, Defer):
                return child._value
