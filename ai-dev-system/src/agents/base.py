"""Abstract base agent node — OCP / DIP / LSP.

All concrete agent nodes inherit from ``BaseAgentNode``.  The graph only
knows about this interface, making it trivial to add, swap, or mock agents
without touching ``graph.py``.
"""
from abc import ABC, abstractmethod

from src.state import GraphState


class BaseAgentNode(ABC):
    """
    Contract for every LangGraph node.

    Subclasses implement ``run`` to perform their single responsibility and
    return a **partial** state dict (only the keys they mutate).
    """

    @abstractmethod
    def run(self, state: GraphState) -> dict:
        """
        Execute the agent's logic given the current graph state.

        Args:
            state: The current ``GraphState``.

        Returns:
            A dict whose keys are a subset of ``GraphState`` fields.
        """

    def __call__(self, state: GraphState) -> dict:
        """Make instances directly usable as LangGraph node callables."""
        return self.run(state)
