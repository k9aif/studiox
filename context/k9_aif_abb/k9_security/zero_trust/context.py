# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IdentityContext:
    principal_id: str
    principal_type: str
    roles: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None


@dataclass
class AttributeContext:
    data_sensitivity: str = "low"
    environment: str = "dev"
    trust_zone: str = "internal"
    labels: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DestinationContext:
    destination_type: str
    destination_name: str
    destination_uri: Optional[str] = None
    is_external: bool = False


@dataclass
class ExecutionContext:
    request_id: str
    session_id: Optional[str]
    workflow_id: Optional[str]
    source_type: str
    action_type: str
    identity: IdentityContext
    attributes: AttributeContext
    destination: DestinationContext
    payload: Dict[str, Any] = field(default_factory=dict)