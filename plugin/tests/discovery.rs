use margrete_rpc::discovery::{self, DiscoveryTransport};
use margrete_rpc::logger::Logger;
use std::sync::Mutex;

static ENV_LOCK: Mutex<()> = Mutex::new(());

struct LocalAppDataGuard {
    previous: Option<std::ffi::OsString>,
}

impl LocalAppDataGuard {
    fn set(value: &std::path::Path) -> Self {
        let previous = std::env::var_os("LOCALAPPDATA");
        std::env::set_var("LOCALAPPDATA", value);
        Self { previous }
    }
}

impl Drop for LocalAppDataGuard {
    fn drop(&mut self) {
        match &self.previous {
            Some(value) => std::env::set_var("LOCALAPPDATA", value),
            None => std::env::remove_var("LOCALAPPDATA"),
        }
    }
}

#[test]
fn discovery_publishes_configured_host() {
    let _lock = ENV_LOCK.lock().unwrap();
    let base = std::env::temp_dir().join("margrete_rpc-discovery-test");
    let _ = std::fs::remove_dir_all(&base);
    std::fs::create_dir_all(&base).unwrap();
    let _guard = LocalAppDataGuard::set(&base);
    let instance_id = "test-instance";
    let log_path = base.join("test.log");
    let logger = Logger::new(&log_path);
    discovery::publish(
        instance_id,
        &[
            DiscoveryTransport {
                r#type: "tcp".into(),
                endpoint: "192.168.1.23:49000".into(),
                path: String::new(),
            },
            DiscoveryTransport {
                r#type: "npipe".into(),
                endpoint: String::new(),
                path: r"\\.\pipe\margrete_rpc-test".into(),
            },
        ],
        &log_path,
        "test-version",
        &logger,
    );
    let record_path = base
        .join("MargreteRPC")
        .join("instances")
        .join("test-instance.json");
    let content = std::fs::read_to_string(&record_path).unwrap();
    assert!(content.contains("\"endpoint\": \"192.168.1.23:49000\""));
    assert!(content.contains("\"schema_version\": 2"));
    assert!(content.contains("\"type\": \"tcp\""));
    assert!(content.contains("\"type\": \"npipe\""));
    assert!(content.contains("\"path\": \"\\\\\\\\.\\\\pipe\\\\margrete_rpc-test\""));
    let _ = std::fs::remove_dir_all(&base);
}

#[test]
fn discovery_publishes_utf8_log_path() {
    let _lock = ENV_LOCK.lock().unwrap();
    let base = std::env::temp_dir().join("margrete_rpc-discovery-utf8-test");
    let _ = std::fs::remove_dir_all(&base);
    std::fs::create_dir_all(&base).unwrap();
    let _guard = LocalAppDataGuard::set(&base);
    let instance_id = "utf8-instance";
    let log_path = base.join("テスト.log");
    let logger = Logger::new(&log_path);
    discovery::publish(
        instance_id,
        &[DiscoveryTransport {
            r#type: "tcp".into(),
            endpoint: "127.0.0.1:49000".into(),
            path: String::new(),
        }],
        &log_path,
        "test-version",
        &logger,
    );
    let record_path = base
        .join("MargreteRPC")
        .join("instances")
        .join("utf8-instance.json");
    let content = std::fs::read(&record_path).unwrap();
    let as_text = String::from_utf8_lossy(&content);
    assert!(as_text.contains("テスト.log"));
    let _ = std::fs::remove_dir_all(&base);
}

#[test]
fn discovery_directory_keeps_unicode_local_app_data() {
    let _lock = ENV_LOCK.lock().unwrap();
    let base = std::env::temp_dir().join("テスト-rpc");
    let _ = std::fs::remove_dir_all(&base);
    std::fs::create_dir_all(&base).unwrap();
    let _guard = LocalAppDataGuard::set(&base);
    assert_eq!(
        discovery::directory(),
        base.join("MargreteRPC").join("instances")
    );
    assert_eq!(
        discovery::log_directory(),
        base.join("MargreteRPC").join("logs")
    );
    let _ = std::fs::remove_dir_all(&base);
}
