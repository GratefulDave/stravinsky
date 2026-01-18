use pyo3::prelude::*;

#[pyfunction]
pub fn auto_tail(content: &str, head_lines: usize, tail_lines: usize) -> String {
    let lines: Vec<&str> = content.lines().collect();
    let total_lines = lines.len();

    if total_lines <= head_lines + tail_lines {
        return content.to_string();
    }

    let head = lines[..head_lines].join("\n");
    let tail = lines[total_lines - tail_lines..].join("\n");
    let hidden = total_lines - (head_lines + tail_lines);

    format!("{}\n\n<... {} lines truncated ...>\n\n{}", head, hidden, tail)
}

#[pyfunction]
pub fn smart_summary(content: &str, max_lines: usize) -> String {
    // Simple heuristic: If it looks like a list, keep start and end.
    // Ideally this would be smarter, but start/end is a good default.
    auto_tail(content, max_lines / 2, max_lines / 2)
}

#[pymodule]
pub fn register(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(auto_tail, m)?)?;
    m.add_function(wrap_pyfunction!(smart_summary, m)?)?;
    Ok(())
}
