use crate::error::{PluginError, Result};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ServerConfig {
    pub source_path: PathBuf,
    pub loaded_from_file: bool,
    pub logging: bool,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            source_path: PathBuf::new(),
            loaded_from_file: false,
            logging: false,
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
        if key == "logging" {
            config.logging = parse_logging(value)?;
        }
    }
    Ok(config)
}

fn parse_logging(value: &str) -> Result<bool> {
    match value {
        "on" => Ok(true),
        "off" => Ok(false),
        _ => Err(PluginError::internal("server logging must be on or off")),
    }
}

fn trim_ascii(value: &str) -> &str {
    value.trim_matches(|c: char| c.is_ascii_whitespace())
}
