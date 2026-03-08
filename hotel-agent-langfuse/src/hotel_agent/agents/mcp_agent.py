"""MCP Agent — Model Context Protocol manager for tool registration and discovery.

Responsibilities:
- Manages tool registration and discovery via MCP-style protocol
- Provides standardized tool interfaces for all agents
- Handles tool capability descriptions and versioning
- Enables external system integration through a unified tool registry
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """MCP-style tool definition."""
    name: str
    description: str
    category: str  # booking, billing, knowledge, system
    version: str = "1.0.0"
    parameters: dict[str, Any] = field(default_factory=dict)
    callable: Callable | None = None
    enabled: bool = True


class MCPAgent:
    """Model Context Protocol agent — manages tool registry and discovery.

    Implements a lightweight MCP-inspired pattern for:
    1. Registering tools with metadata
    2. Discovering tools by category or capability
    3. Providing tool schemas to LLM agents
    4. Tracking tool usage and availability
    """

    def __init__(self) -> None:
        self._registry: dict[str, ToolDefinition] = {}
        self._usage_counts: dict[str, int] = {}

    def register_tool(self, tool_def: ToolDefinition) -> None:
        """Register a tool in the MCP registry."""
        self._registry[tool_def.name] = tool_def
        self._usage_counts.setdefault(tool_def.name, 0)
        logger.info("MCP: Registered tool '%s' (category=%s)", tool_def.name, tool_def.category)

    def discover_tools(self, category: str = "", enabled_only: bool = True) -> list[ToolDefinition]:
        """Discover available tools, optionally filtered by category."""
        tools = list(self._registry.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a specific tool by name."""
        return self._registry.get(name)

    def get_tool_schemas(self, category: str = "") -> list[dict[str, Any]]:
        """Get OpenAI-compatible tool schemas for LLM function calling."""
        tools = self.discover_tools(category=category)
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "category": t.category,
                "version": t.version,
            }
            for t in tools
        ]

    def record_usage(self, tool_name: str) -> None:
        """Record that a tool was used (for observability)."""
        self._usage_counts[tool_name] = self._usage_counts.get(tool_name, 0) + 1

    def get_usage_stats(self) -> dict[str, int]:
        """Get tool usage statistics."""
        return dict(self._usage_counts)

    def disable_tool(self, name: str) -> bool:
        """Disable a tool (e.g. during maintenance)."""
        tool = self._registry.get(name)
        if tool:
            tool.enabled = False
            logger.info("MCP: Disabled tool '%s'", name)
            return True
        return False

    def enable_tool(self, name: str) -> bool:
        """Re-enable a disabled tool."""
        tool = self._registry.get(name)
        if tool:
            tool.enabled = True
            logger.info("MCP: Enabled tool '%s'", name)
            return True
        return False

    def get_status(self) -> dict[str, Any]:
        """Get overall MCP agent status."""
        tools = list(self._registry.values())
        return {
            "total_tools": len(tools),
            "enabled_tools": sum(1 for t in tools if t.enabled),
            "categories": list({t.category for t in tools}),
            "usage_stats": self.get_usage_stats(),
        }


# Singleton instance
mcp_agent = MCPAgent()


def register_all_tools() -> None:
    """Register all hotel system tools with the MCP agent."""
    from hotel_agent.tools.booking_tools import (
        check_availability, create_booking, cancel_booking, modify_booking,
    )
    from hotel_agent.tools.billing_tools import get_bill, process_refund, apply_discount
    from hotel_agent.tools.knowledge_base import search_hotel_info

    # Booking tools
    for tool_fn, desc in [
        (check_availability, "Check room availability for dates"),
        (create_booking, "Create a new guest reservation"),
        (cancel_booking, "Cancel an existing reservation"),
        (modify_booking, "Modify booking dates or room type"),
    ]:
        mcp_agent.register_tool(ToolDefinition(
            name=tool_fn.name,
            description=desc,
            category="booking",
            callable=tool_fn,
        ))

    # Billing tools
    for tool_fn, desc in [
        (get_bill, "Retrieve itemized guest bill"),
        (process_refund, "Process a guest refund"),
        (apply_discount, "Apply promotional discount code"),
    ]:
        mcp_agent.register_tool(ToolDefinition(
            name=tool_fn.name,
            description=desc,
            category="billing",
            callable=tool_fn,
        ))

    # Knowledge tools
    mcp_agent.register_tool(ToolDefinition(
        name=search_hotel_info.name,
        description="Search hotel knowledge base (policies, rooms, facilities, FAQs)",
        category="knowledge",
        callable=search_hotel_info,
    ))

    logger.info("MCP: All %d tools registered", len(mcp_agent._registry))
