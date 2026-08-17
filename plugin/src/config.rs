use crate::error::{PluginError, Result};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ServerTransportMode {
    Tcp,
    Pipe,
    Both,
}

impl ServerTransportMode {
    pub fn name(self) -> &'static str {
        match self {
            Self::Tcp => "tcp",
            Self::Pipe => "pipe",
            Self::Both => "both",
        }
    }

    pub fn includes_tcp(self) -> bool {
        matches!(self, Self::Tcp | Self::Both)
    }

    pub fn includes_pipe(self) -> bool {
        matches!(self, Self::Pipe | Self::Both)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ServerConfig {
    pub source_path: PathBuf,
    pub loaded_from_file: bool,
    pub transport: ServerTransportMode,
    pub host: String,
    pub port: u16,
    pub auto_port: bool,
    pub pipe_name: String,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            source_path: PathBuf::new(),
            loaded_from_file: false,
            transport: ServerTransportMode::Both,
            host: "127.0.0.1".into(),
            port: 0,
            auto_port: true,
            pipe_name: "auto".into(),
        }
    }
}

pub fn load_server_config(ini_path: impl AsRef<Path>) -> Result<ServerConfig> {
    let ini_path = ini_path.as_ref();
    let mut config = ServerConfig {
        source_path: ini_path.to_path_buf(),
        ..ServerConfig::default()
    };
    let Ok(bytes) = fs::read(ini_path) else {
        return Ok(config);
    };
    config.loaded_from_file = true;
    let text = String::from_utf8_lossy(&bytes);
    let mut section = String::new();
    for (index, raw_line) in text.lines().enumerate() {
        let mut line = raw_line;
        if index == 0 {
            line = line.strip_prefix('\u{feff}').unwrap_or(line);
        }
        let line = trim_ascii(line);
        if line.is_empty() || line.starts_with(';') || line.starts_with('#') {
            continue;
        }
        if let Some(inner) = line.strip_prefix('[').and_then(|s| s.strip_suffix(']')) {
            section = inner.to_string();
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let key = trim_ascii(key);
        let value = trim_ascii(value);
        if section != "server" {
            continue;
        }
        match key {
            "host" => config.host = value.to_string(),
            "transport" => config.transport = parse_transport_mode(value)?,
            "port" => {
                if value == "auto" {
                    config.port = 0;
                    config.auto_port = true;
                } else {
                    let port: i32 = value.parse().map_err(|_| {
                        PluginError::internal("server port must be auto or between 0 and 65535")
                    })?;
                    if !(0..=65535).contains(&port) {
                        return Err(PluginError::internal(
                            "server port must be auto or between 0 and 65535",
                        ));
                    }
                    config.port = port as u16;
                    config.auto_port = port == 0;
                }
            }
            "pipe_name" => config.pipe_name = value.to_string(),
            _ => {}
        }
    }

    if !is_valid_ipv4_address(&config.host) {
        return Err(PluginError::internal("server host must be an IPv4 address"));
    }
    if config.pipe_name != "auto" && !is_valid_pipe_name(&config.pipe_name) {
        return Err(PluginError::internal(
            "server pipe_name must be auto or a simple pipe name",
        ));
    }
    Ok(config)
}

pub fn is_loopback_address(host: &str) -> bool {
    host.starts_with("127.")
}

pub fn transport_mode_name(mode: ServerTransportMode) -> &'static str {
    mode.name()
}

fn parse_transport_mode(value: &str) -> Result<ServerTransportMode> {
    match value {
        "tcp" => Ok(ServerTransportMode::Tcp),
        "pipe" | "npipe" => Ok(ServerTransportMode::Pipe),
        "both" => Ok(ServerTransportMode::Both),
        _ => Err(PluginError::internal(
            "server transport must be tcp, pipe, or both",
        )),
    }
}

fn is_valid_ipv4_address(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    let mut octet_count = 0;
    let mut start = 0;
    loop {
        let rest = &value[start..];
        let (octet, next) = match rest.find('.') {
            Some(dot) => (&rest[..dot], start + dot + 1),
            None => (rest, value.len()),
        };
        if octet.is_empty() || octet.len() > 3 {
            return false;
        }
        let mut number = 0i32;
        for ch in octet.chars() {
            if !ch.is_ascii_digit() {
                return false;
            }
            number = number * 10 + (ch as i32 - '0' as i32);
        }
        if number > 255 {
            return false;
        }
        octet_count += 1;
        if rest.find('.').is_none() {
            break;
        }
        start = next;
        if start > value.len() {
            break;
        }
    }
    octet_count == 4
}

fn is_valid_pipe_name(value: &str) -> bool {
    !value.is_empty()
        && value
            .find(['\\', '/', ':', '*', '?', '"', '<', '>', '|'])
            .is_none()
}

fn trim_ascii(value: &str) -> &str {
    value.trim_matches(|c: char| c.is_ascii_whitespace())
}
