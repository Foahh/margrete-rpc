use crate::config::is_loopback_address;
use crate::error::PluginError;
use crate::framing::{self, MAX_FRAME_SIZE};
use crate::logger::Logger;
use crate::router::RequestRouter;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;

type OnTcpStarted = Box<dyn Fn(u16) + Send>;

pub struct SocketServer {
    host: String,
    port: u16,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    on_started: Mutex<Option<OnTcpStarted>>,
    running: Arc<AtomicBool>,
    actual_port: Arc<AtomicU16>,
    thread: Mutex<Option<JoinHandle<()>>>,
}

impl SocketServer {
    pub fn new(
        host: String,
        port: u16,
        router: Arc<RequestRouter>,
        logger: Arc<Logger>,
        on_started: impl Fn(u16) + Send + 'static,
    ) -> Self {
        Self {
            host,
            port,
            router,
            logger,
            on_started: Mutex::new(Some(Box::new(on_started))),
            running: Arc::new(AtomicBool::new(false)),
            actual_port: Arc::new(AtomicU16::new(0)),
            thread: Mutex::new(None),
        }
    }

    pub fn start(&mut self) {
        if self.running.swap(true, Ordering::SeqCst) {
            return;
        }
        let host = self.host.clone();
        let port = self.port;
        let router = Arc::clone(&self.router);
        let logger = Arc::clone(&self.logger);
        let running = Arc::clone(&self.running);
        let actual_port = Arc::clone(&self.actual_port);
        let on_started = self.on_started.lock().expect("cb").take();
        let thread = thread::spawn(move || {
            run(host, port, router, logger, running, actual_port, on_started);
        });
        *self.thread.lock().expect("thread") = Some(thread);
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        if let Some(thread) = self.thread.lock().expect("thread").take() {
            let _ = thread.join();
        }
    }

    pub fn running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    pub fn actual_port(&self) -> u16 {
        self.actual_port.load(Ordering::SeqCst)
    }
}

impl Drop for SocketServer {
    fn drop(&mut self) {
        self.stop();
    }
}

fn run(
    host: String,
    port: u16,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
    actual_port: Arc<AtomicU16>,
    on_started: Option<Box<dyn Fn(u16) + Send>>,
) {
    let listener = match TcpListener::bind((host.as_str(), port)) {
        Ok(listener) => listener,
        Err(_) => {
            running.store(false, Ordering::SeqCst);
            logger.error("bind failed");
            return;
        }
    };
    if listener.set_nonblocking(true).is_err() {
        running.store(false, Ordering::SeqCst);
        logger.error("listen failed");
        return;
    }
    let bound = match listener.local_addr() {
        Ok(addr) => addr.port(),
        Err(_) => {
            running.store(false, Ordering::SeqCst);
            logger.error("getsockname failed");
            return;
        }
    };
    actual_port.store(bound, Ordering::SeqCst);
    logger.info(format!("server started on {host}:{bound}"));
    if !is_loopback_address(&host) {
        logger.info(format!(
            "WARNING: server bound to non-loopback host {host}; other machines on this network can connect. \
             Set host=127.0.0.1 in {} to restrict access to this machine.",
            crate::meta::CONFIG_FILE_NAME
        ));
    }
    if let Some(cb) = on_started {
        cb(bound);
    }

    let mut clients: Vec<(JoinHandle<()>, Arc<AtomicBool>)> = Vec::new();
    while running.load(Ordering::SeqCst) {
        clients.retain(|(h, done)| {
            if done.load(Ordering::SeqCst) {
                let _ = h;
                false
            } else {
                true
            }
        });
        match listener.accept() {
            Ok((stream, _)) => {
                let done = Arc::new(AtomicBool::new(false));
                let done2 = Arc::clone(&done);
                let router = Arc::clone(&router);
                let logger = Arc::clone(&logger);
                let running = Arc::clone(&running);
                let logger_for_err = Arc::clone(&logger);
                match thread::Builder::new().spawn(move || {
                    handle_client(stream, router, logger, running);
                    done2.store(true, Ordering::SeqCst);
                }) {
                    Ok(handle) => clients.push((handle, done)),
                    Err(err) => {
                        logger_for_err.error(format!("client thread creation failed: {err}"))
                    }
                }
            }
            Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(250));
            }
            Err(_) => {
                if running.load(Ordering::SeqCst) {
                    logger.error("accept failed");
                }
                break;
            }
        }
    }

    running.store(false, Ordering::SeqCst);
    actual_port.store(0, Ordering::SeqCst);
    for (handle, _) in clients {
        let _ = handle.join();
    }
    logger.info("server stopped");
}

fn handle_client(
    mut stream: TcpStream,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
) {
    if let Err(err) = client_loop(&mut stream, &router, &running) {
        logger.error(err.to_string());
    }
}

fn client_loop(
    stream: &mut TcpStream,
    router: &RequestRouter,
    running: &AtomicBool,
) -> Result<(), PluginError> {
    let _ = stream.set_nonblocking(false);
    while running.load(Ordering::SeqCst) {
        let mut header = [0u8; 4];
        match read_exact(stream, &mut header, true) {
            Ok(false) => break,
            Ok(true) => {}
            Err(err) => return Err(err),
        }
        let size = framing::payload_size_from_header(&header)?;
        if size > MAX_FRAME_SIZE {
            return Err(PluginError::internal("frame payload is too large"));
        }
        let mut frame = vec![0u8; 4 + size as usize];
        frame[..4].copy_from_slice(&header);
        read_exact(stream, &mut frame[4..], false)?;
        let request = framing::decode(&frame)?;
        let response = router.route(&request);
        let out = framing::encode(&response)?;
        write_all(stream, &out)?;
    }
    Ok(())
}

fn read_exact(
    stream: &mut TcpStream,
    buf: &mut [u8],
    allow_clean_eof: bool,
) -> Result<bool, PluginError> {
    let mut received = 0;
    while received < buf.len() {
        match stream.read(&mut buf[received..]) {
            Ok(0) => {
                if allow_clean_eof && received == 0 {
                    return Ok(false);
                }
                return Err(PluginError::internal(
                    "client disconnected before frame completed",
                ));
            }
            Ok(n) => received += n,
            Err(_) => return Err(PluginError::internal("client disconnected")),
        }
    }
    Ok(true)
}

fn write_all(stream: &mut TcpStream, buf: &[u8]) -> Result<(), PluginError> {
    stream
        .write_all(buf)
        .map_err(|_| PluginError::internal("failed to send response frame"))
}
