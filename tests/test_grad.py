import sys
sys.path.append("./src")
from micrograd import *
from math import isclose

class TestMicrograd():
    def test_addition(self):
        x, y = Value(4+9j), Value(5-3j)
        z = x + y
        assert z.data == x.data + y.data
        z.backward()
        assert z.grad == x.grad
        assert z.grad == y.grad

    def test_multiplication(self):
        x, y = Value(4+9j), Value(5-3j)
        z = x * y
        assert isclose(abs(z.data - x.data * y.data), 0)
        z.backward()
        assert isclose(abs(z.grad * y.data - x.grad), 0)
        assert isclose(abs(z.grad * x.data - y.grad), 0)
    
    def test_division(self):
        x, y = Value(4+9j), 5-3j
        z = x/y
        assert isclose(abs(z.data - x.data / y), 0)
        z.backward()
        assert isclose(abs(z.grad/y - x.grad), 0)
        
    def test_abs(self):
        x = Value(4+9j)
        z = abs(x)
        assert isclose(abs(z.data - abs(x.data)**2), 0)
        z.backward()
        assert isclose(abs(2*z.grad*x.data.conjugate()-x.grad), 0)