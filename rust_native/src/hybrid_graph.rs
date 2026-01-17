use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use crate::git_analysis;
use crate::import_analysis;

#[pyfunction]
#[pyo3(signature = (target_file, root_dir, limit = 10, threshold_score = 0.4))]
pub fn get_hybrid_context(
    target_file: String,
    root_dir: String,
    limit: usize,
    threshold_score: f64
) -> PyResult<Vec<(String, f64, String)>> {
    // 1. Get Temporal Signal (Git)
    // We request more than the limit to allow filtering
    let git_files = git_analysis::get_related_files(target_file.clone(), root_dir.clone(), limit * 3)?;
    
    // Convert git vector to Map for lookup: File -> Count (implied ranking)
    let mut git_map: HashMap<String, usize> = HashMap::new();
    for (i, file) in git_files.iter().enumerate() {
        // Simple ranking proxy: (total - rank)
        git_map.insert(file.clone(), git_files.len() - i);
    }

    // 2. Get Static Signal (Imports)
    // We check imports in the target file (outgoing)
    let full_target_path = Path::new(&root_dir).join(&target_file);
    let static_imports = if full_target_path.exists() {
        import_analysis::get_imports(full_target_path.to_string_lossy().to_string()).unwrap_or_default()
    } else {
        Vec::new()
    };
    
    let mut static_set: HashSet<String> = HashSet::new();
    for imp in static_imports {
        // Resolve import to file path
        // This is tricky without full language server resolution.
        // We attempt heuristic resolution:
        // "from mcp_bridge.tools import x" -> "mcp_bridge/tools/x.py" OR "mcp_bridge/tools/__init__.py"
        
        // Basic heuristic resolution
        let parts: Vec<&str> = imp.split('.').collect();
        let path_slashed = parts.join("/");
        
        // Try exact match in git map (fuzzy)
        // Or check if file exists
        static_set.insert(path_slashed); 
    }
    
    // 3. Scoring
    let mut scored_files: Vec<(String, f64, String)> = Vec::new();
    let mut all_candidates: HashSet<String> = HashSet::new();
    for f in git_map.keys() { all_candidates.insert(f.clone()); }
    // Note: We currently only score files found in Git OR imports that map clearly.
    // Ideally we'd scan all files for reverse imports too, but that's expensive.
    
    for candidate in all_candidates {
        let git_rank = git_map.get(&candidate).copied().unwrap_or(0);
        
        // Check if static import matches candidate
        // Heuristic: does candidate path end with import path?
        // e.g. candidate: "mcp_bridge/tools/find_code.py", import: "mcp_bridge/tools/find_code"
        let is_static = static_set.iter().any(|imp| {
            candidate.contains(imp)
        });
        
        let mut score = 0.0;
        let mut reasons = Vec::new();
        
        if is_static {
            score += 0.7;
            reasons.push("imported");
        }
        
        if git_rank > 0 {
            // Normalize git rank 0.0 - 0.5
            let git_score = 0.5 * (git_rank as f64 / git_files.len() as f64);
            score += git_score;
            reasons.push("git-history");
        }
        
        // Boost if BOTH
        if is_static && git_rank > 0 {
            score += 0.2; // Synergy bonus
        }
        
        if score >= threshold_score {
            scored_files.push((candidate, score, reasons.join("+")));
        }
    }
    
    // Sort by score desc
    scored_files.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    
    Ok(scored_files.into_iter().take(limit).collect())
}
