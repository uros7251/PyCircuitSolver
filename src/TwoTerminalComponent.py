from CurrentVoltageCharacteristic import CurrentVoltageCharacteristic, Value
from enum import Enum
from SIUnits import *

class ComponentType(Enum):
    IDEAL_VOLTAGE_SOURCE = 1
    IDEAL_CURRENT_SOURCE = 2
    RESISTOR = 3
    CAPACITOR = 4
    INDUCTOR = 5
    IMPEDANCE = 6
    SERIES = 7
    PARALLEL = 8

class TwoTerminalComponent():
    characteristic: CurrentVoltageCharacteristic
    state: tuple[complex, complex] | tuple[Value, Value]
    omega: float
    label: str

    def __init__(self, label: str) -> None:
        self.label = label
        self.characteristic = None
    
    @property
    def current(self) -> complex | Value:
        return self.state[0] if self.state else None
    
    @property
    def voltage(self) -> complex | Value:
        return self.state[1] if self.state else None
    
    @property
    def component_type(self) -> ComponentType:
        pass

    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        pass

    def current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        if self.characteristic is None or self.omega != omega:
            self.omega = omega
            self.characteristic = self.calculate_current_voltage_characteristic(omega)
        return self.characteristic  
    
    def apply_current(self, current: Value | complex, omega: float = 0, recursive: bool = False):
        self.state = (current,
                      self.current_voltage_characteristic(omega).voltage_at_current(current))
    
    def apply_voltage(self, voltage: Value | complex, omega: float = 0, recursive: bool = False):
        self.state = (self.current_voltage_characteristic(omega).current_at_voltage(voltage),
                      voltage)
    
    def reverse(self):
        return self
    
    def in_series_with(self, other):
        if other.component_type == ComponentType.SERIES:
            return other.in_series_with(self)
        return Series().add_component(self).add_component(other)
    
    def in_parallel_with(self, other):
        if other.component_type == ComponentType.PARALLEL:
            return other.in_parallel_with(self)
        return Parallel().add_component(self).add_component(other)
    
    def __invert__(self):
        return self.reverse()
    
    def __and__(self, other):
        if not isinstance(other, TwoTerminalComponent):
            raise Exception('Invalid operands!')
        return self.in_series_with(other)
    
    def __or__(self, other):
        if not isinstance(other, TwoTerminalComponent):
            raise Exception('Invalid operands!')
        return self.in_parallel_with(other)
    
class ComplexValuedTwoTerminalComponent(TwoTerminalComponent):
    value: complex

    def __init__(self, label: str, value: complex, unit: SIPrefix = SIPrefix.Nil) -> None:
        super().__init__(label)
        self.value = value * get_prefix_value(unit)

class RealValuedTwoTerminalComponent(TwoTerminalComponent):
    value: float

    def __init__(self, label: str, value: float, unit: SIPrefix = SIPrefix.Nil) -> None:
        super().__init__(label)
        self.value = value * get_prefix_value(unit)

class CompositeTwoTerminalComponent(TwoTerminalComponent):
    components: list[TwoTerminalComponent]

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.components = list()
    
    def add_component(self, component: TwoTerminalComponent):
        pass

    def remove_component(self, component: TwoTerminalComponent):
        pass

class IdealVoltageSource(ComplexValuedTwoTerminalComponent):

    @property
    def emf(self) -> complex:
        return self.value
    
    @emf.setter
    def emf(self, new_value):
        self.value = new_value

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.IDEAL_VOLTAGE_SOURCE
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(True, complex(0,0), self.value)
    
    def reverse(self):
        self.value = -self.value
        self.characteristic = None # force new calculation
        return self

class IdealCurrentSource(ComplexValuedTwoTerminalComponent):
    @property
    def amperage(self) -> complex:
        return self.value
    
    @amperage.setter
    def emf(self, new_value):
        self.value = new_value

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.IDEAL_CURRENT_SOURCE
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(False, complex(1,0), self.value)
    
    def reverse(self):
        self.value = -self.value
        self.characteristic = None # force new calculation
        return self
    
class Resistor(RealValuedTwoTerminalComponent):

    @property
    def resistance(self) -> float:
        return self.value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.RESISTOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(True, complex(-self.value, 0), complex(0,0))
    
class Capacitor(RealValuedTwoTerminalComponent):
    @property
    def capacitance(self) -> float:
        return self.value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.CAPACITOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic.open_circuit() if omega == 0 else CurrentVoltageCharacteristic(True, complex(0, 1/(omega*self.value)), complex(0,0))
    
class Inductor(RealValuedTwoTerminalComponent):
    @property
    def inductance(self) -> float:
        return self.value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.INDUCTOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic.short_circuit() if omega == 0 else CurrentVoltageCharacteristic(True, complex(0, -omega*self.value), complex(0,0))

class Impedance(ComplexValuedTwoTerminalComponent):
    @property
    def impedance(self) -> float:
        return self.value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.IMPEDANCE
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(True, -self.value, complex(0,0))

class Series(CompositeTwoTerminalComponent):
    fixed_current_component: TwoTerminalComponent

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SERIES
    
    def __init__(self, label: str = None) -> None:
        super().__init__(label)
        self.fixed_current_component = None

    def add_component(self, component: TwoTerminalComponent):
        if component.component_type == ComponentType.IDEAL_CURRENT_SOURCE:
            if self.fixed_current_component is None:
                self.fixed_current_component = component
            else:
                raise Exception('Two ideal current sources cannot be connected in series!')
        else:
            self.components.append(component)
        return self

    def remove_component(self, component: TwoTerminalComponent):
        if component.component_type == self.fixed_current_component:
            self.fixed_current_component = None
        else:
            self.components.remove(component)
        return self
        
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        if self.fixed_current_component:
            return self.fixed_current_component.current_voltage_characteristic(omega)
        elif self.components is None:
            return CurrentVoltageCharacteristic.short_circuit()
        characterstic = CurrentVoltageCharacteristic.short_circuit()
        for component in self.components:
            characterstic = characterstic & component.current_voltage_characteristic(omega)
        return characterstic
    
    def apply_current(self, current: Value | complex, omega: float, recursive: bool = True):
        if self.fixed_current_component:
            raise Exception('Cannot apply current to constant-current component')
        super().apply_current(current, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_current(current, omega, recursive)

    def apply_voltage(self, voltage: Value | complex, omega: float, recursive: bool = True):
        super().apply_voltage(voltage, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_current(self.current, omega)
            voltage -= component.voltage
        if self.fixed_current_component:
            self.fixed_current_component.apply_voltage(voltage, omega, recursive)

    def reverse(self):
        for component in self.components:
            component.reverse()
        if self.fixed_current_component:
            self.fixed_current_component.reverse()
        if self.characteristic:
            self.characteristic = ~self.characteristic

    def in_series_with(self, other: TwoTerminalComponent):
        if other.component_type == ComponentType.SERIES:
            for component in other.components:
                self.add_component(component)
        else:
            self.add_component(other)
        return self

class Parallel(CompositeTwoTerminalComponent):
    fixed_voltage_component: TwoTerminalComponent

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PARALLEL
    
    def __init__(self, label: str = None) -> None:
        super().__init__(label)
        self.fixed_voltage_component = None

    def add_component(self, component: TwoTerminalComponent):
        if component.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
            if self.fixed_voltage_component is None:
                self.fixed_voltage_component = component
            else:
                raise Exception('Two ideal voltage sources cannot be connected in parallel!')
        else:
            self.components.append(component)
        return self

    def remove_component(self, component: TwoTerminalComponent):
        if component.component_type == self.fixed_voltage_component:
            self.fixed_voltage_component = None
        else:
            self.components.remove(component)
        return self
        
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        if self.fixed_voltage_component:
            return self.fixed_voltage_component.current_voltage_characteristic(omega)
        elif self.components is None:
            return CurrentVoltageCharacteristic.open_circuit()
        characterstic = CurrentVoltageCharacteristic.open_circuit()
        for component in self.components:
            characterstic = characterstic | component.current_voltage_characteristic(omega)
        return characterstic
    
    def apply_current(self, current: Value | complex, omega: float, recursive: bool = True):
        super().apply_current(current, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_voltage(self.voltage, omega, recursive)
            current -= component.current
        if self.fixed_voltage_component:
            self.fixed_voltage_component.apply_current(current, omega, recursive)

    def apply_voltage(self, voltage: Value | complex, omega: float, recursive: bool = True):
        if self.fixed_voltage_component:
            raise Exception('Cannot apply voltage to constant-voltage component')
        super().apply_voltage(voltage, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_voltage(voltage, omega, recursive)

    def reverse(self):
        for component in self.components:
            component.reverse()
        if self.fixed_voltage_component:
            self.fixed_voltage_component.reverse()
        if self.characteristic:
            self.characteristic = ~self.characteristic

    def in_parallel_with(self, other: TwoTerminalComponent):
        if other.component_type == ComponentType.PARALLEL:
            for component in other.components:
                self.add_component(component)
        else:
            self.add_component(other)
        return self