from .events import EventType, HookPolicy, PolicyResult, ToolCallEvent
from ..utils.truncation import truncate_output, TruncationStrategy


class TruncationPolicy(HookPolicy):
    def __init__(self, max_chars: int = 20000):
        self.max_chars = max_chars

    @property
    def event_type(self) -> EventType:
        return EventType.POST_TOOL_CALL

    async def evaluate(self, event: ToolCallEvent) -> PolicyResult:
        if not event.output or len(event.output) <= self.max_chars:
            return PolicyResult(modified_data=event.output)

        # Skip truncation for read_file since it handles its own truncation with log-awareness
        if event.tool_name == "read_file":
            return PolicyResult(modified_data=event.output)

        # Use middle truncation for general tool outputs
        modified = truncate_output(
            event.output, 
            limit=self.max_chars, 
            strategy=TruncationStrategy.MIDDLE
        )
        
        return PolicyResult(
            modified_data=modified,
            message=modified,  # Message is what gets printed in run_as_native
        )


if __name__ == "__main__":
    policy = TruncationPolicy()
    policy.run_as_native()

