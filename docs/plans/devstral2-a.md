# Stravinsky Development Plan: Phase 2 - Parallel Management & Orchestration

## Executive Summary

This document outlines the strategic plan to enhance Stravinsky's parallel management capabilities, add sophisticated orchestration features, and implement comprehensive performance monitoring to achieve feature parity with oh-my-opencode while maintaining Stravinsky's unique strengths.

## Current State Assessment

### Strengths
- Excellent Model Proxy architecture preventing head-of-line blocking
- Strong LSP integration with 35x speedup
- Comprehensive semantic search with file watching
- Native subagent pattern with good parallelism
- OAuth-first authentication with automatic fallback

### Critical Gaps
1. **Concurrency Management**: No limits on parallel agent spawning
2. **Explicit Orchestration**: Missing 7-phase orchestration system
3. **Context Management**: No automatic output truncation/compaction
4. **Skills System**: No skill-embedded MCPs or built-in skills
5. **Advanced Features**: Missing Ralph loop, keyword detector, interactive bash

## Strategic Objectives

### Phase 1: Critical Fixes (Week 1-2)
**Priority 1: Implement Concurrency Management**
- Add 3-tier concurrency limits (model → provider → default)
- Prevent provider overload with configurable limits
- Implement FIFO queues with proper task tracking

**Priority 2: Add Output Truncation & Compaction**
- Implement smart truncation with 50% headroom
- Add preemptive compaction at 85% context usage
- Create context window monitoring

### Phase 2: Orchestration Enhancement (Month 2-3)
**Priority 3: Implement 7-Phase Orchestrator**
- Add explicit orchestration phases
- Implement wisdom notepad for cross-session learning
- Create structured delegation patterns

**Priority 4: Add Skill-Embedded MCPs**
- Implement skill parsing with YAML frontmatter
- Create Playwright skill for browser automation
- Add Git Master skill for git operations

### Phase 3: Advanced Features (Month 4-6)
**Priority 5: Add Ralph Loop**
- Implement self-referential development loop
- Add iterative task completion with auto-continuation
- Create progress tracking and iteration limits

**Priority 6: Add Keyword Detector**
- Implement automatic mode activation
- Add ultrawork/search/ultrathink modes
- Enhance UX with smart detection

## Parallel Management Enhancements

### Current Mechanisms
- Asyncio-based concurrency with async/await patterns
- Semaphore-based rate limiting per model
- Background agents via subprocess spawning
- Multi-turn agentic loops support

### Limitations
- No concurrency limits (risk of provider overload)
- Basic task tracking (simple spawn/status)
- No notification batching
- FIFO queues only (no priority scheduling)

### Improvement Plan
1. **Concurrency Management**
   ```python
   class ConcurrencyManager:
       def __init__(self):
           self.default_limit = 5
           self.provider_limits = {
               "anthropic": 3,
               "openai": 5,
               "google": 10
           }
           self.model_limits = {
               "anthropic/claude-opus-4-5": 2,
               "google/gemini-3-flash": 10
           }
   ```

2. **Enhanced Task Management**
   - Comprehensive task state management
   - Notification batching
   - Priority scheduling capabilities

## Orchestration Capabilities

### Missing Features vs oh-my-opencode
1. **7-Phase Orchestration System**
   - Task Classification & Scope Definition
   - Context Gathering (Parallel)
   - Strategic Planning
   - Validation & Risk Assessment
   - Delegation (Parallel)
   - Execution & Monitoring
   - Synthesis & Iteration
   - Cleanup & Iteration

2. **Wisdom Notepad**
   - Persistent learning across sessions
   - Cross-session knowledge retention
   - Continuous improvement tracking

3. **Category-Based Routing**
   - Intelligent task routing
   - Automatic model selection
   - Intermediate delegation layer

### Implementation
```python
ORCHESTRATION_PHASES = [
    "Task Classification & Scope Definition",
    "Context Gathering (Parallel)",
    "Strategic Planning",
    "Validation & Risk Assessment",
    "Delegation (Parallel)",
    "Execution & Monitoring",
    "Synthesis & Iteration",
    "Cleanup & Iteration"
]
```

## Performance Monitoring

### Current State
- Basic logging and error reporting
- No comprehensive performance metrics
- No real-time monitoring dashboard
- Limited historical analysis

### Enhancement Opportunities
1. **Real-time Metrics Collection**
   - Task execution times
   - Agent response times
   - Resource utilization (CPU, memory)
   - Concurrent task counts

2. **Performance Dashboard**
   - Real-time visualization
   - Task execution tracking
   - Resource utilization metrics
   - Historical trend analysis

3. **Advanced Monitoring Features**
   - Rate limit monitoring and alerts
   - Error rate tracking
   - Performance anomaly detection
   - Capacity planning tools

### Implementation
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'task_execution_times': [],
            'agent_response_times': [],
            'resource_utilization': {},
            'concurrent_tasks': 0
        }
```

## Innovation Opportunities

### TUI Performance Dashboard
- Real-time agent performance monitoring
- Visual task execution tracking
- Resource utilization metrics
- Interactive performance analysis

### Enhanced Parallelism Patterns
- Parallel tool execution for independent operations
- Batch processing for common workflows
- Improved resource management for high-concurrency

### Advanced Caching Strategies
- Result caching for common queries
- Smart routing with token reduction
- Write-through cache invalidation

### Rust Integration Expansion
- Extend native performance to more tools
- Tree-sitter AST chunking for better code analysis
- Native file watching with robust shutdown

## Implementation Roadmap

### Week 1-2: Critical Fixes
- Implement concurrency management (HIGHEST PRIORITY)
- Add output truncation and compaction
- Fix critical parallel execution issues

### Month 2-3: Orchestration Expansion
- Implement 7-phase orchestrator
- Add skill-embedded MCPs
- Enhance agent management capabilities

### Month 4-6: Advanced Features
- Add Ralph loop and keyword detector
- Implement TUI performance dashboard
- Expand Rust integration

## Success Metrics

### Short-term (2 weeks)
- No provider overload incidents
- Stable parallel execution
- Basic context management working

### Medium-term (3 months)
- Full orchestration capabilities
- Skills system operational
- Enhanced performance monitoring

### Long-term (6 months)
- Complete feature parity with oh-my-opencode
- Advanced UX features working
- Production-ready performance

## Conclusion

This strategic plan addresses the critical gaps in Stravinsky's parallel management, adds sophisticated orchestration capabilities, and implements comprehensive performance monitoring. By following this roadmap, Stravinsky will achieve feature parity with oh-my-opencode while maintaining its unique strengths and positioning itself as a production-ready, highly optimized agent harness.
