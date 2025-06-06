from typing import Generator
from current_voltage_characteristic import CurrentVoltageCharacteristic, Value
from enum import Enum
from si_units import *

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
    """
    Base class representing linear electric components with two terminals (ends). 
    """
    _characteristic: CurrentVoltageCharacteristic
    _state: tuple[complex, complex] | tuple[Value, Value]
    orientation: int = 1
    omega: float = 0
    label: str

    def __init__(self, label: str) -> None:
        self.label = label
        self._characteristic = None

    @property
    def current(self) -> complex | Value:
        """
        Returns current flowing through the component.
        """
        return self._state[0] if self._state else None
    
    @property
    def voltage(self) -> complex | Value:
        """
        Returns voltage difference between two terminals.
        """
        return self._state[1] if self._state else None
    
    @property
    def component_type(self) -> ComponentType:
        pass
    
    def traverse(self) -> Generator['TwoTerminalComponent', None, None]:
        """
        Traverses the component and its children. Returns the component itself or all its descendants.
        """
        yield self

    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        """
        Calculates current-voltage characteristic.
        
        Parameters:
        -----------
        omega: float
            Angular frequency at which current-voltage characteristic ought to be calculated
        Returns:
        Current-voltage characteristic
        """
        pass

    def current_voltage_characteristic(self, omega: float, with_orientation = False) -> CurrentVoltageCharacteristic:
        """
        Returns current-voltage characteristic. If it was already calculated earlier for the provided omega, it is not calculated again, but cached object is returned.
        
        Parameters:
        -----------
        omega: float
            Angular frequency at which current-voltage characteristic ought to be calculated
        Returns:
        Current-voltage characteristic
        """
        if self._characteristic is None or self.omega != omega:
            self.omega = omega
            self._characteristic = self.calculate_current_voltage_characteristic(omega)
        return ~self._characteristic if with_orientation and self.orientation == -1 else self._characteristic
    
    def apply_current(self, current: Value | complex, omega: float = 0, recursive: bool = True) -> None:
        """
        Imposes current flowing through the component. This operation affects the electric state of the component.

        Parameters:
        -----------
        current: Value | Complex
            Current flowing through the component
        omega: float
            Angular frequency
        recursive: bool
            Should a change of state of the component be propagated to its children? 
        """
        self._state = (current,
                      self.current_voltage_characteristic(omega).voltage_at_current(current))
    
    def apply_voltage(self, voltage: Value | complex, omega: float = 0, recursive: bool = True) -> None:
        """
        Imposes voltage difference across terminals of the component. This operation affects the electric state of the component.

        Parameters:
        -----------
        voltage: Value | Complex
            Voltage across terminals of the component
        omega: float
            Angular frequency
        recursive: bool
            Should a change of state of the component be propagated to its children? 
        """
        self._state = (self.current_voltage_characteristic(omega).current_at_voltage(voltage),
                      voltage)
    
    def flip(self) -> 'TwoTerminalComponent':
        """
        Returns the component flipped.
        """
        self.orientation = -1 * self.orientation
        return self
    
    def in_series_with(self, other) -> 'TwoTerminalComponent':
        """
        Combines two components in series.

        Returns:
        Resulting component
        """
        if other.component_type == ComponentType.SERIES:
            return other.in_series_with(self)
        return Series().add_component(self).add_component(other)
    
    def in_parallel_with(self, other) -> 'TwoTerminalComponent':
        """
        Combines two components in parallel.

        Returns:
        Resulting component
        """
        if other.component_type == ComponentType.PARALLEL:
            return other.in_parallel_with(self)
        return Parallel().add_component(self).add_component(other)
    
    def __invert__(self):
        return self.flip()
    
    def __and__(self, other):
        if not isinstance(other, TwoTerminalComponent):
            raise Exception(f'Invalid operands! The second operand is {type(other).__name__}!')
        return self.in_series_with(other)
    
    def __or__(self, other):
        if not isinstance(other, TwoTerminalComponent):
            raise Exception(f'Invalid operands! The second operand is {type(other).__name__}!')
        return self.in_parallel_with(other)
    
    def __iter__(self):
        yield from self.traverse()
    
class ComplexValuedTwoTerminalComponent(TwoTerminalComponent):
    """
    Base class for linear electric components which have to be characterized by a complex value.
    """
    value: complex

    def __init__(self, label: str, value: complex, unit: SIPrefix = SIPrefix.Nil) -> None:
        super().__init__(label)
        self.value = value * get_prefix_value(unit)

class RealValuedTwoTerminalComponent(TwoTerminalComponent):
    """
    Base class for linear electric components which can be characterized by a real value.
    """
    value: float

    def __init__(self, label: str, value: float, unit: SIPrefix = SIPrefix.Nil) -> None:
        super().__init__(label)
        self.value = value * get_prefix_value(unit)

class CompositeTwoTerminalComponent(TwoTerminalComponent):
    """
    Base class for linear electric components which consist of other linear electric components.
    """
    components: list[TwoTerminalComponent]

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.components = list()

    def traverse(self):
        for component in self.components:
            yield from component.traverse()

    
    def add_component(self, component: TwoTerminalComponent):
        pass

    def remove_component(self, component: TwoTerminalComponent):
        pass

class IdealVoltageSource(ComplexValuedTwoTerminalComponent):
    """
    Represents an ideal voltage source. It is characterized by electromotive force (in AC mode this means both amplitude and phase).
    """
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
        return CurrentVoltageCharacteristic(True, 0, self.value)

class Ammeter(IdealVoltageSource):
    """
    Represents an ammeter. Under the hood, it is just a special case of an ideal voltage source with zero electromotive force.
    """
    def __init__(self, label: str) -> None:
        super().__init__(label, 0)

class IdealCurrentSource(ComplexValuedTwoTerminalComponent):
    """
    Represents an ideal current source. It is characterized by current strength (in AC mode this means both amplitude and phase).
    """
    @property
    def amperage(self) -> complex:
        return self.value
    
    @amperage.setter
    def amperage(self, new_value):
        self.value = new_value

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.IDEAL_CURRENT_SOURCE
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(False, 1, self.value)

class Voltmeter(IdealCurrentSource):
    """
    Represents a voltmeter. Under the hood, it is just a special case of an ideal current source with zero current strength.
    """
    def __init__(self, label: str) -> None:
        super().__init__(label, 0)

class Resistor(RealValuedTwoTerminalComponent):
    """
    Represents a resistor. It is characterized by its resistance.
    """
    @property
    def resistance(self) -> float:
        return self.value
    
    @resistance.setter
    def resistance(self, new_value):
        self.value = new_value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.RESISTOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(True, -self.value, 0)
    
class Capacitor(RealValuedTwoTerminalComponent):
    """
    Represents a capacitor. It is characterized by its capacitance.
    """
    @property
    def capacitance(self) -> float:
        return self.value
    
    @capacitance.setter
    def capacitance(self, new_value):
        self.value = new_value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.CAPACITOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        assert not self.value == 0
        return CurrentVoltageCharacteristic.open_circuit() if omega == 0 else CurrentVoltageCharacteristic(True, 1j/(omega*self.value), 0)
    
class Inductor(RealValuedTwoTerminalComponent):
    """
    Represents an inductor. It is characterized by its inductance.
    """
    @property
    def inductance(self) -> float:
        return self.value
    
    @inductance.setter
    def inductance(self, new_value):
        self.value = new_value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.INDUCTOR
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic.short_circuit() if omega == 0 else CurrentVoltageCharacteristic(True, -1j*omega*self.value, 0)

class Impedance(ComplexValuedTwoTerminalComponent):
    """
    Represents a general passive element. It is characterized by its impedance.
    """
    @property
    def impedance(self) -> complex:
        return self.value
    
    @impedance.setter
    def impedance(self, new_value):
        self.value = new_value
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.IMPEDANCE
    
    def calculate_current_voltage_characteristic(self, omega: float) -> CurrentVoltageCharacteristic:
        return CurrentVoltageCharacteristic(True, -self.value, 0)

class Series(CompositeTwoTerminalComponent):
    """
    Represents a multitude of components connected in series.
    """
    fixed_current_component: IdealCurrentSource
    
    def __init__(self, label: str = None) -> None:
        super().__init__(label)
        self.fixed_current_component = None

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SERIES
    
    def traverse(self):
        if self.fixed_current_component:
            yield self.fixed_current_component
        yield from super().traverse()

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
            return self.fixed_current_component.current_voltage_characteristic(omega, with_orientation=True)
        elif self.components is None:
            return CurrentVoltageCharacteristic.short_circuit()
        characterstic = CurrentVoltageCharacteristic.short_circuit()
        for component in self.components:
            characterstic = characterstic & component.current_voltage_characteristic(omega, with_orientation=True)
        return characterstic
    
    def apply_current(self, current: Value | complex, omega: float, recursive: bool = True):
        if self.fixed_current_component:
            raise Exception('Cannot apply current to constant-current component')
        super().apply_current(current, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_current(current * component.orientation, omega, recursive)

    def apply_voltage(self, voltage: Value | complex, omega: float = 0, recursive: bool = True):
        super().apply_voltage(voltage, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_current(self.current * component.orientation, omega)
            voltage -= component.voltage * component.orientation
        if self.fixed_current_component:
            self.fixed_current_component.apply_voltage(voltage * self.fixed_current_component.orientation, omega, recursive)

    def in_series_with(self, other: TwoTerminalComponent):
        if other.component_type == ComponentType.SERIES:
            for component in other.components:
                self.add_component(component)
            if other.fixed_current_component:
                self.add_component(other.fixed_current_component)
        else:
            self.add_component(other)
        return self

class Parallel(CompositeTwoTerminalComponent):
    """
    Represents a multitude of components connected in parallel.
    """
    fixed_voltage_component: IdealVoltageSource
    
    def __init__(self, label: str = None) -> None:
        super().__init__(label)
        self.fixed_voltage_component = None

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PARALLEL
    
    def traverse(self):
        if self.fixed_voltage_component:
            yield self.fixed_voltage_component
        yield from super().traverse()
    
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
            return self.fixed_voltage_component.current_voltage_characteristic(omega, with_orientation=True)
        elif self.components is None:
            return CurrentVoltageCharacteristic.open_circuit()
        characterstic = CurrentVoltageCharacteristic.open_circuit()
        for component in self.components:
            characterstic = characterstic | component.current_voltage_characteristic(omega, with_orientation=True)
        return characterstic
    
    def apply_current(self, current: Value | complex, omega: float, recursive: bool = True):
        super().apply_current(current, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_voltage(self.voltage * component.orientation, omega, recursive)
            current -= component.current * component.orientation
        if self.fixed_voltage_component:
            self.fixed_voltage_component.apply_current(current * component.orientation, omega, recursive)

    def apply_voltage(self, voltage: Value | complex, omega: float = 0, recursive: bool = True):
        if self.fixed_voltage_component:
            raise Exception('Cannot apply voltage to constant-voltage component')
        super().apply_voltage(voltage, omega)
        if not recursive:
            return
        for component in self.components:
            component.apply_voltage(voltage * component.orientation, omega, recursive)

    def in_parallel_with(self, other: TwoTerminalComponent):
        if other.component_type == ComponentType.PARALLEL:
            for component in other.components:
                self.add_component(component)
            if other.fixed_voltage_component:
                self.add_component(other.fixed_voltage_component)
        else:
            self.add_component(other)
        return self