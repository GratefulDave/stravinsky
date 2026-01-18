from enum import Enum

class OrchestrationPhase(Enum):
    CLASSIFY = "classify"
    CONTEXT = "context"
    WISDOM = "wisdom"
    PLAN = "plan"
    VALIDATE = "validate"
    DELEGATE = "delegate"
    EXECUTE = "execute"
    VERIFY = "verify"
