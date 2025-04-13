# This file defines the supported compiler targets.

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    "A compiler target."
    os: str
    arch: str

    def __str__(self):
        return f"{self.os}-{self.arch}"

    @classmethod
    def from_str(cls, target_str: str) -> Target:
        os = target_str.split('-')[0]
        arch = target_str.split('-')[1]
        target = Target(os, arch)
        return target


supported_targets = [
    Target.from_str("darwin-x86_64"),
]


current_target = supported_targets[0]
