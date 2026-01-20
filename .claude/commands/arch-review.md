# Architecture Review

Comprehensive architecture review for the specified component or system.

**Model Tier**: HIGH (GPT-5.2 / Claude Opus Thinking)

## Usage

```
/arch-review <component or file path>
```

## Workflow

1. **Context Gathering**
   - Fire `explore` agent to map component structure
   - Fire `dewey` agent to find architectural patterns/best practices
   
2. **Analysis** (using HIGH tier model)
   - Design pattern evaluation
   - Dependency analysis
   - Interface design review
   - Coupling/cohesion assessment
   - Scalability considerations
   
3. **Report Generation**
   - Strengths identified
   - Concerns raised
   - Improvement recommendations
   - Priority-ranked action items

## Output Format

```markdown
## Architecture Review: <component>

### Overview
[Brief description of component purpose]

### Strengths
- [strength 1]
- [strength 2]

### Concerns
- [concern 1 - severity: HIGH/MEDIUM/LOW]
- [concern 2 - severity: HIGH/MEDIUM/LOW]

### Recommendations
1. [Recommendation with rationale]
2. [Recommendation with rationale]

### Action Items
- [ ] [Specific actionable task]
- [ ] [Specific actionable task]
```

## Delegation

This skill automatically delegates to `delphi` (GPT-5.2 HIGH tier) for the core architectural analysis.

$ARGUMENTS
