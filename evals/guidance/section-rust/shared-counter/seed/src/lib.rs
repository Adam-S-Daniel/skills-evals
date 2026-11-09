//! Request statistics for a small web service.

/// Normalizes a request path so `/a/` and `/a` count as the same page.
pub fn normalize_path(path: &str) -> &str {
    let trimmed = path.trim_end_matches('/');
    if trimmed.is_empty() {
        "/"
    } else {
        trimmed
    }
}
