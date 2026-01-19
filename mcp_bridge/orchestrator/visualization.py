from .enums import OrchestrationPhase

def format_phase_progress(current_phase: OrchestrationPhase) -> str:
    """Formats the current phase as a progress string."""
    phases = list(OrchestrationPhase)
    total = len(phases)
    
    # Find index (1-based)
    try:
        index = phases.index(current_phase) + 1
    except ValueError:
        index = 0
        
    return f"[Phase {index}/{total}: {current_phase.name}]"
