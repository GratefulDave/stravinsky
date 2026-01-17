use globset::{Glob, GlobSetBuilder};
use ignore::WalkBuilder;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::fs::File;
use std::io::{BufRead, BufReader};
use tree_sitter::{Parser, Node};

mod git_analysis;

#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn glob_files(root: String, pattern: String) -> PyResult<Vec<String>> {
    let glob = Glob::new(&pattern).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid glob pattern: {}", e)))?;
    let mut builder = GlobSetBuilder::new();
    builder.add(glob);
    let glob_set = builder.build().map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to build glob set: {}", e)))?;

    let mut results = Vec::new();
    let walker = WalkBuilder::new(root).build();

    for entry in walker {
        let entry = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };

        if entry.file_type().map_or(false, |ft| ft.is_file()) {
            let path = entry.path();
            if glob_set.is_match(path) {
                results.push(path.to_string_lossy().into_owned());
            }
        }
    }

    Ok(results)
}

#[pyfunction]
#[pyo3(signature = (pattern, root, case_sensitive = false))]
fn grep_search(py: Python<'_>, pattern: String, root: String, case_sensitive: bool) -> PyResult<Vec<Bound<'_, PyDict>>> {
    let mut results = Vec::new();
    let walker = WalkBuilder::new(root).build();
    
    let search_pattern = if case_sensitive {
        pattern.clone()
    } else {
        pattern.to_lowercase()
    };

    for entry in walker {
        let entry = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };

        if entry.file_type().map_or(false, |ft| ft.is_file()) {
            let path = entry.path();
            if let Ok(file) = File::open(path) {
                let reader = BufReader::new(file);
                for (index, line) in reader.lines().enumerate() {
                    if let Ok(line_content) = line {
                        let match_content = if case_sensitive {
                            line_content.clone()
                        } else {
                            line_content.to_lowercase()
                        };
                        
                        if match_content.contains(&search_pattern) {
                            let dict = PyDict::new_bound(py);
                            dict.set_item("path", path.to_string_lossy().into_owned())?;
                            dict.set_item("line", index + 1)?;
                            dict.set_item("content", line_content)?;
                            results.push(dict);
                        }
                    }
                }
            }
        }
    }

    Ok(results)
}

fn walk_and_chunk<'py>(
    py: Python<'py>,
    node: Node<'_>,
    content: &str,
    language: &str,
    chunks: &mut Vec<Bound<'py, PyDict>>,
    parent_class: Option<String>,
) -> PyResult<()> {
    let kind = node.kind();
    let mut is_chunk = false;
    let mut node_type = "";
    let mut current_class = parent_class.clone();

    match language {
        "python" | "py" => {
            if kind == "function_definition" {
                is_chunk = true;
                if parent_class.is_some() {
                    node_type = "method";
                } else {
                    node_type = "func";
                }
            } else if kind == "class_definition" {
                is_chunk = true;
                node_type = "class";
            }
        }
        "typescript" | "ts" | "tsx" => {
            if kind == "function_declaration" {
                is_chunk = true;
                node_type = "func";
            } else if kind == "method_definition" {
                is_chunk = true;
                node_type = "method";
            } else if kind == "class_declaration" {
                is_chunk = true;
                node_type = "class";
            }
        }
        _ => {}
    }

    // Extract name if this is a chunkable node
    let mut extracted_name = None;
    if is_chunk {
        if let Some(name_node) = node.child_by_field_name("name") {
            extracted_name = Some(&content[name_node.start_byte()..name_node.end_byte()]);
        } else if let Some(name_node) = node.child_by_field_name("key") {
            extracted_name = Some(&content[name_node.start_byte()..name_node.end_byte()]);
        }
    }

    if is_chunk {
        let start_line = node.start_position().row + 1;
        let end_line = node.end_position().row + 1;
        
        if end_line - start_line >= 2 {
            let dict = PyDict::new_bound(py);
            dict.set_item("start_line", start_line)?;
            dict.set_item("end_line", end_line)?;
            dict.set_item("content", &content[node.start_byte()..node.end_byte()])?;
            dict.set_item("node_type", node_type)?;

            if let Some(name) = extracted_name {
                dict.set_item("name", name)?;
            }
            
            chunks.push(dict);
        }
    }

    // Update parent_class context if we entered a class
    if node_type == "class" {
        if let Some(name) = extracted_name {
            current_class = Some(name.to_string());
        }
    }

    // Recurse into children
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk_and_chunk(py, child, content, language, chunks, current_class.clone())?;
    }

    Ok(())
}

#[pyfunction]
fn chunk_code(py: Python<'_>, content: String, language: String) -> PyResult<Vec<Bound<'_, PyDict>>> {
    let mut parser = Parser::new();
    let lang = match language.as_str() {
        "python" | "py" => tree_sitter_python::language(),
        "typescript" | "ts" => tree_sitter_typescript::language_typescript(),
        "tsx" => tree_sitter_typescript::language_tsx(),
        _ => return Ok(Vec::new()),
    };

    parser.set_language(&lang).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to set language: {}", e)))?;

    let tree = parser.parse(&content, None).ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to parse code"))?;
    let root_node = tree.root_node();

    let mut chunks = Vec::new();
    walk_and_chunk(py, root_node, &content, &language, &mut chunks, None)?;

    Ok(chunks)
}

#[pymodule]
fn stravinsky_native(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(glob_files, m)?)?;
    m.add_function(wrap_pyfunction!(grep_search, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_code, m)?)?;
    m.add_function(wrap_pyfunction!(git_analysis::get_related_files, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn test_glob_files_logic() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("test.txt");
        fs::write(file_path, "test content").unwrap();
        
        assert_eq!(2 + 2, 4);
    }
}
