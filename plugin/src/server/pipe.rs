use crate::error::PluginError;
use crate::rpc::framing::{self, MAX_FRAME_SIZE};
use crate::rpc::router::RequestRouter;
use interprocess::os::windows::named_pipe::{
    DuplexPipeStream, PipeListener, PipeListenerOptions, PipeMode, WaitTimeout, pipe_mode,
};
use std::io::{self, Read, Write};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;

type BytePipe = DuplexPipeStream<pipe_mode::Bytes>;
type BytePipeListener = PipeListener<pipe_mode::Bytes, pipe_mode::Bytes>;

const IO_POLL_INTERVAL: Duration = Duration::from_millis(10);
const ACCEPT_RETRY_LIMIT: u32 = 3;
const ACCEPT_RETRY_DELAY: Duration = Duration::from_millis(50);

pub struct NamedPipeServer {
    pipe_name: String,
    router: Arc<RequestRouter>,
    running: Arc<AtomicBool>,
    thread: Mutex<Option<JoinHandle<()>>>,
}

impl NamedPipeServer {
    pub fn new(pipe_name: String, router: Arc<RequestRouter>) -> Self {
        Self {
            pipe_name,
            router,
            running: Arc::new(AtomicBool::new(false)),
            thread: Mutex::new(None),
        }
    }

    pub fn start(&mut self) {
        if self.running.swap(true, Ordering::SeqCst) {
            return;
        }
        if let Some(previous) = self.thread.lock().expect("thread").take() {
            let _ = previous.join();
        }
        let pipe_name = self.pipe_name.clone();
        let router = Arc::clone(&self.router);
        let running = Arc::clone(&self.running);
        let thread = thread::spawn(move || run(pipe_name, router, running));
        *self.thread.lock().expect("thread") = Some(thread);
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        let Some(thread) = self.thread.lock().expect("thread").take() else {
            return;
        };
        let _ = thread.join();
    }

    pub fn running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }
}

impl Drop for NamedPipeServer {
    fn drop(&mut self) {
        self.stop();
    }
}

fn run(pipe_name: String, router: Arc<RequestRouter>, running: Arc<AtomicBool>) {
    let pipe_path = format!(r"\\.\pipe\{pipe_name}");
    log::info!("pipe server starting path={pipe_path}");
    let mut clients: Vec<JoinHandle<()>> = Vec::new();

    let listener = match create_listener(&pipe_path) {
        Ok(listener) => listener,
        Err(err) => {
            log::error!("named pipe listener creation failed: {err}");
            running.store(false, Ordering::SeqCst);
            return;
        }
    };
    let mut accept_failures = 0u32;

    while running.load(Ordering::SeqCst) {
        reap_clients(&mut clients);
        match listener.accept() {
            Ok(pipe) => {
                accept_failures = 0;
                spawn_client(
                    pipe,
                    Arc::clone(&router),
                    Arc::clone(&running),
                    &mut clients,
                );
            }
            Err(err) if err.kind() == io::ErrorKind::WouldBlock => {
                thread::sleep(IO_POLL_INTERVAL);
            }
            Err(err) if err.kind() == io::ErrorKind::Interrupted => {}
            Err(err) => {
                accept_failures += 1;
                if accept_failures >= ACCEPT_RETRY_LIMIT {
                    log::error!(
                        "named pipe accept failed: {err}; giving up after {accept_failures} attempts"
                    );
                    break;
                }
                log::error!(
                    "named pipe accept failed: {err}; retrying ({accept_failures}/{ACCEPT_RETRY_LIMIT})"
                );
                thread::sleep(ACCEPT_RETRY_DELAY);
            }
        }
    }

    running.store(false, Ordering::SeqCst);
    for handle in clients {
        let _ = handle.join();
    }
    log::info!("pipe server stopped");
}

fn create_listener(pipe_path: &str) -> io::Result<BytePipeListener> {
    PipeListenerOptions::new()
        .path(Path::new(pipe_path))
        .mode(PipeMode::Bytes)
        .nonblocking(true)
        .instance_limit(None)
        .accept_remote(true)
        .input_buffer_size_hint(MAX_FRAME_SIZE)
        .output_buffer_size_hint(MAX_FRAME_SIZE)
        .wait_timeout(WaitTimeout::DEFAULT)
        .create_duplex::<pipe_mode::Bytes>()
}

fn spawn_client(
    pipe: BytePipe,
    router: Arc<RequestRouter>,
    running: Arc<AtomicBool>,
    clients: &mut Vec<JoinHandle<()>>,
) {
    match thread::Builder::new()
        .name("margrete-rpc-pipe-client".into())
        .spawn(move || handle_client(pipe, router, running))
    {
        Ok(handle) => clients.push(handle),
        Err(err) => {
            log::error!("pipe client thread creation failed: {err}");
        }
    }
}

fn reap_clients(clients: &mut Vec<JoinHandle<()>>) {
    let mut index = 0;
    while index < clients.len() {
        if clients[index].is_finished() {
            let handle = clients.swap_remove(index);
            let _ = handle.join();
        } else {
            index += 1;
        }
    }
}

fn handle_client(mut pipe: BytePipe, router: Arc<RequestRouter>, running: Arc<AtomicBool>) {
    if let Err(err) = client_loop(&mut pipe, &router, &running)
        && running.load(Ordering::SeqCst)
    {
        log::error!("{err}");
    }
    pipe.assume_flushed();
}

fn client_loop(
    pipe: &mut BytePipe,
    router: &RequestRouter,
    running: &AtomicBool,
) -> Result<(), PluginError> {
    while running.load(Ordering::SeqCst) {
        let mut header = [0u8; 4];
        if !read_exact_cooperative(pipe, &mut header, true, running)? {
            break;
        }
        let size = framing::payload_size_from_header(&header)?;
        let mut frame = vec![0u8; 4 + size as usize];
        frame[..4].copy_from_slice(&header);
        if !read_exact_cooperative(pipe, &mut frame[4..], false, running)? {
            break;
        }
        let request = framing::decode(&frame)?;
        let response = router.route(&request);
        let out = framing::encode(&response)?;
        if !write_all_cooperative(pipe, &out, running)? {
            break;
        }
    }
    Ok(())
}

fn read_exact_cooperative(
    pipe: &mut BytePipe,
    buf: &mut [u8],
    allow_clean_eof: bool,
    running: &AtomicBool,
) -> Result<bool, PluginError> {
    let mut received = 0usize;
    while received < buf.len() {
        if !running.load(Ordering::SeqCst) {
            return Ok(false);
        }
        match pipe.read(&mut buf[received..]) {
            Ok(0) => {
                if pipe.client_process_id().is_ok() {
                    thread::sleep(IO_POLL_INTERVAL);
                    continue;
                }
                if allow_clean_eof && received == 0 {
                    return Ok(false);
                }
                return Err(PluginError::internal(
                    "pipe client disconnected before frame completed",
                ));
            }
            Ok(n) => received += n,
            Err(err) if err.kind() == io::ErrorKind::WouldBlock => {
                thread::sleep(IO_POLL_INTERVAL);
            }
            Err(err) if err.kind() == io::ErrorKind::Interrupted => {}
            Err(err) => {
                if allow_clean_eof && received == 0 {
                    return Ok(false);
                }
                return Err(PluginError::internal(format!("pipe read failed: {err}")));
            }
        }
    }
    Ok(true)
}

fn write_all_cooperative(
    pipe: &mut BytePipe,
    buf: &[u8],
    running: &AtomicBool,
) -> Result<bool, PluginError> {
    let mut sent = 0usize;
    while sent < buf.len() {
        if !running.load(Ordering::SeqCst) {
            return Ok(false);
        }
        match pipe.write(&buf[sent..]) {
            Ok(0) if pipe.client_process_id().is_ok() => {
                thread::sleep(IO_POLL_INTERVAL);
            }
            Ok(0) => {
                return Err(PluginError::internal(
                    "pipe client disconnected during write",
                ));
            }
            Ok(n) => sent += n,
            Err(err) if err.kind() == io::ErrorKind::WouldBlock => {
                thread::sleep(IO_POLL_INTERVAL);
            }
            Err(err) if err.kind() == io::ErrorKind::Interrupted => {}
            Err(err) => {
                return Err(PluginError::internal(format!("pipe write failed: {err}")));
            }
        }
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rpc::proto::{Envelope, envelope};
    use crate::server::instance;
    use std::fs::File;
    use std::fs::OpenOptions;
    use std::io::{Read, Write};
    use std::time::Instant;

    fn connect(pipe_name: &str) -> io::Result<File> {
        let path = format!(r"\\.\pipe\{pipe_name}");
        let start = Instant::now();
        loop {
            match OpenOptions::new().read(true).write(true).open(&path) {
                Ok(file) => return Ok(file),
                Err(err)
                    if matches!(err.raw_os_error(), Some(2 | 231))
                        && start.elapsed() < Duration::from_secs(2) =>
                {
                    thread::sleep(Duration::from_millis(5));
                }
                Err(err) => return Err(err),
            }
        }
    }

    fn ping(pipe_name: &str) -> io::Result<()> {
        let mut file = connect(pipe_name)?;
        let request = Envelope {
            request_id: 1,
            body: Some(envelope::Body::PingRequest(Default::default())),
        };
        file.write_all(&framing::encode(&request).expect("encode"))?;
        let mut header = [0u8; 4];
        file.read_exact(&mut header)?;
        let size = u32::from_le_bytes(header) as usize;
        let mut payload = vec![0u8; size];
        file.read_exact(&mut payload)?;
        let mut frame = Vec::with_capacity(4 + size);
        frame.extend_from_slice(&header);
        frame.extend_from_slice(&payload);
        let decoded = framing::decode(&frame).expect("decode");
        assert!(matches!(
            decoded.body,
            Some(envelope::Body::PingResponse(_))
        ));
        Ok(())
    }

    fn fragmented_ping(pipe_name: &str) -> io::Result<()> {
        let mut file = connect(pipe_name)?;
        let request = Envelope {
            request_id: 7,
            body: Some(envelope::Body::PingRequest(Default::default())),
        };
        let frame = framing::encode(&request).expect("encode");

        for byte in frame {
            file.write_all(&[byte])?;
            thread::sleep(Duration::from_millis(1));
        }

        let mut header = [0u8; 4];
        for byte in &mut header {
            file.read_exact(std::slice::from_mut(byte))?;
        }
        let size = u32::from_le_bytes(header) as usize;
        let mut payload = vec![0u8; size];
        for byte in &mut payload {
            file.read_exact(std::slice::from_mut(byte))?;
        }
        let mut response = header.to_vec();
        response.extend_from_slice(&payload);
        let decoded = framing::decode(&response).expect("decode");
        assert_eq!(decoded.request_id, 7);
        assert!(matches!(
            decoded.body,
            Some(envelope::Body::PingResponse(_))
        ));
        Ok(())
    }

    fn ping_until(pipe_name: &str, timeout: Duration) {
        let start = Instant::now();
        let mut last = None;
        while start.elapsed() < timeout {
            match ping(pipe_name) {
                Ok(()) => return,
                Err(err) => last = Some(err),
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("timed out pinging {pipe_name}: {last:?}");
    }

    fn start_test_server() -> (AllocatedGuard, NamedPipeServer) {
        let instance = instance::allocate().expect("allocate");
        let router = Arc::new(RequestRouter::new(std::ptr::null_mut()));
        let mut server = NamedPipeServer::new(instance.pipe_name(), router);
        server.start();
        (AllocatedGuard(instance), server)
    }

    struct AllocatedGuard(instance::AllocatedInstance);

    impl AllocatedGuard {
        fn pipe_name(&self) -> String {
            self.0.pipe_name()
        }
    }

    #[test]
    fn lifecycle_is_idempotent_and_restartable() {
        let (instance, mut server) = start_test_server();
        let pipe_name = instance.pipe_name();
        server.start();
        ping_until(&pipe_name, Duration::from_secs(2));
        for _ in 0..64 {
            ping(&pipe_name).expect("ping");
        }
        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(!server.running());
        server.stop();

        server.start();
        ping_until(&pipe_name, Duration::from_secs(2));
        server.stop();
        assert!(!server.running());
    }

    #[test]
    fn accepts_concurrent_clients() {
        let (instance, server) = start_test_server();
        let pipe_name = instance.pipe_name();
        ping_until(&pipe_name, Duration::from_secs(2));
        thread::scope(|scope| {
            for _ in 0..8 {
                let name = pipe_name.clone();
                scope.spawn(move || {
                    for _ in 0..16 {
                        ping(&name).expect("ping");
                    }
                });
            }
        });
        server.stop();
    }

    #[test]
    fn accepts_fragmented_frames() {
        let (instance, server) = start_test_server();
        fragmented_ping(&instance.pipe_name()).expect("fragmented ping");
        server.stop();
    }

    #[test]
    fn stops_with_idle_and_partial_clients() {
        let (instance, server) = start_test_server();
        let pipe_name = instance.pipe_name();
        ping_until(&pipe_name, Duration::from_secs(2));

        let _idle = connect(&pipe_name).expect("idle client");
        let mut partial = connect(&pipe_name).expect("partial client");
        partial.write_all(&[8, 0]).expect("partial header");
        thread::sleep(Duration::from_millis(20));

        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(1));
        assert!(!server.running());
    }
}
