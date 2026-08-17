use margrete_rpc::server::logger;
use std::fs;
use std::path::Path;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

static LOGGER_TEST: Mutex<()> = Mutex::new(());

#[test]
fn logger_appends_disables_reenables_and_switches_paths() {
    let _guard = LOGGER_TEST.lock().expect("logger test lock");
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "margrete-rpc-logger-test-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir_all(&root).expect("create test log directory");
    let first = root.join("first.log");
    let second = root.join("second.log");
    fs::write(&first, "sentinel\n").expect("seed first log");

    logger::configure(Some(&first), true);
    assert_eq!(logger::path(), first);
    log::info!("logger-test-enabled-{nonce}");
    log::logger().flush();

    let first_contents = read(&first);
    assert!(first_contents.starts_with("sentinel\n"));
    assert_log_line(&first_contents, &format!("logger-test-enabled-{nonce}"));

    logger::configure(Some(&first), false);
    assert!(logger::path().as_os_str().is_empty());
    log::info!("logger-test-disabled-{nonce}");
    log::logger().flush();
    assert!(!read(&first).contains(&format!("logger-test-disabled-{nonce}")));

    logger::configure(Some(&first), true);
    log::info!("logger-test-reenabled-{nonce}");
    log::logger().flush();
    assert_log_line(&read(&first), &format!("logger-test-reenabled-{nonce}"));

    logger::configure(Some(&second), true);
    assert_eq!(logger::path(), second);
    log::info!("logger-test-switched-{nonce}");
    log::logger().flush();
    assert!(!read(&first).contains(&format!("logger-test-switched-{nonce}")));
    assert_log_line(&read(&second), &format!("logger-test-switched-{nonce}"));

    logger::configure(Some(&second), false);
    assert!(logger::path().as_os_str().is_empty());
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).expect("read test log")
}

fn assert_log_line(contents: &str, message: &str) {
    let line = contents
        .lines()
        .find(|line| line.ends_with(message))
        .expect("formatted log line");
    assert_eq!(line.len(), 27 + message.len());

    let bytes = line.as_bytes();
    assert_eq!(&bytes[19..27], b" [INFO] ");
    for (index, byte) in bytes[..19].iter().enumerate() {
        match index {
            4 | 7 => assert_eq!(*byte, b'-'),
            10 => assert_eq!(*byte, b' '),
            13 | 16 => assert_eq!(*byte, b':'),
            _ => assert!(byte.is_ascii_digit()),
        }
    }
}
