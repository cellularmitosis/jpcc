# This file defines the supported compiler targets.

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    "A compiler target."
    os: str
    arch: str

    def __str__(self):
        return f"{self.arch}_{self.os}"

    @classmethod
    def from_str(cls, target_str: str) -> Target:
        arch = target_str.split('_', maxsplit=1)[0]
        os = target_str.split('_', maxsplit=1)[1]
        target = Target(os, arch)
        return target


supported_targets = [
    Target.from_str("amd64_darwin"),
]


current_target = supported_targets[0]
