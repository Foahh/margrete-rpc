use margrete_rpc::server::instance::{self, allocate, parse_code, pipe_name};

#[test]
fn parse_code_accepts_zero_padded_names() {
    assert_eq!(parse_code("margrete-0421"), Some("0421"));
    assert_eq!(parse_code("margrete-0000"), Some("0000"));
    assert_eq!(parse_code("margrete-9999"), Some("9999"));
}

#[test]
fn parse_code_rejects_other_names() {
    assert_eq!(parse_code("margrete-421"), None);
    assert_eq!(parse_code("margrete-04210"), None);
    assert_eq!(parse_code("margrete_rpc-0421"), None);
    assert_eq!(parse_code("margrete-abcd"), None);
    assert_eq!(parse_code("other"), None);
}

#[test]
fn pipe_name_is_prefixed_and_zero_padded() {
    assert_eq!(pipe_name("0421"), "margrete-0421");
}

#[test]
fn allocate_returns_unique_four_digit_codes() {
    let first = allocate().expect("first instance");
    let second = allocate().expect("second instance");
    assert_ne!(first.code, second.code);
    assert_eq!(first.code.len(), 4);
    assert_eq!(second.code.len(), 4);
    assert!(first.code.chars().all(|c| c.is_ascii_digit()));
    assert!(second.code.chars().all(|c| c.is_ascii_digit()));
    assert_eq!(first.pipe_name(), instance::pipe_name(&first.code));
    assert_eq!(second.pipe_name(), instance::pipe_name(&second.code));
}
