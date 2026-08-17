use super::logger::Logger;
use crate::error::PluginError;
use crate::rpc::framing::{self, MAX_FRAME_SIZE};
use crate::rpc::router::RequestRouter;
use std::os::windows::io::AsRawHandle;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};
use windows::Win32::Foundation::{
    CloseHandle, ERROR_PIPE_CONNECTED, GENERIC_READ, GENERIC_WRITE, HANDLE, WAIT_OBJECT_0,
    WIN32_ERROR,
};
use windows::Win32::Storage::FileSystem::{
    CreateFileW, FILE_ATTRIBUTE_NORMAL, FILE_SHARE_MODE, OPEN_EXISTING, PIPE_ACCESS_DUPLEX,
    ReadFile, WriteFile,
};
use windows::Win32::System::Pipes::{
    ConnectNamedPipe, CreateNamedPipeW, DisconnectNamedPipe, PIPE_READMODE_BYTE, PIPE_TYPE_BYTE,
    PIPE_UNLIMITED_INSTANCES, PIPE_WAIT,
};
use windows::Win32::System::Threading::WaitForSingleObject;
use windows::core::PCWSTR;

const STOP_TIMEOUT: Duration = Duration::from_secs(5);
const STOP_POLL_MS: u32 = 50;
const CONNECT_RETRY_LIMIT: u32 = 3;
const CONNECT_RETRY_DELAY: Duration = Duration::from_millis(50);

pub struct NamedPipeServer {
    pipe_name: String,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
    thread: Mutex<Option<JoinHandle<()>>>,
}

impl NamedPipeServer {
    pub fn new(pipe_name: String, router: Arc<RequestRouter>, logger: Arc<Logger>) -> Self {
        Self {
            pipe_name,
            router,
            logger,
            running: Arc::new(AtomicBool::new(false)),
            thread: Mutex::new(None),
        }
    }

    pub fn start(&mut self) {
        if self.running.swap(true, Ordering::SeqCst) {
            return;
        }
        let pipe_name = self.pipe_name.clone();
        let router = Arc::clone(&self.router);
        let logger = Arc::clone(&self.logger);
        let running = Arc::clone(&self.running);
        let thread = thread::spawn(move || run(pipe_name, router, logger, running));
        *self.thread.lock().expect("thread") = Some(thread);
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        let Some(thread) = self.thread.lock().expect("thread").take() else {
            return;
        };
        let deadline = Instant::now() + STOP_TIMEOUT;
        while Instant::now() < deadline {
            wake_listener(&self.pipe_name);
            let wait = unsafe { WaitForSingleObject(HANDLE(thread.as_raw_handle()), STOP_POLL_MS) };
            if wait == WAIT_OBJECT_0 {
                break;
            }
        }
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

fn run(
    pipe_name: String,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
) {
    let pipe_path = format!(r"\\.\pipe\{pipe_name}");
    logger.info(format!("pipe server starting path={pipe_path}"));
    let wide: Vec<u16> = pipe_path.encode_utf16().chain(std::iter::once(0)).collect();
    let mut clients: Vec<JoinHandle<()>> = Vec::new();

    let Some(mut listener) = create_listening_pipe(&wide, &logger) else {
        return;
    };
    let mut connect_failures = 0u32;

    while running.load(Ordering::SeqCst) {
        let connect_error = match connect_pipe(listener) {
            Ok(()) => None,
            Err(err) => Some(win32_code(&err)),
        };

        if !running.load(Ordering::SeqCst) {
            close_pipe(listener, connect_error.is_none());
            break;
        }
        if let Some(code) = connect_error {
            close_pipe(listener, false);
            connect_failures += 1;
            if connect_failures >= CONNECT_RETRY_LIMIT {
                logger.error(format!(
                    "ConnectNamedPipe failed error={code}; giving up after {connect_failures} attempts"
                ));
                break;
            }
            logger.error(format!(
                "ConnectNamedPipe failed error={code}; retrying ({connect_failures}/{CONNECT_RETRY_LIMIT})"
            ));
            thread::sleep(CONNECT_RETRY_DELAY);
            match create_listening_pipe(&wide, &logger) {
                Some(pipe) => listener = pipe,
                None => break,
            }
            continue;
        }

        connect_failures = 0;
        let next = create_listening_pipe(&wide, &logger);
        spawn_client(
            listener,
            Arc::clone(&router),
            Arc::clone(&logger),
            Arc::clone(&running),
            &mut clients,
        );
        match next {
            Some(pipe) => listener = pipe,
            None => break,
        }
    }

    running.store(false, Ordering::SeqCst);
    for handle in clients {
        let _ = handle.join();
    }
    logger.info("pipe server stopped");
}

fn create_listening_pipe(wide: &[u16], logger: &Logger) -> Option<HANDLE> {
    let pipe = unsafe {
        CreateNamedPipeW(
            PCWSTR(wide.as_ptr()),
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            MAX_FRAME_SIZE,
            MAX_FRAME_SIZE,
            0,
            None,
        )
    };
    if pipe.is_invalid() {
        logger.error(format!(
            "CreateNamedPipeW failed error={}",
            std::io::Error::last_os_error()
        ));
        None
    } else {
        Some(pipe)
    }
}

fn connect_pipe(pipe: HANDLE) -> windows::core::Result<()> {
    match unsafe { ConnectNamedPipe(pipe, None) } {
        Ok(()) => Ok(()),
        Err(err) if WIN32_ERROR::from_error(&err) == Some(ERROR_PIPE_CONNECTED) => Ok(()),
        Err(err) => Err(err),
    }
}

fn spawn_client(
    pipe: HANDLE,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
    clients: &mut Vec<JoinHandle<()>>,
) {
    let raw = pipe.0 as isize;
    let on_spawn_err = Arc::clone(&logger);
    match thread::Builder::new().spawn(move || {
        handle_client(
            HANDLE(raw as *mut std::ffi::c_void),
            router,
            logger,
            running,
        )
    }) {
        Ok(handle) => clients.push(handle),
        Err(err) => {
            on_spawn_err.error(format!("pipe client thread creation failed: {err}"));
            close_pipe(pipe, true);
        }
    }
}

fn wake_listener(pipe_name: &str) {
    let path = format!(r"\\.\pipe\{pipe_name}");
    let wide: Vec<u16> = path.encode_utf16().chain(std::iter::once(0)).collect();
    let handle = unsafe {
        CreateFileW(
            PCWSTR(wide.as_ptr()),
            GENERIC_READ.0 | GENERIC_WRITE.0,
            FILE_SHARE_MODE(0),
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
    };
    if let Ok(handle) = handle {
        let _ = unsafe { CloseHandle(handle) };
    }
}

fn close_pipe(pipe: HANDLE, disconnect: bool) {
    unsafe {
        if disconnect {
            let _ = DisconnectNamedPipe(pipe);
        }
        let _ = CloseHandle(pipe);
    }
}

fn win32_code(err: &windows::core::Error) -> u32 {
    WIN32_ERROR::from_error(err)
        .map(|code| code.0)
        .unwrap_or(err.code().0 as u32)
}

fn handle_client(
    pipe: HANDLE,
    router: Arc<RequestRouter>,
    logger: Arc<Logger>,
    running: Arc<AtomicBool>,
) {
    if let Err(err) = client_loop(pipe, &router, &running) {
        logger.error(err.to_string());
    }
    close_pipe(pipe, true);
}

fn client_loop(
    pipe: HANDLE,
    router: &RequestRouter,
    running: &AtomicBool,
) -> Result<(), PluginError> {
    while running.load(Ordering::SeqCst) {
        let mut header = [0u8; 4];
        if !read_exact(pipe, &mut header, true)? {
            break;
        }
        let size = framing::payload_size_from_header(&header)?;
        let mut frame = vec![0u8; 4 + size as usize];
        frame[..4].copy_from_slice(&header);
        read_exact(pipe, &mut frame[4..], false)?;
        let request = framing::decode(&frame)?;
        let response = router.route(&request);
        let out = framing::encode(&response)?;
        write_all(pipe, &out)?;
    }
    Ok(())
}

fn read_exact(pipe: HANDLE, buf: &mut [u8], allow_clean_eof: bool) -> Result<bool, PluginError> {
    let mut received = 0usize;
    while received < buf.len() {
        let mut n = 0u32;
        let ok = unsafe { ReadFile(pipe, Some(&mut buf[received..]), Some(&mut n), None) };
        match ok {
            Ok(()) => {
                if n == 0 {
                    if allow_clean_eof && received == 0 {
                        return Ok(false);
                    }
                    return Err(PluginError::internal(
                        "pipe client disconnected before frame completed",
                    ));
                }
                received += n as usize;
            }
            Err(_) => {
                if allow_clean_eof && received == 0 {
                    return Ok(false);
                }
                return Err(PluginError::internal(format!(
                    "ReadFile failed error={}",
                    std::io::Error::last_os_error()
                )));
            }
        }
    }
    Ok(true)
}

fn write_all(pipe: HANDLE, buf: &[u8]) -> Result<(), PluginError> {
    let mut sent = 0usize;
    while sent < buf.len() {
        let mut n = 0u32;
        let ok = unsafe { WriteFile(pipe, Some(&buf[sent..]), Some(&mut n), None) };
        if ok.is_err() || n == 0 {
            return Err(PluginError::internal(format!(
                "WriteFile failed error={}",
                std::io::Error::last_os_error()
            )));
        }
        sent += n as usize;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rpc::proto::{Envelope, envelope};
    use crate::server::instance;
    use std::fs::OpenOptions;
    use std::io::{Read, Write};

    fn ping(pipe_name: &str) -> std::io::Result<()> {
        let path = format!(r"\\.\pipe\{pipe_name}");
        let start = Instant::now();
        let mut file = loop {
            match OpenOptions::new().read(true).write(true).open(&path) {
                Ok(file) => break file,
                Err(err)
                    if matches!(err.raw_os_error(), Some(2 | 231))
                        && start.elapsed() < Duration::from_secs(2) =>
                {
                    thread::sleep(Duration::from_millis(5));
                }
                Err(err) => return Err(err),
            }
        };
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
        let logger = Arc::new(Logger::new());
        let mut server = NamedPipeServer::new(instance.pipe_name(), router, logger);
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
    fn accepts_rapid_reconnects_and_stops() {
        let (instance, server) = start_test_server();
        let pipe_name = instance.pipe_name();
        ping_until(&pipe_name, Duration::from_secs(2));
        for _ in 0..64 {
            ping(&pipe_name).expect("ping");
        }
        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(2));
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
}
