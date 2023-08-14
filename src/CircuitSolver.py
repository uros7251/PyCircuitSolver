from TwoTerminalComponent import *
from functools import reduce
import math, cmath

class Branch():
    """
    Wrapper class for a circuit branch consisting of source, sink identifiers and a list of components
    """
    source: int
    sink: int
    components: list[TwoTerminalComponent] | TwoTerminalComponent

    def __init__(self, source, sink, components) -> None:
        self.source = source
        self.sink = sink
        self.components = components

class Optimizer():
    """
    Base class to be extended by different optimizers. Updates parameters of the circuit ie. node potentials and branch currents.
    """
    params: list[Value]

    def __init__(self, params) -> None:
        self.params = params

    def step(self, loss: float = None) -> None:
        raise NotImplementedError()
    
    def zero_grad(self) -> None:
        for param in self.params:
            param.grad = 0+0j

class ExponentialBackoffGD(Optimizer):
    """
    Increases learning rate exponentially as long as loss is decreasing; reduces it when loss increases between two consecutive iterations (bad)
    """
    lr: float
    loss: float
    def __init__(self, params, learning_rate = 0.1) -> None:
        super().__init__(params)
        self.lr = learning_rate
        self.loss = float('inf')
    
    def step(self, loss: float) -> None:
        for param in self.params:
            param.data -= self.lr*param.grad
        if loss < self.loss:
            self.lr *= 2
        else:
            self.lr /= 16
        self.loss = loss


class Newton(Optimizer):
    """
    Calculates learning rate based on current loss and gradient norm (bad)
    """
    def step(self, loss: float) -> None:
        grad_norm_sq = reduce(lambda acc, param: acc + abs(param.grad)**2, self.params, 0.0)
        lr = 0.1*loss/grad_norm_sq
        for param in self.params:
            param.data -= lr * param.grad.conjugate()

class CircuitSolver():
    """
    Encapsulates logic for solving linear electric circuits 
    """
    reference_node: int | None
    node_potentials: dict[int, Value | complex]
    node_currents: dict[int, Value]
    branch_currents: dict[int, Value]
    optimizer: Optimizer
    components: dict[str, TwoTerminalComponent]

    def __init__(self, branches: list[Branch]) -> None:
        self.branches = branches
        self._init_components_dict()
        self._init_nodes()
        self._init_optimizer()

    @staticmethod
    def _init_value():
        return Value(0+0j)

    def _init_nodes(self):
        """
        Initialize voltages at nodes, currents through branches with constant voltage differences. These are 'learnable parameters'.
        """
        # TODO: write tests for this function

        self.reference_node = None
        self.node_currents = dict()
        self.node_potentials = dict()
        
        for i, branch in enumerate(self.branches):
            if len(branch.components) > 1:
                branch.components = reduce(lambda a, b: a & b, branch.components, Series())
            else:
                branch.components = branch.components[0]
            # first we only insert ideal voltage source components
            if branch.components.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
                voltage_delta = branch.components.current_voltage_characteristic(omega=0).free_coefficient
                if self.reference_node is None:
                    self.reference_node = branch.source
                    self.node_potentials[branch.source] = Value(0)
                elif branch.source not in self.node_potentials:
                    if branch.sink not in self.node_potentials:
                        self.node_potentials[branch.source] = CircuitSolver._init_value()
                        self.node_potentials[branch.sink] = self.node_potentials[branch.source] - voltage_delta
                    else:
                        self.node_potentials[branch.source] = self.node_potentials[branch.sink] + voltage_delta
                else:
                    if branch.sink not in self.node_potentials:
                        self.node_potentials[branch.sink] = self.node_potentials[branch.source] - voltage_delta
                    elif not cmath.isclose(self.node_potentials[branch.source].data - self.node_potentials[branch.sink].data, voltage_delta):
                        raise RuntimeError(f'Configuration invalid: nodes {branch.source}, {branch.sink}!')
                self.branch_currents[i] = CircuitSolver._init_value()
        
        for branch in self.branches:
            if self.reference_node is None:
                self.reference_node = branch.source
                self.node_potentials[branch.source] = Value(complex(0))
            if branch.source not in self.node_potentials:
                self.node_potentials[branch.source] = CircuitSolver._init_value()
            if branch.sink not in self.node_potentials:
                self.node_potentials[branch.sink] = CircuitSolver._init_value()

    def _init_components_dict(self) -> None:
        """
        A dict of components is maintained to enable queries on state of components.
        """
        self.components = dict()
        for branch in self.branches:
            for component in branch.components:
                self.components[component.label] = component

    def _init_optimizer(self) -> None:
        """
        Initialize optimization algo with learnable parameters.
        """
        learnable_params = []
        for node_id, node in self.node_potentials.items():
            # skip reference node and nodes whose voltage is not independent of other nodes
            if node_id != self.reference_node and node.is_leaf:
                learnable_params.append(node)
        for current in self.node_currents.values():
            learnable_params.append(current)
        # change optimizing algorithm here
        self.optimizer = Newton(learnable_params)

    def solve(self, omega: float = 0.) -> tuple[list[Value], dict[int, Value]]:
        """
        Finds the correct node voltages and branch currents via loss minimization

        Parameters:
        -----------
        omega: float
            Angular frequency of all the energy sources in the circuit
        """
        MAX_EPOCHS = int(1e4)
        history = []

        for i in range(MAX_EPOCHS):
            for node_id in self.node_potentials:
                self.node_currents[node_id] = 0.
            
            loss = self._loss(omega)
            history.append(loss.data.real)

            if i > 0 and math.isclose(loss.data.real, 0, abs_tol=1e-30):
                break
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step(loss.data.real)
        
        self._apply_node_voltages(omega)

        return history, {key: value for key, value in zip(self.node_potentials.keys(), map(lambda v: CircuitSolver._round_complex(v.data), self.node_potentials.values()))}
    
    def _loss(self, omega: float) -> Value:
        """
        Calculates the loss for current values of node voltages (and fixed-voltage branch currents).
        First, the net current going out of the node is calculated for each node
        Second, these values are squared and an average is evaluated across all nodes

        Parameters:
        -----------
        omega: float
            Angular frequency of all the energy sources in the circuit
        """
        for j, branch in enumerate(self.branches):
            if branch.components.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
                branch.components.apply_current(self.branch_currents[j], recursive=False)
            else:
                voltage_diff = self.node_potentials[branch.source]-self.node_potentials[branch.sink]
                branch.components.apply_voltage(voltage_diff, omega, recursive=True)
            self.node_currents[branch.source] += branch.components.current
            self.node_currents[branch.sink] -= branch.components.current

        return sum([abs(c) for c in self.node_currents.values()]) / len(self.node_currents)

    def _apply_node_voltages(self, omega: float = 0):
        """
        Apply current node voltages to the circuit.
        Electrical state of each element of the circuit is affected by this operation.

        Parameters:
        -----------
        omega: float
            Angular frequency of all the energy sources in the circuit
        """
        for branch in self.branches:
            voltage_diff = self.node_potentials[branch.source].data - self.node_potentials[branch.sink].data
            branch.components.apply_voltage(voltage_diff, omega, recursive=True)

    def state_at(self, label: str) -> tuple[complex, complex] | None:
        """
        Query on electrical state of a component identified by a given label
        """
        return None if label not in self.components or self.components[label].state is None else (CircuitSolver._round_complex(self.components[label].state[0]), CircuitSolver._round_complex(self.components[label].state[1]))
    
    @staticmethod
    def _round_complex(value: complex, ndigits: int = 5) -> complex:
        """
        Rounds a complex number.

        Parameters:
        -----------
        value: complex
            Value to be rounded
        ndigits: int
            Number of decimal places left after rounding
        """
        return complex(round(value.real, ndigits), round(value.imag, ndigits))