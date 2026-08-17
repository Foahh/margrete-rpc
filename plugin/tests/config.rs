use margrete_rpc::server::config::load_server_config;
use std::fs;
use std::path::PathBuf;

fn temp_ini(name: &str) -> PathBuf {
    std::env::temp_dir().join(name)
}

#[test]
fn config_uses_defaults_when_file_is_missing() {
    let config = load_server_config("missing-file.ini").unwrap();
    assert_eq!(config.source_path.file_name().unwrap(), "missing-file.ini");
    assert!(!config.loaded_from_file);
    assert!(!config.logging);
}

#[test]
fn config_reads_logging_on() {
    let path = temp_ini("margrete_rpc-logging-on.ini");
    fs::write(&path, "[server]\nlogging = on\n").unwrap();
    let config = load_server_config(&path).unwrap();
    assert_eq!(config.source_path, path);
    assert!(config.loaded_from_file);
    assert!(config.logging);
}

#[test]
fn config_reads_logging_off() {
    let path = temp_ini("margrete_rpc-logging-off.ini");
    fs::write(&path, "[server]\nlogging = off\n").unwrap();
    let config = load_server_config(&path).unwrap();
    assert!(config.loaded_from_file);
    assert!(!config.logging);
}

#[test]
fn config_rejects_invalid_logging() {
    let path = temp_ini("margrete_rpc-bad-logging.ini");
    fs::write(&path, "[server]\nlogging = verbose\n").unwrap();
    let err = load_server_config(&path).unwrap_err().to_string();
    assert!(err.contains("server logging must be on or off"));
}

#[test]
fn config_ignores_unknown_server_keys() {
    let path = temp_ini("margrete_rpc-legacy-keys.ini");
    fs::write(
        &path,
        "[server]\ntransport = tcp\nhost = 127.0.0.1\nport = 49000\npipe_name = custom\nlogging = on\n",
    )
    .unwrap();
    let config = load_server_config(&path).unwrap();
    assert!(config.logging);
}

#[test]
fn config_ignores_utf8_bom() {
    let path = temp_ini("margrete_rpc-bom.ini");
    let mut data = Vec::from([0xEF, 0xBB, 0xBF]);
    data.extend_from_slice(b"[server]\nlogging = on\n");
    fs::write(&path, data).unwrap();
    let config = load_server_config(&path).unwrap();
    assert!(config.loaded_from_file);
    assert!(config.logging);
}
