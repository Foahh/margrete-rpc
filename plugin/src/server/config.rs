use crate::error::{PluginError, Result};
use configparser::ini::{Ini, IniDefault};
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
    let text = text.strip_prefix('\u{feff}').unwrap_or(&text);
    let mut defaults = IniDefault::default();
    defaults.delimiters = vec!['='];
    defaults.case_sensitive = true;
    defaults.enable_inline_comments = false;
    let mut ini = Ini::new_from_defaults(defaults);
    ini.read(text.to_owned())
        .map_err(|err| PluginError::internal(format!("failed to parse server config: {err}")))?;
    if let Some(value) = ini.get("server", "logging") {
        config.logging = parse_logging(&value)?;
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
