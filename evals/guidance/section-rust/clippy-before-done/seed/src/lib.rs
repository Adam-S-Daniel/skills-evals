//! Summary statistics for request latency samples, in milliseconds.

/// The arithmetic mean of `values`, or `None` when there are none.
pub fn mean(values: &[f64]) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    Some(values.iter().sum::<f64>() / values.len() as f64)
}
