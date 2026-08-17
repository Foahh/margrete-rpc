use crate::logger::Logger;
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, Serialize)]
pub struct DiscoveryTransport {
    pub r#type: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub endpoint: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub path: String,
}

#[derive(Serialize)]
struct DiscoveryRecord<'a> {
    schema_version: u32,
    instance_id: &'a str,
    pid: u32,
    endpoint: &'a str,
    transports: &'a [DiscoveryTransport],
    started_at_unix: u64,
    plugin_version: &'a str,
    log: &'a str,
}

pub fn create_instance_id() -> String {
    let pid = current_pid();
    let unix = unix_time_seconds();
    let rand = unique_u64();
    format!("{pid}-{unix:x}-{rand:x}")
}

pub fn directory() -> PathBuf {
    local_app_data()
        .unwrap_or_else(std::env::temp_dir)
        .join("MargreteRPC")
        .join("instances")
}

pub fn log_directory() -> PathBuf {
    local_app_data()
        .unwrap_or_else(std::env::temp_dir)
        .join("MargreteRPC")
        .join("logs")
}

pub fn log_path(instance_id: &str) -> PathBuf {
    log_directory().join(format!("{}-{instance_id}.log", crate::meta::DLL_NAME))
}

pub fn record_path(instance_id: &str) -> PathBuf {
    directory().join(format!("{instance_id}.json"))
}

pub fn publish(
    instance_id: &str,
    transports: &[DiscoveryTransport],
    log_path: &Path,
    plugin_version: &str,
    logger: &Logger,
) {
    let dir = directory();
    if let Err(err) = fs::create_dir_all(&dir) {
        logger.error(format!("discovery publish failed: {err}"));
        return;
    }
    let path = record_path(instance_id);
    let endpoint = transports
        .first()
        .map(|t| t.endpoint.as_str())
        .unwrap_or("");
    let log = path_utf8(log_path);
    let record = DiscoveryRecord {
        schema_version: 2,
        instance_id,
        pid: current_pid(),
        endpoint,
        transports,
        started_at_unix: unix_time_seconds(),
        plugin_version,
        log: &log,
    };
    match serde_json::to_string_pretty(&record) {
        Ok(mut json) => {
            json.push('\n');
            if fs::write(&path, json).is_err() {
                logger.error(format!(
                    "discovery publish failed path={}",
                    path_utf8(&path)
                ));
                return;
            }
            logger.info(format!(
                "discovery published path={} endpoint={endpoint}",
                path_utf8(&path)
            ));
        }
        Err(err) => logger.error(format!("discovery publish failed: {err}")),
    }
}

pub fn remove(instance_id: &str, logger: &Logger) {
    let path = record_path(instance_id);
    match fs::remove_file(&path) {
        Ok(()) => logger.info(format!("discovery removed path={}", path_utf8(&path))),
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
            logger.info(format!("discovery removed path={}", path_utf8(&path)));
        }
        Err(err) => logger.error(format!(
            "discovery remove failed path={} error={err}",
            path_utf8(&path)
        )),
    }
}

pub fn local_app_data() -> Option<PathBuf> {
    std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
}

pub fn path_utf8(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn current_pid() -> u32 {
    std::process::id()
}

fn unix_time_seconds() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn unique_u64() -> u64 {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    unix_time_seconds().hash(&mut hasher);
    current_pid().hash(&mut hasher);
    std::thread::current().id().hash(&mut hasher);
    let mut buf = [0u8; 8];
    if fill_random(&mut buf) {
        u64::from_le_bytes(buf) ^ hasher.finish()
    } else {
        hasher.finish()
    }
}

fn fill_random(buf: &mut [u8]) -> bool {
    #[cfg(windows)]
    {
        use std::fs::File;
        use std::io::Read;
        if let Ok(mut f) = File::open("\\\\.\\RNG") {
            return f.read_exact(buf).is_ok();
        }
    }
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    let value = (unix_time_seconds().wrapping_mul(0x9E37_79B9_7F4A_7C15)) ^ u64::from(nanos);
    buf.copy_from_slice(&value.to_le_bytes());
    true
}
