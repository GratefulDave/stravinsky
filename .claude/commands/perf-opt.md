# Performance Optimization

Performance analysis and optimization recommendations.

**Model Tier**: HIGH (GPT-5.2 / Claude Opus Thinking)

## Usage

```
/perf-opt <file, directory, or "hotspots">
```

## Workflow

1. **Profiling Context**
   - Identify performance-critical paths
   - Map data flow and I/O patterns
   - Locate computational hotspots
   
2. **Analysis** (using HIGH tier model)
   - Algorithmic complexity review (Big-O)
   - Memory usage patterns
   - I/O bottleneck identification
   - Concurrency and parallelization opportunities
   - Caching strategies
   - Database query optimization
   
3. **Recommendations**
   - Quick wins (low effort, high impact)
   - Strategic improvements (higher effort)
   - Architecture-level optimizations

## Output Format

```markdown
## Performance Analysis: <path>

### Hotspots Identified
| Location | Issue | Severity | Est. Impact |
|----------|-------|----------|-------------|
| file:line | [description] | HIGH/MED/LOW | [%improvement] |

### Quick Wins
1. **[Optimization]** (file:line)
   - Current: [what's happening]
   - Proposed: [what to do]
   - Expected gain: [metric]

### Strategic Improvements
1. **[Optimization]**
   - Effort: [LOW/MEDIUM/HIGH]
   - Impact: [description]
   - Implementation: [approach]

### Architecture Considerations
- [Caching strategy]
- [Async/parallel opportunities]
- [Data structure optimizations]
```

## Analysis Areas

- [ ] Loop optimization
- [ ] Memory allocation patterns
- [ ] I/O batching opportunities
- [ ] Query N+1 problems
- [ ] Caching candidates
- [ ] Parallelization opportunities
- [ ] Data structure selection
- [ ] Algorithm complexity

## Delegation

This skill uses `delphi` (GPT-5.2 HIGH tier) for deep performance analysis.

$ARGUMENTS
