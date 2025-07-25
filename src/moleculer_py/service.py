import inspect
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .broker import Broker


def action(
    name: Optional[str] = None,
    cache: bool = False,
    params: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to mark a method as a Moleculer action.
    """

    def decorator(func):
        func._moleculer_action = {
            "name": name or func.__name__,
            "rawName": name or func.__name__,
            "cache": cache,
            "params": params or {},
            "handler": func,
        }
        return func

    return decorator


def event(
    name: Optional[str] = None,
):
    """
    Decorator to mark a method as a Moleculer event.
    """

    def decorator(func):
        func._moleculer_event = {
            "name": name or func.__name__,
            "handler": func,
        }
        return func

    return decorator


class BaseService:
    def __init__(
        self,
        broker: "Broker",
        name: str,
        settings: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ):
        self.broker = broker
        self.name = name
        self.settings = settings or {}
        self.version = version
        self.actions = self._collect_actions()
        self.events = self._collect_events()
        # Register this service with the broker
        # The broker expects a dict with at least 'actions' key
        actions_dict = {}
        for a_name, a in self.actions.items():
            action_def = {k: v for k, v in a.items() if k != "handler"}
            actions_dict[a_name] = action_def

        event_dict = {}
        for a_name, a in self.events.items():
            event_def = {k: v for k, v in a.items() if k != "handler"}
            event_dict[a_name] = event_def

        service_def = {
            "name": self.name,
            "metadata": {},
            "fullName": self.name,
            "version": self.version,
            "settings": self.settings,
            "actions": actions_dict,
            "events": event_dict,
        }
        self.broker.register_service(self.name, self, service_def)

    def _collect_actions(self) -> Dict[str, Dict[str, Any]]:
        actions = {}
        for name, method in inspect.getmembers(
            self, predicate=inspect.iscoroutinefunction
        ):
            if hasattr(method, "_moleculer_action"):
                action_info = method._moleculer_action.copy()
                action_info["handler"] = method
                # Set action name to service.name + action name
                full_action_name = f"{self.name}.{action_info['name']}"
                action_info["name"] = full_action_name
                action_info["rawName"] = full_action_name
                actions[full_action_name] = action_info
        return actions

    def _collect_events(self) -> Dict[str, Dict[str, Any]]:
        events = {}
        for name, method in inspect.getmembers(
            self, predicate=inspect.iscoroutinefunction
        ):
            if hasattr(method, "_moleculer_event"):
                event_info = method._moleculer_event.copy()
                event_info["handler"] = method
                full_event_name = f"{event_info['name']}"
                event_info["name"] = full_event_name
                events[full_event_name] = event_info
        return events

    def get_action(self, name: str) -> Optional[Callable]:
        action = self.actions.get(name)
        if action:
            return action["handler"]
        return None

    def get_event(self, name: str) -> Optional[Callable]:
        event = self.events.get(name)
        if event:
            return event["handler"]
        return None
