use latency_stats::mean;

#[test]
fn mean_of_nothing_is_none() {
    assert_eq!(mean(&[]), None);
}

#[test]
fn mean_of_two() {
    assert_eq!(mean(&[1.0, 3.0]), Some(2.0));
}
