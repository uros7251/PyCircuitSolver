import sys
sys.path.append("./src")
from TwoTerminalComponent import *
from cmath import isclose, phase, pi

class TestTwoTerminalComponent():
    def test_simple_series(self):
        r1 = Resistor('R1', 100)
        e1 = IdealVoltageSource('E1', 12)
        circuit = ~e1 & r1
        circuit.apply_voltage(0, omega=0, recursive=True)
        assert isclose(r1.voltage, 12)
        assert isclose(r1.current, 12/100)

    def test_simple_parallel(self):
        r1 = Resistor('R1', 100)
        r2 = Resistor('R2', 400)
        e1 = IdealVoltageSource('E1', 100)
        circuit = ~e1 & (r1 | r2)
        circuit.apply_voltage(0, omega=0, recursive=True)
        assert isclose(circuit.current, 100*(1/100 + 1/400))
        assert isclose(r1.voltage, 100)

    def test_simple_rlc(self):
        omega = 1e4
        r = Resistor('R', 100)
        l = Inductor('L', 1, SIPrefix.Milli)
        c = Capacitor('C', 1, SIPrefix.Micro)
        e = IdealVoltageSource('E', 12)
        circuit = ~e & r & l & c
        circuit.apply_voltage(0, omega=omega)
        assert isclose(circuit.current, 12./(100-90j))
        assert isclose(l.voltage, (omega*0.001j)*circuit.current)

    def test_complex_reactive_free_circuit(self):
        r1 = Resistor('R1', 200)
        r2 = Resistor('R2', 100)
        r3 = Resistor('R3', 100)
        r4 = Resistor('R4', 50)
        r5 = Resistor('R5', 100)

        e1 = IdealVoltageSource('E1', 1)
        j1 = IdealCurrentSource('J1', 20, SIPrefix.Milli)
        j2 = IdealCurrentSource('J2', 10, SIPrefix.Milli)

        b1 = j1 & r1
        b2 = r4 & ~e1
        b3 = r3 & (b2 | r5) & j2

        circuit = b1 | r2 | b3
        circuit.apply_current(0, omega=0)

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

    def test_mitic_7_28(self):
        x_c = Impedance('X_C', -4j)
        x_l1 = Impedance('X_L1', 2j)
        x_l2 = Impedance('X_L2', 2j)
        r1 = Resistor('R1', 5)
        r2 = Resistor('R2', 5)

        e1 = IdealVoltageSource('E1', 10)

        circuit = ~e1 & x_l1 & (r1 | (x_c & (x_l2 | r2)))

        circuit.apply_voltage(0)
        
        I1_2 = e1.current / r2.current

        assert isclose(abs(I1_2), 3.3)
        assert isclose(phase(I1_2), -pi/2)

#TestTwoTerminalComponent().test_mitic_7_28()