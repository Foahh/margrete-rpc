use margrete_rpc::config::{
    is_loopback_address, load_server_config, transport_mode_name, ServerTransportMode,
};
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
    assert_eq!(config.transport, ServerTransportMode::Both);
    assert_eq!(config.host, "127.0.0.1");
    assert_eq!(config.port, 0);
    assert!(config.auto_port);
    assert_eq!(config.pipe_name, "auto");
}

#[test]
fn config_reads_server_section() {
    let path = temp_ini("margrete_rpc-test.ini");
    fs::write(
        &path,
        "[server]\ntransport = pipe\nhost = 127.0.0.1\nport = 49000\npipe_name = margrete_rpc-test\n",
    )
    .unwrap();
    let config = load_server_config(&path).unwrap();
    assert_eq!(config.source_path, path);
    assert!(config.loaded_from_file);
    assert_eq!(config.transport, ServerTransportMode::Pipe);
    assert_eq!(config.host, "127.0.0.1");
    assert_eq!(config.port, 49000);
    assert!(!config.auto_port);
    assert_eq!(config.pipe_name, "margrete_rpc-test");
}

#[test]
fn config_rejects_invalid_transport() {
    let path = temp_ini("margrete_rpc-bad-transport.ini");
    fs::write(&path, "[server]\ntransport = udp\n").unwrap();
    let err = load_server_config(&path).unwrap_err().to_string();
    assert!(err.contains("server transport must be tcp, pipe, or both"));
}

#[test]
fn config_rejects_invalid_pipe_name() {
    let path = temp_ini("margrete_rpc-bad-pipe.ini");
    fs::write(&path, "[server]\npipe_name = bad/name\n").unwrap();
    let err = load_server_config(&path).unwrap_err().to_string();
    assert!(err.contains("server pipe_name must be auto"));
}

#[test]
fn config_supports_automatic_port() {
    let path = temp_ini("margrete_rpc-auto.ini");
    fs::write(&path, "[server]\nport = auto\n").unwrap();
    let config = load_server_config(&path).unwrap();
    assert_eq!(config.port, 0);
    assert!(config.auto_port);
}

#[test]
fn config_accepts_explicit_ipv4_host() {
    let path = temp_ini("margrete_rpc-host.ini");
    fs::write(&path, "[server]\nhost = 0.0.0.0\n").unwrap();
    let config = load_server_config(&path).unwrap();
    assert_eq!(config.host, "0.0.0.0");
}

#[test]
fn config_rejects_invalid_host() {
    let path = temp_ini("margrete_rpc-bad-host.ini");
    fs::write(&path, "[server]\nhost = localhost\n").unwrap();
    let err = load_server_config(&path).unwrap_err().to_string();
    assert!(err.contains("server host must be an IPv4 address"));
}

#[test]
fn loopback_detection() {
    assert!(is_loopback_address("127.0.0.1"));
    assert!(is_loopback_address("127.5.6.7"));
    assert!(!is_loopback_address("0.0.0.0"));
    assert!(!is_loopback_address("192.168.1.10"));
}

#[test]
fn config_ignores_utf8_bom() {
    let path = temp_ini("margrete_rpc-bom.ini");
    let mut data = Vec::from([0xEF, 0xBB, 0xBF]);
    data.extend_from_slice(b"[server]\nport = 49000\n");
    fs::write(&path, data).unwrap();
    let config = load_server_config(&path).unwrap();
    assert!(config.loaded_from_file);
    assert_eq!(config.port, 49000);
    assert!(!config.auto_port);
}

#[test]
fn transport_mode_names() {
    assert_eq!(transport_mode_name(ServerTransportMode::Tcp), "tcp");
    assert_eq!(transport_mode_name(ServerTransportMode::Pipe), "pipe");
    assert_eq!(transport_mode_name(ServerTransportMode::Both), "both");
}
