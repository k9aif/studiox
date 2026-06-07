# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF MCP Package

The `k9_mcp` package provides MCP-oriented runtime components within the
K9-AIF framework.

It supports interaction with MCP-compatible services and tools, enabling
agents and other framework components to consume external capabilities such
as weather, inference, orchestration, and tool-based services through
standardized MCP communication patterns.

This package complements the integration abstractions defined in
`k9_core.integration` by enabling concrete MCP-facing runtime interaction.


## Key Responsibilities

- Supporting MCP-based runtime interaction with external tools and services
- Enabling agents to consume MCP capabilities through client connections
- Hosting MCP-compatible runtime servers where applicable
- Providing reusable MCP communication patterns for framework extensions
- Supporting protocol-driven integration with external systems


## Typical Components

This package may include:

- `mcp_inference_server` — MCP-facing inference server
- `mcp_orchestrator_server` — MCP-facing orchestration server
- `servers` — shared MCP server support components


## Example: Using an MCP Client Connection

    from k9_aif_abb.k9_factories.mcp_client_connection_factory import MCPClientConnectionFactory

    factory = MCPClientConnectionFactory.from_config(config)
    client = factory.get_connection("weather")

    await client.connect()
    result = await client.call_tool("get_weather", {"city": "Boston"})

"""