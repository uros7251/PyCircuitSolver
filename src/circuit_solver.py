from two_terminal_component import *
from functools import reduce
import math, cmath

from two_terminal_component import Value

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

    def __init__(self, params: list[Value]) -> None:
        self.params = params

    def step(self, loss: float = None) -> Value:
        raise NotImplementedError()
    
    def zero_grad(self) -> None:
        for param in self.params:
            param.grad = 0+0j

class Newton(Optimizer):
    """
    Calculates learning rate based on current loss and gradient norm (bad)
    """
    def step(self, loss: float) -> None:
        grad_norm_sq = reduce(lambda acc, param: acc + abs(param.grad)**2, self.params, 0.0)
        lr = 0.01*loss/grad_norm_sq
        for param in self.params:
            param.data -= lr * param.grad.conjugate()

class Adam(Optimizer):
    """
    Implements Adam optimization algorithm. Dynamically adapts learning rate using exponential backoff. (not optimal)
    """
    m: list[Value]
    v: list[Value]
    BETA_m: float = 0.75
    BETA_v: float = 0.9
    beta_m_pow: float = 1
    beta_v_pow: float = 1
    lr: float = 1
    prev_loss: float = float('inf')
    def __init__(self, params: list[Value]) -> None:
        super().__init__(params)
        self.v, self.m = [], []
        for _ in range(len(self.params)):
            self.v.append(0)
            self.m.append(0+0j)

    def step(self, loss: float) -> Value:
        self.beta_m_pow *= self.BETA_m
        self.beta_v_pow *= self.BETA_v
        if loss > self.prev_loss:
            self.lr /= 10
        else:
            self.lr *= 1.2
        for i, param in enumerate(self.params):
            self.m[i] = (self.BETA_m*self.m[i] + (1-self.BETA_m)*param.grad.conjugate())/(1-self.beta_m_pow)
            self.v[i] = (self.BETA_v*self.v[i] + (1-self.BETA_v)*abs(param.grad)**2) # /(1-self.beta_v_pow)
            param.data -= self.lr * self.m[i]/(math.sqrt(self.v[i])+1e-30)
        self.prev_loss = loss

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

    def _init_nodes(self):
        """
        Initialize voltages at nodes, currents through branches with constant voltage differences. These are 'learnable parameters'.
        """
        # TODO: write tests for this function

        self.reference_node = None
        self.node_currents = dict()
        self.node_potentials = dict()
        self.branch_currents = dict()
        
        for i, branch in enumerate(self.branches):
            assert len(branch.components) > 0, "branche has to have at least one component!"
            if len(branch.components) == 1:
                branch.components = branch.components[0]
            else:
                branch.components = reduce(lambda a, b: a & b, branch.components, Series())
                
            # first we only insert ideal voltage source components
            if branch.components.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
                voltage_delta = branch.components.current_voltage_characteristic(omega=0).free_coefficient
                if self.reference_node is None:
                    self.reference_node = branch.source
                    self.node_potentials[branch.source] = Value(0)
                    self.node_potentials[branch.sink] = self.node_potentials[branch.source] - voltage_delta
                elif branch.source not in self.node_potentials:
                    if branch.sink not in self.node_potentials:
                        self.node_potentials[branch.source] = Value(0)
                        self.node_potentials[branch.sink] = self.node_potentials[branch.source] - voltage_delta
                    else:
                        self.node_potentials[branch.source] = self.node_potentials[branch.sink] + voltage_delta
                else:
                    if branch.sink not in self.node_potentials:
                        self.node_potentials[branch.sink] = self.node_potentials[branch.source] - voltage_delta
                    elif not cmath.isclose(self.node_potentials[branch.source].data - self.node_potentials[branch.sink].data, voltage_delta):
                        raise RuntimeError(f'Configuration invalid: nodes {branch.source}, {branch.sink}!')
                self.branch_currents[i] = Value(0)
        
        for branch in self.branches:
            if self.reference_node is None:
                self.reference_node = branch.source
                self.node_potentials[branch.source] = Value(0+0j)
            if branch.source not in self.node_potentials:
                self.node_potentials[branch.source] = Value(0+0j)
            if branch.sink not in self.node_potentials:
                self.node_potentials[branch.sink] = Value(0+0j)

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
        for current in self.branch_currents.values():
            learnable_params.append(current)
        self.optimizer = Adam(learnable_params)

    def _update_dependent_nodes(self):
        for node in self.node_potentials.values():
            if not node.is_leaf:
                node.data = node.inputs[0].data + node.inputs[1]

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
            loss = self._loss(omega)
            history.append(loss.data.real)

            if math.isclose(loss.data.real, 0, abs_tol=1e-30) or (i > 0 and math.isclose(history[-2], loss.data.real, rel_tol=1e-15)):
                break

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step(loss.data.real)
            # not forget to update dependent nodes
            self._update_dependent_nodes()
        
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

        Returns:
        loss: float
        """
        for node_id in self.node_potentials:
            self.node_currents[node_id] = 0.
        for j, branch in enumerate(self.branches):
            if branch.components.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
                branch.components.apply_current(self.branch_currents[j], recursive=False)
            else:
                voltage_diff = self.node_potentials[branch.source]-self.node_potentials[branch.sink]
                branch.components.apply_voltage(voltage_diff, omega, recursive=False)
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
            if branch.components.component_type == ComponentType.IDEAL_VOLTAGE_SOURCE:
                continue
            voltage_diff = self.node_potentials[branch.source].data - self.node_potentials[branch.sink].data
            branch.components.apply_voltage(voltage_diff, omega, recursive=True)
        for branch_id, current in self.branch_currents.items():
            self.branches[branch_id].components.apply_current(current.data, omega, recursive=True)

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