import sys
sys.path.append("./src")
from micrograd import *
from cmath import isclose, phase, pi

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
        assert isclose(z.data, x.data * y.data)
        z.backward()
        assert isclose(z.grad * y.data, x.grad)
        assert isclose(z.grad * x.data, y.grad)
    
    def test_division(self):
        x, y = Value(4+9j), 5-3j
        z = x/y
        assert isclose(z.data, x.data / y)
        z.backward()
        assert isclose(z.grad/y, x.grad)
        
    def test_abs(self):
        x = Value(4+9j)
        z = abs(x)
        assert isclose(z.data, abs(x.data)**2)
        z.backward()
        assert isclose(z.grad*2*x.data.conjugate(), x.grad)

    def test_phase(self):
        z = Value(1+1j)
        phi = z.phase()
        assert isclose(phi.data, phase(1+1j))
        phi.backward()
        assert isclose(z.grad, -(z.data.imag+1j*z.data.real)/abs(z.data)**2)

    def test_real(self):
        z = Value(1+1j)
        re = z.real()
        assert isclose(re.data, z.data.real)
        re.backward()
        assert isclose(z.grad, re.grad.real)

    def test_imag(self):
        z = Value(1+1j)
        im = z.imag()
        assert isclose(im.data, 1j*z.data.imag)
        im.backward()
        assert isclose(z.grad, -1j*im.grad.real)