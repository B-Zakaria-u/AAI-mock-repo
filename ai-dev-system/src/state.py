from typing import TypedDict

class GraphState(TypedDict):
    ticket_text: str
    spec: str
    spec_feedback: str
    test_output: str
    tests_passed: bool
    pr_url: str
    iteration_count: int
