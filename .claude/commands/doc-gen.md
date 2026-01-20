# Documentation Generator

Automated documentation generation for code, APIs, and modules.

**Model Tier**: STANDARD (Gemini Flash)

## Usage

```
/doc-gen <file, directory, or module>
```

## Workflow

1. **Analysis**
   - Parse code structure (classes, functions, modules)
   - Extract existing docstrings
   - Identify public APIs
   
2. **Generation** (using STANDARD tier model)
   - Generate/update docstrings
   - Create API reference documentation
   - Generate usage examples
   - Create module-level documentation
   
3. **Output**
   - Inline docstring updates
   - Markdown documentation files
   - API reference tables

## Output Format

### Inline Docstrings (Python)
```python
def function_name(param1: Type, param2: Type) -> ReturnType:
    """Brief description of function.
    
    Detailed description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
        
    Returns:
        Description of return value.
        
    Raises:
        ExceptionType: When this happens.
        
    Example:
        >>> function_name(value1, value2)
        expected_result
    """
```

### Module Documentation
```markdown
# Module Name

Brief description of module purpose.

## Overview

Detailed explanation of what this module does.

## API Reference

### Classes

#### `ClassName`

Description of class.

**Methods:**
- `method_name(params)`: Description

### Functions

#### `function_name(params) -> ReturnType`

Description of function.

## Usage Examples

[Code examples with explanation]
```

## Documentation Types

- [ ] Function/method docstrings
- [ ] Class docstrings
- [ ] Module docstrings
- [ ] API reference (Markdown)
- [ ] Usage examples
- [ ] Type annotations

## Delegation

This skill uses `dewey` (STANDARD tier) for documentation research and generation.

$ARGUMENTS
