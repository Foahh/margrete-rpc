pub mod config;
pub mod instance;
pub mod logger;
mod pipe;

use crate::abi::Context;
use crate::rpc::router::{RequestRouter, RouterStatusSnapshot};
use config::ServerConfig;
use instance::AllocatedInstance;
use logger::{Logger, path_utf8};
use pipe::NamedPipeServer;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct ServerControllerStatus {
    pub running: bool,
    pub loaded_config: ServerConfig,
    pub active_config: ServerConfig,
    pub has_active_config: bool,
    pub instance_id: String,
    pub pipe_name: String,
    pub log_path: PathBuf,
}

struct Shared {
    instance_id: String,
    pipe_name: String,
    logger: Arc<Logger>,
    plugin_dir: Option<PathBuf>,
}

pub struct ServerController {
    config: Mutex<ServerConfig>,
    active_config: Mutex<Option<ServerConfig>>,
    shared: Arc<Shared>,
    process_id: u32,
    server_start: Mutex<Option<Instant>>,
    router: Arc<RequestRouter>,
    pipe_server: Mutex<Option<NamedPipeServer>>,
    _instance: AllocatedInstance,
}

impl ServerController {
    pub fn new(config: ServerConfig, plugin_dir: Option<PathBuf>) -> Self {
        let instance = instance::allocate().expect("allocate margrete-XXXX");
        let instance_id = instance.code.clone();
        let pipe_name = instance.pipe_name();
        let logger = Arc::new(Logger::new());
        let router = Arc::new(RequestRouter::with_config(
            std::ptr::null_mut(),
            config.clone(),
        ));
        router.set_logger(Some(logger.as_ref()));
        router.set_instance_id(instance_id.clone());

        let controller = Self {
            config: Mutex::new(config),
            active_config: Mutex::new(None),
            shared: Arc::new(Shared {
                instance_id,
                pipe_name,
                logger,
                plugin_dir,
            }),
            process_id: std::process::id(),
            server_start: Mutex::new(None),
            router,
            pipe_server: Mutex::new(None),
            _instance: instance,
        };
        controller.apply_logger();
        let config = controller.config.lock().expect("config").clone();
        log_config(
            &controller.shared.logger,
            &config,
            "config initialized",
            &controller.shared.logger.path(),
        );
        controller.shared.logger.info(format!(
            "instance id={} pipe={}",
            controller.shared.instance_id, controller.shared.pipe_name
        ));
        controller
    }

    pub fn running(&self) -> bool {
        self.pipe_server
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
            loaded_config: loaded,
            has_active_config: active.is_some(),
            active_config: active.unwrap_or_default(),
            instance_id: self.shared.instance_id.clone(),
            pipe_name: self.shared.pipe_name.clone(),
            log_path: self.shared.logger.path(),
        }
    }

    pub fn set_config(&self, config: ServerConfig) {
        let running = self.running();
        self.router.set_config(config.clone());
        *self.config.lock().expect("config") = config;
        if !running {
            self.apply_logger();
        }
        let config = self.config.lock().expect("config").clone();
        log_config(
            &self.shared.logger,
            &config,
            "config reloaded",
            &self.shared.logger.path(),
        );
    }

    pub fn start(&self, context: *mut Context) {
        if self.running() {
            return;
        }
        let config = self.config.lock().expect("config").clone();
        *self.active_config.lock().expect("active") = Some(config.clone());
        self.apply_logger();
        self.router.set_context(context);
        self.router.set_logger(Some(self.shared.logger.as_ref()));
        self.router.set_config(config.clone());

        let start = Instant::now();
        *self.server_start.lock().expect("start") = Some(start);
        let pid = self.process_id;
        let log_path = path_utf8(&self.shared.logger.path());
        let config_path = path_utf8(&config.source_path);
        self.router
            .set_status_snapshot_provider(move || RouterStatusSnapshot {
                pid,
                log_path: log_path.clone(),
                config_path: config_path.clone(),
                uptime: start.elapsed().as_secs(),
            });
        self.shared
            .logger
            .info(format!("server starting pipe={}", self.shared.pipe_name));

        let mut server = NamedPipeServer::new(
            self.shared.pipe_name.clone(),
            Arc::clone(&self.router),
            Arc::clone(&self.shared.logger),
        );
        server.start();
        *self.pipe_server.lock().expect("pipe") = Some(server);
    }

    pub fn stop(&self) {
        if let Some(server) = self.pipe_server.lock().expect("pipe").take() {
            self.shared.logger.info("pipe server stopping");
            server.stop();
        }
        self.router.set_context(std::ptr::null_mut());
        self.router.set_logger(None);
        *self.active_config.lock().expect("active") = None;
    }

    pub fn toggle(&self, context: *mut Context) {
        if self.running() {
            self.stop();
        } else {
            self.start(context);
        }
    }

    fn apply_logger(&self) {
        let logging = self.config.lock().expect("config").logging;
        let path = if logging {
            log_file_path(self.shared.plugin_dir.as_deref(), &self.shared.instance_id)
        } else {
            None
        };
        self.shared.logger.configure(path.as_deref());
    }
}

impl Drop for ServerController {
    fn drop(&mut self) {
        self.stop();
    }
}

fn log_file_path(plugin_dir: Option<&Path>, code: &str) -> Option<PathBuf> {
    Some(
        plugin_dir?
            .join("margrete_rpc")
            .join("logs")
            .join(format!("margrete-{code}-{}.log", logger::local_date())),
    )
}

fn log_config(logger: &Logger, config: &ServerConfig, label: &str, log_path: &Path) {
    if !config.source_path.as_os_str().is_empty() {
        logger.info(format!(
            "{label} path={}{}",
            path_utf8(&config.source_path),
            if config.loaded_from_file {
                " (loaded)"
            } else {
                " (not found; using defaults)"
            }
        ));
    }
    logger.info(format!(
        "{label} logging={} resolved_log={}",
        if config.logging { "on" } else { "off" },
        if log_path.as_os_str().is_empty() {
            "(disabled)".to_string()
        } else {
            path_utf8(log_path)
        }
    ));
}
