"""Deterministic local response adapter.

No external LLM provider is contacted by this repository.
"""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Clinical Billing CDI Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            f"[{self.system_name} local deterministic response] "
            "No external model was called. The prototype uses configured rules only."
        )


class LLMFactory:
    @staticmethod
    def create(provider: str = "mock", system_name: str = "Clinical Billing CDI Agent"):
        del provider
        return MockLLM(system_name)
