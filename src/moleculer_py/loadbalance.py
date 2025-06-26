import random
from typing import List, Tuple, Optional, Any

from .data import Registry, ActionInfo


class LoadBalanceStrategy:
    """
    Base class for load balancing strategies.
    """

    def select_node(
        self, registry: Registry, action_name: str
    ) -> Optional[Tuple[str, ActionInfo]]:
        raise NotImplementedError


class RoundRobinStrategy(LoadBalanceStrategy):
    """
    Selects a random node among all nodes that provide the given action.
    (Note: true round-robin would cycle, but random is simpler and avoids state.)
    """

    def select_node(
        self, registry: Registry, action_name: str
    ) -> Optional[Tuple[str, ActionInfo]]:
        candidates: List[Tuple[str, ActionInfo]] = []
        for node_id, node in registry.nodes.items():
            if not node.isOnline:
                continue
            for service in node.services:
                for action in service.actions.values():
                    if action.name == action_name:
                        candidates.append((node_id, action))
        if not candidates:
            return None
        return random.choice(candidates)
