from micrograd import Value

class CurrentVoltageCharacteristic():
    """
    Represents a linear current-voltage characteristic of the form a * V + b * I = c.
    Coefficient 'a' is stored as boolean value distinguishing two types of characteristic:
    1) I = c,            used for constant current electric components;
    2) V + b * I = c,    used for other types of electric components.
    Coefficient 'b' and 'c' are complex numbers so both DC and AC mode is supported.
    """
    a: bool
    b: complex
    c: complex

    def __init__(self, a: bool, b: complex, c: complex) -> None:
        self.a = a
        self.b = b
        self.c = c

    def __str__(self) -> str:
        if self.has_fixed_current:
            return f'I = {self.c}'
        elif self.has_fixed_voltage:
            return f'V = {self.c}'
        return f'V + ({self.b})Z = {self.c}'
    
    @property
    def has_fixed_current(self) -> bool:
        """
        Returns True if characterstic has form I = c, otherwise False.
        """
        return not self.a
    
    @property
    def has_fixed_voltage(self) -> bool:
        """
        Returns True if characterstic has form V = c, otherwise False.
        """
        return self.a and abs(self.b) == 0
    
    @property
    def impedance_coefficient(self) -> complex:
        """
        Returns coefficient b.
        """
        return -self.b
    
    @property
    def free_coefficient(self) -> complex:
        """
        Returns coefficient c.
        """
        return self.c
    
    def current_at_voltage(self, voltage: Value | complex) -> Value | complex:
        """
        Calculates and returns the current flowing through the component for a given voltage across it.
        """
        if self.has_fixed_voltage:
            raise Exception('Cannot apply voltage to constant voltage component')
        if self.has_fixed_current:
            return self.c
        return (voltage - self.c) / (-self.b)
    
    def voltage_at_current(self, current: Value | complex) -> Value | complex:
        """
        Calculates and returns the voltage across the component for a given current flowing through it.
        """
        if self.has_fixed_current:
            raise Exception('Cannot apply current to constant current component')
        if self.has_fixed_voltage:
            return self.c
        return -self.b * current + self.c
    
    def __invert__(self) -> 'CurrentVoltageCharacteristic':
        """
        Returns an inverted (flipped) characteristic. Makes no difference for purely passive components.
        For example, it converts V = V_0 to V = -V_0.
        """
        return CurrentVoltageCharacteristic(self.a, self.b, -self.c)
    
    def __and__(self, other) -> 'CurrentVoltageCharacteristic':
        """
        Combines two characteristics in series.
        """
        if not isinstance(other, CurrentVoltageCharacteristic):
            raise Exception('Both operands of AND operation must be CurrentVoltageCharacteristic')
        if self.has_fixed_current and other.has_fixed_current:
            raise Exception('Cannot add two constant-current components in series')
        if self.has_fixed_current:
            return self
        if other.has_fixed_current:
            return other
        return CurrentVoltageCharacteristic(True, self.b + other.b, self.c + other.c)
    
    def __or__(self, other) -> 'CurrentVoltageCharacteristic':
        """
        Combines two characteristics in parallel.
        """
        if not isinstance(other, CurrentVoltageCharacteristic):
            raise Exception('Both operands of OR operation must be CurrentVoltageCharacteristic')
        if self.has_fixed_voltage and other.has_fixed_voltage:
            raise Exception('Cannot add two constant-voltage components in parallel')
        if self.has_fixed_current:
            if other.has_fixed_current:
                return CurrentVoltageCharacteristic(False, 1, self.c + other.c)
            else:
                return CurrentVoltageCharacteristic(True, other.b, other.c + other.b * self.c)
        else:
            if other.has_fixed_current:
                return CurrentVoltageCharacteristic(True, self.b, self.c + self.b * other.c)
            else:
                return CurrentVoltageCharacteristic(
                    True,
                    (self.b * other.b) / (self.b + other.b),
                    (self.c * other.b + other.c * self.b) / (self.b + other.b)
                )
    
    @staticmethod
    def open_circuit() -> 'CurrentVoltageCharacteristic':
        """
        Returns the current-voltage characteristic of open circuit.
        """
        return CurrentVoltageCharacteristic(False, complex(1, 0), complex(0,0))
    
    @staticmethod
    def short_circuit() -> 'CurrentVoltageCharacteristic':
        """
        Returns the current-voltage characteristic of short circuit.
        """
        return CurrentVoltageCharacteristic(True, complex(0,0), complex(0,0))