#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Plugin system for third-party RAGFlow components.

This module provides a plugin manager for discovering and registering
third-party components that follow the standardized interface.

Example usage:

    # In your plugin package's setup.py:
    setup(
        name="ragflow-component-slack",
        entry_points={
            'ragflow.components': [
                'slack = ragflow_slack:SlackComponent',
            ],
        },
    )

    # In RAGFlow:
    from agent.plugins import plugin_manager

    # Discover and load all plugins
    plugin_manager.discover_plugins()

    # Get a component class
    SlackComponent = plugin_manager.get("Slack")

    # List all available components
    schemas = plugin_manager.list_components()
"""

import logging
from typing import Dict, List, Type, Optional
import importlib.metadata

from agent.component.base import StandardizedComponentBase

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manage third-party component plugins.

    The PluginManager discovers and registers components from:
    1. Entry points defined in installed packages
    2. Manually registered components

    Components must inherit from StandardizedComponentBase to be registered.
    """

    def __init__(self):
        """Initialize the plugin manager with empty component registry."""
        self._components: Dict[str, Type[StandardizedComponentBase]] = {}
        self._loaded_entry_points: set = set()

    def discover_plugins(self) -> None:
        """
        Discover installed plugins via entry points.

        Looks for entry points in the 'ragflow.components' group.
        Each entry point should point to a class that inherits from
        StandardizedComponentBase.
        """
        try:
            # Use importlib.metadata for Python 3.10+
            entry_points = importlib.metadata.entry_points()

            # Get ragflow.components group (handles both old and new API)
            if hasattr(entry_points, 'select'):
                # Python 3.10+ with new API
                ragflow_eps = entry_points.select(group='ragflow.components')
            else:
                # Python 3.9 with dict-like API
                ragflow_eps = entry_points.get('ragflow.components', [])

            for entry_point in ragflow_eps:
                if entry_point.name in self._loaded_entry_points:
                    continue

                try:
                    component_cls = entry_point.load()
                    self.register(component_cls)
                    self._loaded_entry_points.add(entry_point.name)
                    logger.info(f"Loaded plugin component: {entry_point.name}")
                except Exception as e:
                    logger.warning(f"Failed to load plugin {entry_point.name}: {e}")

        except Exception as e:
            logger.warning(f"Error discovering plugins: {e}")

    def register(self, component_cls: Type[StandardizedComponentBase]) -> None:
        """
        Register a component class.

        Args:
            component_cls: Component class to register. Must inherit from
                           StandardizedComponentBase.

        Raises:
            ValueError: If component_cls doesn't inherit from StandardizedComponentBase
            TypeError: If component_cls is not a class
        """
        if not isinstance(component_cls, type):
            raise TypeError(f"Expected a class, got {type(component_cls)}")

        if not issubclass(component_cls, StandardizedComponentBase):
            raise ValueError(
                f"Component {component_cls.__name__} must inherit from StandardizedComponentBase"
            )

        name = component_cls.component_name
        if name in self._components:
            logger.warning(f"Overwriting component: {name}")

        self._components[name] = component_cls
        logger.debug(f"Registered component: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a component by name.

        Args:
            name: Component name to unregister

        Returns:
            True if component was removed, False if not found
        """
        if name in self._components:
            del self._components[name]
            logger.debug(f"Unregistered component: {name}")
            return True
        return False

    def get(self, name: str) -> Type[StandardizedComponentBase]:
        """
        Get component class by name.

        Args:
            name: Component name

        Returns:
            Component class

        Raises:
            KeyError: If component not found
        """
        if name not in self._components:
            raise KeyError(f"Unknown component: {name}")
        return self._components[name]

    def get_or_none(self, name: str) -> Optional[Type[StandardizedComponentBase]]:
        """
        Get component class by name, or None if not found.

        Args:
            name: Component name

        Returns:
            Component class or None
        """
        return self._components.get(name)

    def has(self, name: str) -> bool:
        """
        Check if a component is registered.

        Args:
            name: Component name

        Returns:
            True if component exists
        """
        return name in self._components

    def list_components(self) -> List[dict]:
        """
        List all available components with their schemas.

        Returns:
            List of component schema dictionaries
        """
        return [cls.get_schema() for cls in self._components.values()]

    def list_names(self) -> List[str]:
        """
        List all registered component names.

        Returns:
            List of component names
        """
        return list(self._components.keys())

    def get_all(self) -> Dict[str, Type[StandardizedComponentBase]]:
        """
        Get all registered components.

        Returns:
            Dictionary mapping component names to classes
        """
        return self._components.copy()

    def clear(self) -> None:
        """Clear all registered components."""
        self._components.clear()
        self._loaded_entry_points.clear()
        logger.debug("Cleared all registered components")


# Global plugin manager instance
plugin_manager = PluginManager()


def discover_plugins() -> None:
    """Convenience function to discover plugins using the global manager."""
    plugin_manager.discover_plugins()


def register_component(component_cls: Type[StandardizedComponentBase]) -> None:
    """
    Convenience function to register a component with the global manager.

    Args:
        component_cls: Component class to register
    """
    plugin_manager.register(component_cls)


def get_component(name: str) -> Type[StandardizedComponentBase]:
    """
    Convenience function to get a component from the global manager.

    Args:
        name: Component name

    Returns:
        Component class
    """
    return plugin_manager.get(name)


def list_components() -> List[dict]:
    """
    Convenience function to list components from the global manager.

    Returns:
        List of component schemas
    """
    return plugin_manager.list_components()


__all__ = [
    'PluginManager',
    'plugin_manager',
    'discover_plugins',
    'register_component',
    'get_component',
    'list_components',
]
