from .events import EventType, HookPolicy, PolicyResult, ToolCallEvent


class TruncationPolicy(HookPolicy):
    def __init__(self, max_chars: int = 30000):
        self.max_chars = max_chars

    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        if not event.output or len(event.output) <= self.max_chars:
            return PolicyResult(modified_data=event.output)

        header = f"[TRUNCATED - {len(event.output)} chars reduced to {self.max_chars}]\n"
        footer = "\n...[TRUNCATED]"
        truncated = event.output[:self.max_chars]

        modified = header + truncated + footer
        return PolicyResult(
            modified_data=modified,
            message=modified,  # Message is what gets printed in run_as_native
        )


if __name__ == "__main__":
    policy = TruncationPolicy()
    policy.run_as_native()

