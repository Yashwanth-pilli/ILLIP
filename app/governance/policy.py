from dataclasses import dataclass, field
from enum import Enum
from typing import List


class PolicyLevel(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


@dataclass
class GovernancePolicy:
    name: str
    description: str
    level: PolicyLevel
    applies_to: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "applies_to": self.applies_to,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GovernancePolicy":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            level=PolicyLevel(data.get("level", "allow")),
            applies_to=data.get("applies_to", []),
        )


DEFAULT_POLICIES: dict[str, GovernancePolicy] = {
    "agent_execution": GovernancePolicy(
        name="agent_execution",
        description="Allow agents to execute tasks",
        level=PolicyLevel.ALLOW,
        applies_to=["agent"],
    ),
    "plugin_install": GovernancePolicy(
        name="plugin_install",
        description="Require approval before installing plugins",
        level=PolicyLevel.REQUIRE_APPROVAL,
        applies_to=["plugin"],
    ),
    "self_update": GovernancePolicy(
        name="self_update",
        description="Require approval before applying self-updates",
        level=PolicyLevel.REQUIRE_APPROVAL,
        applies_to=["update"],
    ),
    "network_access": GovernancePolicy(
        name="network_access",
        description="Allow outbound network access for search and APIs",
        level=PolicyLevel.ALLOW,
        applies_to=["network"],
    ),
    "file_write_outside_data": GovernancePolicy(
        name="file_write_outside_data",
        description="Block writes outside the data directory",
        level=PolicyLevel.BLOCK,
        applies_to=["file_write"],
    ),
    "high_risk_tool": GovernancePolicy(
        name="high_risk_tool",
        description="Require approval for tools that mutate external systems",
        level=PolicyLevel.REQUIRE_APPROVAL,
        applies_to=["tool"],
    ),
}
