
class Value:
    """ stores a single scalar value and its gradient """

    def __init__(self, data: complex, _children=(), _op=''):
        self.data: complex = data
        self.grad: complex = 0
        # internal variables used for autograd graph construction
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op # the op that produced this node, for graphviz / debugging / etc

    def __add__(self, other):
        if isinstance(other, Value):
            out = Value(self.data + other.data, (self, other), '+')

            def _backward():
                self.grad += out.grad
                other.grad += out.grad
            out._backward = _backward
        else:
            out = Value(self.data + other, (self,), '+')

            def _backward():
                self.grad += out.grad
            out._backward = _backward
        return out

    def __mul__(self, other):
        if isinstance(other, Value):
            out = Value(self.data * other.data, (self, other), '*')

            def _backward():
                self.grad += other.data*out.grad
                other.grad += self.data*out.grad
            out._backward = _backward
        else:
            out = Value(self.data * other, (self,), '*')

            def _backward():
                self.grad += other*out.grad
            out._backward = _backward
        return out

    def __truediv__(self, other):
        assert isinstance(other, (int, float, complex)), "only supporting division by int/float/complex"
        out = Value(self.data/other, (self,), f'/{other}')

        def _backward():
            self.grad += out.grad / other
        out._backward = _backward

        return out
    
    def __abs__(self):
        out = Value(abs(self.data)**2, (self,), f'.abs')

        def _backward():
            self.grad += 2 * self.data.conjugate() * out.grad
        out._backward = _backward

        return out
    
    @property
    def is_leaf(self):
        return self._op == ''
    
    def backward(self):

        # topological order all of the children in the graph
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        build_topo(self)

        # go one variable at a time and apply the chain rule to get its gradient
        self.grad = 1
        for v in reversed(topo):
            v._backward()

    def __neg__(self): # -self
        return self * -1

    def __radd__(self, other): # other + self
        return self + other

    def __sub__(self, other): # self - other
        return self + (-other)

    def __rsub__(self, other): # other - self
        return other + (-self)

    def __rmul__(self, other): # other * self
        return self * other

    def __repr__(self):
        return f"Value(data={self.data}, grad={self.grad})"