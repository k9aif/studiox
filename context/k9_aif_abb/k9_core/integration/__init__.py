# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Integration Package (ABB Layer)

The `k9_core.integration` package defines the **integration-level Architecture
Building Blocks (ABBs)** within the K9-AIF framework.

It provides the foundational abstractions for connecting K9-AIF components
to external systems, services, tools, and protocols.

This layer establishes a consistent, extensible model for integrating with:

- External APIs and services
- MCP (Model Context Protocol) endpoints
- HTTP-based tools and platforms
- Streaming or event-driven systems
- Enterprise connectors and third-party platforms


## Architectural Role

Within K9-AIF, integration is a core capability that enables agents,
orchestrators, and other components to interact with the external world.

Integration ABBs define:

- Standardized connection interfaces
- Protocol-agnostic communication patterns
- Extensible connector implementations
- Reusable integration contracts for SBBs


## Key Concepts

- **Connector Abstraction**  
  Base connectors define how communication with external systems is performed.

- **Protocol Adaptation**  
  Supports multiple protocols such as HTTP, MCP, and custom transports.

- **Pluggable Integration Layer**  
  SBB implementations can extend ABB connectors for specific providers or services.

- **Separation of Concerns**  
  Integration logic is isolated from agent reasoning and orchestration logic.


## Typical Components

This package may include:

- `base_connector` — Abstract connector interface
- `mcp_client_connector` — MCP-based client integration
- `mcp_http_connector` — HTTP-based MCP interaction
- `mcp_stdio_connector` — STDIO-based MCP communication


## Example: Using a Connector (Conceptual)

    from k9_aif_abb.k9_core.integration.base_connector import BaseConnector

    class MyConnector(BaseConnector):
        def connect(self):
            pass

        def send(self, payload):
            pass


## Relationship to Other Packages

- `k9_mcp` provides MCP-specific runtime servers and interaction patterns
- `k9_factories` instantiates connectors based on configuration
- `k9_agents` use connectors to interact with external tools
- `k9_orchestrators` may coordinate integration-driven workflows
- `k9_governance` may enforce policies on external interactions


## Architectural Note

k9_core.integration defines the abstraction layer for external connectivity,
while concrete implementations are provided as SBB extensions or protocol-specific modules.
"""
