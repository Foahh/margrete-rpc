use super::logger::Logger;
use crate::error::PluginError;
use crate::rpc::framing::{self, MAX_FRAME_SIZE};
use crate::rpc::router::RequestRouter;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use windows::Win32::Foundation::{CloseHandle, ERROR_PIPE_CONNECTED, ERROR_PIPE_LISTENING, HANDLE};
use windows::Win32::Storage::FileSystem::{PIPE_ACCESS_DUPLEX, ReadFile, WriteFile};
use windows::Win32::System::Pipes::{
    ConnectNamedPipe, CreateNamedPipeW, DisconnectNamedPipe, PIPE_NOWAIT, PIPE_READMODE_BYTE,
    PIPE_TYPE_BYTE, PIPE_UNLIMITED_INSTANCES, PIPE_WAIT, SetNamedPipeHandleState,
};
use windows::Win32::System::Threading::Sleep;
use windows::core::PCWSTR;

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
        if let Some(thread) = self.thread.lock().expect("thread").take() {
            let _ = thread.join();
        }
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

    while running.load(Ordering::SeqCst) {
        let pipe = unsafe {
            CreateNamedPipeW(
                PCWSTR(wide.as_ptr()),
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_NOWAIT,
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
            break;
        }

        let mut connected = false;
        let mut connect_error = 0u32;
        while running.load(Ordering::SeqCst) {
            let result = unsafe { ConnectNamedPipe(pipe, None) };
            match result {
                Ok(()) => {
                    connected = true;
                    break;
                }
                Err(err) => {
                    connect_error = err.code().0 as u32;
                    if connect_error == ERROR_PIPE_CONNECTED.0 {
                        connected = true;
                        break;
                    }
                    if connect_error != ERROR_PIPE_LISTENING.0 {
                        break;
                    }
                    unsafe { Sleep(50) };
                }
            }
        }

        if !connected {
            let _ = unsafe { CloseHandle(pipe) };
            if !running.load(Ordering::SeqCst) {
                break;
            }
            if connect_error != 0 {
                logger.error(format!("ConnectNamedPipe failed error={connect_error}"));
            }
            continue;
        }
        if !running.load(Ordering::SeqCst) {
            let _ = unsafe { CloseHandle(pipe) };
            break;
        }

        let mode = PIPE_READMODE_BYTE | PIPE_WAIT;
        if unsafe { SetNamedPipeHandleState(pipe, Some(&mode), None, None) }.is_err() {
            logger.error("SetNamedPipeHandleState failed");
            let _ = unsafe { CloseHandle(pipe) };
            continue;
        }

        let router_c = Arc::clone(&router);
        let logger_c = Arc::clone(&logger);
        let running_c = Arc::clone(&running);
        let raw = pipe.0 as isize;
        match thread::Builder::new().spawn(move || {
            handle_client(
                HANDLE(raw as *mut std::ffi::c_void),
                router_c,
                logger_c,
                running_c,
            )
        }) {
            Ok(handle) => clients.push(handle),
            Err(err) => {
                logger.error(format!("pipe client thread creation failed: {err}"));
                let _ = unsafe {
                    let _ = DisconnectNamedPipe(pipe);
                    CloseHandle(pipe)
                };
            }
        }
    }

    running.store(false, Ordering::SeqCst);
    for handle in clients {
        let _ = handle.join();
    }
    logger.info("pipe server stopped");
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
    unsafe {
        let _ = DisconnectNamedPipe(pipe);
        let _ = CloseHandle(pipe);
    }
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
