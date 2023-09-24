import sys
sys.path.append("./src")
from circuit_solver import *
from cmath import isclose


class TestCircuitSolver():
    def test_mitic_textbook(self):
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

    def test_mitic_12_7(self):
        r1 = Resistor('R1', 1)
        r2 = Resistor('R2', 2)
        r3 = Resistor('R3', 1)
        r4 = Resistor('R4', 2)
        r5 = Resistor('R5', 1)
        
        e1 = IdealVoltageSource('E1', 1)
        e2 = IdealVoltageSource('E2', 2)
        e3 = IdealVoltageSource('E3', 3)
        e4 = IdealVoltageSource('E4', 7)
        e5 = IdealVoltageSource('E5', 3)

        branches = [
            Branch(1, 2, [e1, r1]),
            Branch(1, 3, [~e2, r2]),
            Branch(1, 4, [~e3, r3]),
            Branch(2, 3, [r5]),
            Branch(2, 4, [r4, ~e4]),
            Branch(3, 4, [e5])
        ]

        circuit = CircuitSolver(branches)
        circuit.solve()

        assert isclose(r1.current, -1)
        assert isclose(r2.current, -1)
        assert isclose(r3.current, 2)
        assert isclose(r4.current, 3)
        assert isclose(r5.current, -4)
        assert isclose(e5.current, -5)

    def test_mitic_8_1(self):
        z3 = Impedance('Z3', 1)
        z5 = Impedance('Z5', 1j)
        z4 = Impedance('Z4', 1-0.5j)
        z1 = Impedance('Z1', 0.5-1j)
        z2 = Impedance('Z2', -2j)

        e1 = IdealVoltageSource('E1', 3-2j)
        e2 = IdealVoltageSource('E2', -1)
        j = IdealCurrentSource('J', 1-1j)

        branches = [
            Branch(1, 2, [z4]),
            Branch(1, 3, [j, z2]),
            Branch(1, 4, [~e1, z1]),
            Branch(2, 3, [z5]),
            Branch(2, 4, [z3]),
            Branch(3, 4, [~e2])
        ]

        circuit = CircuitSolver(branches)
        circuit.solve()

        assert isclose(z1.current, 1)
        assert isclose(z3.current, -1-1j)
        assert isclose(e2.current, 1j)
        assert isclose(z4.current, -2+1j)
        assert isclose(z5.current, -1+2j)