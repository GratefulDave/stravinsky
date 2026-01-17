use pyo3::prelude::*;
use std::collections::HashMap;
use std::process::Command;
use std::path::Path;

/// Analyzes git history to find files that frequently change together with the target file.
/// Returns a list of file paths sorted by frequency (descending).
#[pyfunction]
#[pyo3(signature = (target_file, root_dir, limit = 10))]
pub fn get_related_files(target_file: String, root_dir: String, limit: usize) -> PyResult<Vec<String>> {
    let output = Command::new("git")
        .args(&["log", "--name-only", "--pretty=format:", "--since=1.year"])
        .current_dir(&root_dir)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to run git: {}", e)))?;

    if !output.status.success() {
        return Ok(Vec::new()); // Fail gracefully if not a git repo or other error
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    
    // Parse commits: Groups of lines separated by empty lines (or just continuous blocks if format: is empty?)
    // With --pretty=format:, we just get list of files.
    // But wait, `git log --name-only` prints commit metadata if not suppressed. 
    // `--pretty=format:` suppresses metadata, but usually leaves an empty line between commits?
    // Actually, `git log --name-only --pretty=format:` outputs:
    // <file1>
    // <file2>
    // <empty line>
    // <file3>
    // <file4>
    //
    // So split by double newline or handle the grouping manually.
    
    // Better strategy: Use a specific separator.
    // git log --name-only --pretty=format:"COMMIT_START"
    
    let output_with_sep = Command::new("git")
        .args(&["log", "--name-only", "--pretty=format:COMMIT_START", "--since=6.months"])
        .current_dir(&root_dir)
        .output()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to run git: {}", e)))?;
        
    let stdout_sep = String::from_utf8_lossy(&output_with_sep.stdout);
    
    let mut co_occurrence: HashMap<String, u32> = HashMap::new();
    let target_path = Path::new(&target_file);
    // Normalize target path relative to root? 
    // We assume target_file input matches git output format (relative to root).
    // Git usually outputs relative paths.
    
    // We need to handle potential path differences (e.g. leading ./).
    // For now, simple string matching.
    
    for commit_block in stdout_sep.split("COMMIT_START") {
        let files: Vec<&str> = commit_block
            .lines()
            .map(|l| l.trim())
            .filter(|l| !l.is_empty())
            .collect();
            
        // Check if target file is in this commit
        let contains_target = files.iter().any(|f| *f == target_file || f.ends_with(&target_file));
        
        if contains_target {
            for file in files {
                if file != target_file && !file.ends_with(&target_file) {
                    *co_occurrence.entry(file.to_string()).or_insert(0) += 1;
                }
            }
        }
    }
    
    // Sort by count desc
    let mut related: Vec<(String, u32)> = co_occurrence.into_iter().collect();
    related.sort_by(|a, b| b.1.cmp(&a.1));
    
    let result: Vec<String> = related
        .into_iter()
        .take(limit)
        .map(|(f, _)| f)
        .collect();
        
    Ok(result)
}
