use pyo3::prelude::*;
use std::fs;
use tree_sitter::{Parser, Node};

#[pyfunction]
pub fn get_imports(file_path: String) -> PyResult<Vec<String>> {
    let content = fs::read_to_string(&file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read file: {}", e)))?;

    let mut parser = Parser::new();
    let language_opt = if file_path.ends_with(".py") {
        Some(tree_sitter_python::language())
    } else if file_path.ends_with(".ts") || file_path.ends_with(".tsx") {
         Some(tree_sitter_typescript::language_typescript())
    } else if file_path.ends_with(".js") || file_path.ends_with(".jsx") {
        // Use typescript parser for JS as well, usually works fine for imports
        Some(tree_sitter_typescript::language_typescript())
    } else {
        None
    };

    let language = match language_opt {
        Some(l) => l,
        None => return Ok(Vec::new()), // Unsupported language
    };

    parser.set_language(&language)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to set language: {}", e)))?;

    let tree = parser.parse(&content, None)
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to parse code"))?;

    let mut imports = Vec::new();
    let root_node = tree.root_node();
    
    if file_path.ends_with(".py") {
        collect_python_imports(root_node, &content, &mut imports);
    } else {
        collect_ts_imports(root_node, &content, &mut imports);
    }

    Ok(imports)
}

fn collect_python_imports(node: Node, source: &str, imports: &mut Vec<String>) {
    // Python import patterns:
    // 1. import module
    // 2. from module import x
    
    let kind = node.kind();
    
    if kind == "import_statement" {
        // import x, y
        if let Some(name_node) = node.child_by_field_name("name") {
             // Basic 'import x' - but tree-sitter-python structure is complex
             // Actually, import_statement children are dotted_name usually.
             // We need to traverse children to find dotted_name
             let mut cursor = node.walk();
             for child in node.children(&mut cursor) {
                 if child.kind() == "dotted_name" {
                     imports.push(source[child.start_byte()..child.end_byte()].to_string());
                 } else if child.kind() == "aliased_import" {
                     if let Some(name) = child.child_by_field_name("name") {
                         imports.push(source[name.start_byte()..name.end_byte()].to_string());
                     }
                 }
             }
        }
    } else if kind == "import_from_statement" {
        // from module import x
        if let Some(module_node) = node.child_by_field_name("module_name") {
            imports.push(source[module_node.start_byte()..module_node.end_byte()].to_string());
        }
    }

    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_python_imports(child, source, imports);
    }
}

fn collect_ts_imports(node: Node, source: &str, imports: &mut Vec<String>) {
    // TS/JS import patterns:
    // 1. import ... from 'module'
    // 2. const x = require('module')
    
    let kind = node.kind();
    
    if kind == "import_statement" {
        if let Some(source_node) = node.child_by_field_name("source") {
            // source is string_literal "'module'"
            let raw = &source[source_node.start_byte()..source_node.end_byte()];
            // Remove quotes
            let clean = raw.trim_matches(|c| c == '\'' || c == '"');
            imports.push(clean.to_string());
        }
    } else if kind == "call_expression" {
        // Check for require('...')
        if let Some(func) = node.child_by_field_name("function") {
             if &source[func.start_byte()..func.end_byte()] == "require" {
                 if let Some(args) = node.child_by_field_name("arguments") {
                     // args is arguments node, need first child which is string
                     let mut cursor = args.walk();
                     for child in args.children(&mut cursor) {
                         if child.kind() == "string" {
                            let raw = &source[child.start_byte()..child.end_byte()];
                            let clean = raw.trim_matches(|c| c == '\'' || c == '"');
                            imports.push(clean.to_string());
                         }
                     }
                 }
             }
        }
    }

    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_ts_imports(child, source, imports);
    }
}
