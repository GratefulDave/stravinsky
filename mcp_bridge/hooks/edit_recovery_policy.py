import re

from .events import EventType, HookPolicy, PolicyResult, ToolCallEvent


class EditRecoveryPolicy(HookPolicy):
    """
    Policy to provide recovery guidance when Edit/MultiEdit tools fail.
    """

    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        if event.tool_name not in ["Edit", "MultiEdit", "replace"]:
            return PolicyResult(modified_data=event.output)

        if not event.output:
            return PolicyResult(modified_data=event.output)

        # Error patterns
        error_patterns = [
            r"oldString not found",
            r"oldString matched multiple times",
            r"line numbers out of range",
            r"does not match exactly",
            r"failed to find the target string",
        ]

        recovery_needed = any(re.search(p, event.output, re.IGNORECASE) for p in error_patterns)

        if recovery_needed:
            correction = (
                "\n\n[SYSTEM RECOVERY] It appears the Edit tool failed to find the target string. "
                "Please call 'Read' on the file again to verify the current content, "
                "then ensure your 'oldString' is an EXACT match including all whitespace."
            )
            return PolicyResult(
                modified_data=event.output + correction,
                message=correction,
            )

        return PolicyResult(modified_data=event.output)


if __name__ == "__main__":
    policy = EditRecoveryPolicy()
    policy.run_as_native()
