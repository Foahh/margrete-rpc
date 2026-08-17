mod pipe;
mod tcp;

use crate::abi::Context;
use crate::config::ServerConfig;
use crate::discovery::{self, DiscoveryTransport};
use crate::logger::Logger;
use crate::meta;
use crate::router::{RequestRouter, RouterStatusSnapshot};
use pipe::NamedPipeServer;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;
use tcp::SocketServer;

#[derive(Clone, Debug)]
pub struct ServerControllerStatus {
    pub running: bool,
    pub discovery_published: bool,
    pub loaded_config: ServerConfig,
    pub active_config: ServerConfig,
    pub has_active_config: bool,
    pub instance_id: String,
    pub log_path: std::path::PathBuf,
    pub actual_port: u16,
    pub actual_pipe_path: String,
}

struct Shared {
    actual_port: AtomicU16,
    actual_pipe_path: Mutex<String>,
    instance_id: String,
    log_path: std::path::PathBuf,
    logger: Arc<Logger>,
    discovery_published: AtomicBool,
    active_host: Mutex<String>,
}

impl Shared {
    fn publish(&self) {
        let mut transports = Vec::new();
        let port = self.actual_port.load(Ordering::SeqCst);
        if port != 0 {
            let host = self.active_host.lock().expect("host").clone();
            transports.push(DiscoveryTransport {
                r#type: "tcp".into(),
                endpoint: format!("{host}:{port}"),
                path: String::new(),
            });
        }
        let pipe = self.actual_pipe_path.lock().expect("pipe").clone();
        if !pipe.is_empty() {
            transports.push(DiscoveryTransport {
                r#type: "npipe".into(),
                endpoint: String::new(),
                path: pipe,
            });
        }
        if transports.is_empty() {
            return;
        }
        discovery::publish(
            &self.instance_id,
            &transports,
            &self.log_path,
            meta::PRODUCT_VERSION,
            &self.logger,
        );
        self.discovery_published.store(true, Ordering::SeqCst);
    }
}

pub struct ServerController {
    config: Mutex<ServerConfig>,
    active_config: Mutex<Option<ServerConfig>>,
    shared: Arc<Shared>,
    process_id: u32,
    server_start: Mutex<Option<Instant>>,
    router: Arc<RequestRouter>,
    socket_server: Mutex<Option<SocketServer>>,
    pipe_server: Mutex<Option<NamedPipeServer>>,
}

impl ServerController {
    pub fn new(config: ServerConfig) -> Self {
        let instance_id = discovery::create_instance_id();
        let log_path = discovery::log_path(&instance_id);
        if let Some(parent) = log_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let logger = Arc::new(Logger::new(&log_path));
        let router = Arc::new(RequestRouter::with_config(
            std::ptr::null_mut(),
            config.clone(),
        ));
        router.set_logger(Some(logger.as_ref()));
        router.set_instance_id(instance_id.clone());
        log_config(&logger, &config, "config initialized", &log_path);
        logger.info(format!("instance id={instance_id}"));

        Self {
            config: Mutex::new(config),
            active_config: Mutex::new(None),
            shared: Arc::new(Shared {
                actual_port: AtomicU16::new(0),
                actual_pipe_path: Mutex::new(String::new()),
                instance_id,
                log_path,
                logger,
                discovery_published: AtomicBool::new(false),
                active_host: Mutex::new(String::new()),
            }),
            process_id: std::process::id(),
            server_start: Mutex::new(None),
            router,
            socket_server: Mutex::new(None),
            pipe_server: Mutex::new(None),
        }
    }

    pub fn running(&self) -> bool {
        self.socket_server
            .lock()
            .ok()
            .and_then(|g| g.as_ref().map(|s| s.running()))
            .unwrap_or(false)
            || self
                .pipe_server
                .lock()
                .ok()
                .and_then(|g| g.as_ref().map(|s| s.running()))
                .unwrap_or(false)
    }

    pub fn status(&self) -> ServerControllerStatus {
        let loaded = self.config.lock().expect("config").clone();
        let active = self.active_config.lock().expect("active").clone();
        ServerControllerStatus {
            running: self.running(),
            discovery_published: self.shared.discovery_published.load(Ordering::SeqCst),
            loaded_config: loaded,
            has_active_config: active.is_some(),
            active_config: active.unwrap_or_default(),
            instance_id: self.shared.instance_id.clone(),
            log_path: self.shared.log_path.clone(),
            actual_port: self
                .socket_server
                .lock()
                .ok()
                .and_then(|g| g.as_ref().map(|s| s.actual_port()))
                .unwrap_or_else(|| self.shared.actual_port.load(Ordering::SeqCst)),
            actual_pipe_path: self.shared.actual_pipe_path.lock().expect("pipe").clone(),
        }
    }

    pub fn set_config(&self, config: ServerConfig) {
        log_config(
            &self.shared.logger,
            &config,
            "config reloaded",
            &self.shared.log_path,
        );
        self.router.set_config(config.clone());
        *self.config.lock().expect("config") = config;
    }

    pub fn start(&self, context: *mut Context) {
        if self.running() {
            return;
        }
        let config = self.config.lock().expect("config").clone();
        *self.active_config.lock().expect("active") = Some(config.clone());
        *self.shared.active_host.lock().expect("host") = config.host.clone();
        self.router.set_context(context);
        self.router.set_logger(Some(self.shared.logger.as_ref()));
        self.router.set_config(config.clone());

        let start = Instant::now();
        *self.server_start.lock().expect("start") = Some(start);
        let pid = self.process_id;
        let log_path = discovery::path_utf8(&self.shared.log_path);
        let config_path = discovery::path_utf8(&config.source_path);
        self.router
            .set_status_snapshot_provider(move || RouterStatusSnapshot {
                pid,
                log_path: log_path.clone(),
                config_path: config_path.clone(),
                uptime: start.elapsed().as_secs(),
            });
        self.shared.logger.info("server starting");

        if config.transport.includes_tcp() {
            let shared = Arc::clone(&self.shared);
            let mut server = SocketServer::new(
                config.host.clone(),
                config.port,
                Arc::clone(&self.router),
                Arc::clone(&self.shared.logger),
                move |port| {
                    shared.actual_port.store(port, Ordering::SeqCst);
                    shared.publish();
                },
            );
            server.start();
            *self.socket_server.lock().expect("socket") = Some(server);
        }

        if config.transport.includes_pipe() {
            let pipe_name = if config.pipe_name != "auto" {
                config.pipe_name.clone()
            } else {
                format!("{}-{}", crate::meta::DLL_NAME, self.shared.instance_id)
            };
            let shared = Arc::clone(&self.shared);
            let mut server = NamedPipeServer::new(
                pipe_name,
                Arc::clone(&self.router),
                Arc::clone(&self.shared.logger),
                move |pipe_path| {
                    *shared.actual_pipe_path.lock().expect("pipe") = pipe_path;
                    shared.publish();
                },
            );
            server.start();
            *self.pipe_server.lock().expect("pipe") = Some(server);
        }
    }

    pub fn stop(&self) {
        if let Some(server) = self.socket_server.lock().expect("socket").take() {
            self.shared.logger.info("tcp server stopping");
            server.stop();
        }
        if let Some(server) = self.pipe_server.lock().expect("pipe").take() {
            self.shared.logger.info("pipe server stopping");
            server.stop();
        }
        if self
            .shared
            .discovery_published
            .swap(false, Ordering::SeqCst)
        {
            discovery::remove(&self.shared.instance_id, &self.shared.logger);
        }
        self.router.set_context(std::ptr::null_mut());
        self.router.set_logger(None);
        self.shared.actual_port.store(0, Ordering::SeqCst);
        self.shared.actual_pipe_path.lock().expect("pipe").clear();
    }

    pub fn toggle(&self, context: *mut Context) {
        if self.running() {
            self.stop();
        } else {
            self.start(context);
        }
    }
}

impl Drop for ServerController {
    fn drop(&mut self) {
        self.stop();
    }
}

fn log_config(logger: &Logger, config: &ServerConfig, label: &str, log_path: &std::path::Path) {
    if !config.source_path.as_os_str().is_empty() {
        logger.info(format!(
            "{label} path={}{}",
            discovery::path_utf8(&config.source_path),
            if config.loaded_from_file {
                " (loaded)"
            } else {
                " (not found; using defaults)"
            }
        ));
    }
    logger.info(format!(
        "{label} transport={} host={} port={} pipe_name={} resolved_log={}",
        config.transport.name(),
        config.host,
        if config.auto_port {
            "auto".to_string()
        } else {
            config.port.to_string()
        },
        config.pipe_name,
        discovery::path_utf8(log_path)
    ));
}
