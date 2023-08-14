import sys
sys.path.append("./src")
from CircuitSolver import *
from cmath import isclose


class TestCircuitSolver():
    def test_circuit(self):
        r1 = Resistor('R1', 200)
        r2 = Resistor('R2', 100)
        r3 = Resistor('R3', 100)
        r4 = Resistor('R4', 50)
        r5 = Resistor('R5', 100)

        e1 = IdealVoltageSource('E1', 1)
        j1 = IdealCurrentSource('J1', 20, SIPrefix.Milli)
        j2 = IdealCurrentSource('J2', 10, SIPrefix.Milli)

        branches = [
            Branch(1,4,[j1, r1]),
            Branch(1,4,[r2]),
            Branch(1,2,[r3]),
            Branch(2,3,[r4,~e1]),
            Branch(2,3,[r5]),
            Branch(3,4, [j2])
        ]

        circuit = CircuitSolver(branches=branches)

        circuit.solve()

        assert isclose(r1.current, 20e-3)
        assert isclose(r1.voltage, 4)

        assert isclose(j1.voltage, -7)

        assert isclose(r2.current, -30e-3)
        assert isclose(r2.voltage, -3)

        assert isclose(r3.current, 10e-3)
        assert isclose(r3.voltage, 1)

        assert isclose(r4.current, 40e-3/3)
        assert isclose(r4.voltage, 2./3)

        assert isclose(e1.current, 40e-3/3)

        assert isclose(r5.current, -10e-3/3)
        assert isclose(r5.voltage, -1./3)

        assert isclose(j2.voltage, -11./3)