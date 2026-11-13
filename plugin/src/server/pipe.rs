use crate::error::PluginError;
use crate::rpc::framing::{self, MAX_FRAME_SIZE};
use crate::rpc::router::RequestRouter;
use interprocess::os::windows::named_pipe::{
    DuplexPipeStream, PipeListener, PipeListenerOptions, PipeMode, WaitTimeout, pipe_mode,
};
use interprocess::os::windows::security_descriptor::SecurityDescriptor;
use std::io::{self, Read, Write};
use std::os::windows::io::AsRawHandle;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;
use windows::Win32::Foundation::{HANDLE, WAIT_OBJECT_0};
use windows::Win32::System::Pipes::PeekNamedPipe;
use windows::Win32::System::Threading::WaitForSingleObject;

type BytePipe = DuplexPipeStream<pipe_mode::Bytes>;
type BytePipeListener = PipeListener<pipe_mode::Bytes, pipe_mode::Bytes>;

const IO_POLL_INTERVAL: Duration = Duration::from_millis(10);
const ACCEPT_RETRY_LIMIT: u32 = 3;
const ACCEPT_RETRY_DELAY: Duration = Duration::from_millis(50);
const LISTEN_READY_TIMEOUT: Duration = Duration::from_secs(2);
#[cfg(not(test))]
const MAX_CLIENTS: usize = 32;
#[cfg(test)]
const MAX_CLIENTS: usize = 4;

pub struct NamedPipeServer {
    pipe_name: String,
    allow_low_integrity: bool,
    router: Arc<RequestRouter>,
    running: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    thread: Mutex<Option<JoinHandle<()>>>,
}

impl NamedPipeServer {
    pub fn new(pipe_name: String, router: Arc<RequestRouter>, allow_low_integrity: bool) -> Self {
        Self {
            pipe_name,
            allow_low_integrity,
            router,
            running: Arc::new(AtomicBool::new(false)),
            stop: Arc::new(AtomicBool::new(false)),
            thread: Mutex::new(None),
        }
    }

    pub fn start(&mut self) -> io::Result<()> {
        if self.running() {
            return Ok(());
        }
        self.stop.store(false, Ordering::SeqCst);
        if let Some(previous) = self.thread.lock().expect("thread").take() {
            let _ = previous.join();
        }
        let pipe_name = self.pipe_name.clone();
        let allow_low_integrity = self.allow_low_integrity;
        let router = Arc::clone(&self.router);
        let running = Arc::clone(&self.running);
        let stop = Arc::clone(&self.stop);
        let (ready_tx, ready_rx) = mpsc::sync_channel(1);
        let thread = thread::spawn(move || {
            run(
                pipe_name,
                router,
                running,
                stop,
                ready_tx,
                allow_low_integrity,
            )
        });
        *self.thread.lock().expect("thread") = Some(thread);
        match ready_rx.recv_timeout(LISTEN_READY_TIMEOUT) {
            Ok(Ok(())) => Ok(()),
            Ok(Err(err)) => {
                self.join_listener();
                Err(err)
            }
            Err(_) => {
                self.stop.store(true, Ordering::SeqCst);
                self.running.store(false, Ordering::SeqCst);
                self.join_listener();
                Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "named pipe listener did not become ready",
                ))
            }
        }
    }

    pub fn stop(&self) {
        self.stop_while(|| {});
    }

    /// Stop and join all workers, pumping pending UI jobs while waiting.
    /// Use this on the UI thread so workers blocked in `UiDispatcher::call` can finish.
    pub fn stop_while(&self, mut pump: impl FnMut()) {
        self.stop.store(true, Ordering::SeqCst);
        self.running.store(false, Ordering::SeqCst);
        self.join_listener_while(&mut pump);
    }

    pub fn running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    fn join_listener(&self) {
        self.join_listener_while(&mut || {});
    }

    fn join_listener_while(&self, pump: &mut impl FnMut()) {
        let Some(thread) = self.thread.lock().expect("thread").take() else {
            return;
        };
        loop {
            pump();
            let wait = unsafe { WaitForSingleObject(HANDLE(thread.as_raw_handle()), 50) };
            if wait == WAIT_OBJECT_0 {
                break;
            }
        }
        let _ = thread.join();
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
    running: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    ready: mpsc::SyncSender<io::Result<()>>,
    allow_low_integrity: bool,
) {
    let pipe_path = format!(r"\\.\pipe\{pipe_name}");
    log::info!("pipe server starting path={pipe_path}");
    let mut clients: Vec<JoinHandle<()>> = Vec::new();

    let listener = match create_listener(&pipe_path, allow_low_integrity) {
        Ok(listener) => {
            running.store(true, Ordering::SeqCst);
            let _ = ready.send(Ok(()));
            listener
        }
        Err(err) => {
            running.store(false, Ordering::SeqCst);
            log::error!("named pipe listener creation failed: {err}");
            let _ = ready.send(Err(err));
            return;
        }
    };
    let mut accept_failures = 0u32;

    while !stop.load(Ordering::SeqCst) {
        reap_clients(&mut clients);
        if clients.len() >= MAX_CLIENTS {
            match listener.accept() {
                Ok(_) => {
                    log::warn!("rejected named pipe client: at capacity ({MAX_CLIENTS})");
                }
                Err(err) if err.kind() == io::ErrorKind::WouldBlock => {
                    thread::sleep(IO_POLL_INTERVAL);
                }
                Err(err) if err.kind() == io::ErrorKind::Interrupted => {}
                Err(err) => {
                    log::error!("named pipe accept failed at capacity: {err}");
                    thread::sleep(ACCEPT_RETRY_DELAY);
                }
            }
            continue;
        }
        match listener.accept() {
            Ok(pipe) => {
                accept_failures = 0;
                spawn_client(pipe, Arc::clone(&router), Arc::clone(&stop), &mut clients);
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
    stop.store(true, Ordering::SeqCst);
    reap_clients(&mut clients);
    for handle in clients {
        let _ = handle.join();
    }
    log::info!("pipe server stopped");
}

fn create_listener(pipe_path: &str, allow_low_integrity: bool) -> io::Result<BytePipeListener> {
    // Omit the DACL so Windows uses the creator's default DACL. Only lower the
    // mandatory label; this does not grant other users access to the pipe.
    let security_descriptor = if allow_low_integrity {
        Some(SecurityDescriptor::deserialize(widestring::u16cstr!(
            "S:(ML;;NW;;;LW)"
        ))?)
    } else {
        None
    };
    PipeListenerOptions::new()
        .path(Path::new(pipe_path))
        .mode(PipeMode::Bytes)
        .nonblocking(true)
        .instance_limit(None)
        .accept_remote(!allow_low_integrity)
        .security_descriptor(security_descriptor)
        .input_buffer_size_hint(MAX_FRAME_SIZE)
        .output_buffer_size_hint(MAX_FRAME_SIZE)
        .wait_timeout(WaitTimeout::DEFAULT)
        .create_duplex::<pipe_mode::Bytes>()
}

fn spawn_client(
    pipe: BytePipe,
    router: Arc<RequestRouter>,
    stop: Arc<AtomicBool>,
    clients: &mut Vec<JoinHandle<()>>,
) {
    match thread::Builder::new()
        .name("margrete-rpc-pipe-client".into())
        .spawn(move || handle_client(pipe, router, stop))
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

fn handle_client(mut pipe: BytePipe, router: Arc<RequestRouter>, stop: Arc<AtomicBool>) {
    if let Err(err) = client_loop(&mut pipe, &router, &stop)
        && !stop.load(Ordering::SeqCst)
    {
        log::error!("{err}");
    }
    pipe.assume_flushed();
}

fn client_loop(
    pipe: &mut BytePipe,
    router: &RequestRouter,
    stop: &AtomicBool,
) -> Result<(), PluginError> {
    while !stop.load(Ordering::SeqCst) {
        let mut header = [0u8; 4];
        if !read_exact_cooperative(pipe, &mut header, true, stop)? {
            break;
        }
        let size = framing::payload_size_from_header(&header)?;
        let mut frame = vec![0u8; 4 + size as usize];
        frame[..4].copy_from_slice(&header);
        if !read_exact_cooperative(pipe, &mut frame[4..], false, stop)? {
            break;
        }
        if stop.load(Ordering::SeqCst) {
            break;
        }
        let request = framing::decode(&frame)?;
        let response = router.route(&request);
        let out = framing::encode(&response)?;
        if !write_all_cooperative(pipe, &out, stop)? {
            break;
        }
    }
    Ok(())
}

fn read_exact_cooperative(
    pipe: &mut BytePipe,
    buf: &mut [u8],
    allow_clean_eof: bool,
    stop: &AtomicBool,
) -> Result<bool, PluginError> {
    let mut received = 0usize;
    while received < buf.len() {
        if stop.load(Ordering::SeqCst) {
            return Ok(false);
        }
        match pipe.read(&mut buf[received..]) {
            Ok(0) => {
                if client_connected(pipe) {
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
    stop: &AtomicBool,
) -> Result<bool, PluginError> {
    let mut sent = 0usize;
    while sent < buf.len() {
        if stop.load(Ordering::SeqCst) {
            return Ok(false);
        }
        match pipe.write(&buf[sent..]) {
            Ok(0) if client_connected(pipe) => {
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

fn client_connected(pipe: &BytePipe) -> bool {
    let mut available = 0u32;
    unsafe {
        PeekNamedPipe(
            HANDLE(pipe.as_raw_handle()),
            None,
            0,
            None,
            Some(&mut available),
            None,
        )
        .is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rpc::proto::{Envelope, envelope};
    use crate::server::instance;
    use std::fs::File;
    use std::fs::OpenOptions;
    use std::io::{Read, Write};
    use std::sync::mpsc;
    use std::time::Instant;

    fn pipe_security(file: &File, fields: u32) -> String {
        use interprocess::os::windows::security_descriptor::{
            AsSecurityDescriptorExt, BorrowedSecurityDescriptor,
        };
        use windows::Win32::Security::{GetKernelObjectSecurity, PSECURITY_DESCRIPTOR};

        let mut needed = 0;
        let handle = HANDLE(file.as_raw_handle());
        unsafe {
            let _ = GetKernelObjectSecurity(handle, fields, None, 0, &mut needed);
            assert!(needed > 0);
            let mut buffer = vec![0usize; (needed as usize).div_ceil(size_of::<usize>())];
            GetKernelObjectSecurity(
                handle,
                fields,
                Some(PSECURITY_DESCRIPTOR(buffer.as_mut_ptr().cast())),
                needed,
                &mut needed,
            )
            .expect("read pipe security");
            BorrowedSecurityDescriptor::from_ptr(buffer.as_ptr().cast())
                .serialize(fields, |s| s.to_string_lossy())
                .expect("serialize pipe security")
        }
    }

    #[test]
    fn low_integrity_listener_has_dacl_and_labels_every_instance() {
        let instance = instance::allocate().expect("allocate");
        let name = instance.pipe_name();
        let path = format!(r"\\.\pipe\{name}");
        let listener = create_listener(&path, true).expect("low-integrity listener");
        let mut first_dacl = None;
        for _ in 0..3 {
            let client = connect(&name).expect("client");
            let server = listener.accept().expect("accept");
            let dacl = pipe_security(&client, 4);
            assert!(dacl.starts_with("D:"), "DACL must be present");
            assert!(!dacl.contains("NO_ACCESS_CONTROL"), "DACL must not be null");
            if let Some(first) = &first_dacl {
                assert_eq!(&dacl, first);
            } else {
                first_dacl = Some(dacl);
            }
            let label = pipe_security(&client, 0x10);
            assert!(
                label.ends_with("(ML;;NW;;;LW)"),
                "unexpected label: {label}"
            );
            drop(server);
            drop(client);
        }
    }

    #[test]
    fn low_integrity_server_accepts_rpc_and_restarts() {
        let instance = instance::allocate().expect("allocate");
        let router = Arc::new(RequestRouter::new(std::ptr::null_mut()));
        let mut server = NamedPipeServer::new(instance.pipe_name(), router, true);
        for _ in 0..2 {
            server.start().expect("start");
            ping_until(&instance.pipe_name(), Duration::from_secs(2));
            server.stop();
        }
    }

    #[test]
    #[ignore = "run from a medium-integrity Windows terminal to test the integrity boundary"]
    fn low_integrity_client_requires_opt_in_on_medium_server() {
        use std::os::windows::io::{FromRawHandle, OwnedHandle};
        use windows::Win32::Security::{
            DuplicateTokenEx, GetSidSubAuthority, GetTokenInformation, PSID, RevertToSelf, SID,
            SID_AND_ATTRIBUTES, SID_IDENTIFIER_AUTHORITY, SecurityImpersonation,
            SetTokenInformation, TOKEN_ADJUST_DEFAULT, TOKEN_DUPLICATE, TOKEN_IMPERSONATE,
            TOKEN_MANDATORY_LABEL, TOKEN_QUERY, TokenImpersonation, TokenIntegrityLevel,
        };
        use windows::Win32::System::Threading::{
            GetCurrentProcess, OpenProcessToken, SetThreadToken,
        };

        struct Revert;
        impl Drop for Revert {
            fn drop(&mut self) {
                unsafe { RevertToSelf().expect("revert test impersonation") };
            }
        }

        // Lower only this test's client thread; the server retains its original token.
        unsafe {
            let mut original = HANDLE::default();
            OpenProcessToken(
                GetCurrentProcess(),
                TOKEN_QUERY | TOKEN_DUPLICATE,
                &mut original,
            )
            .expect("process token");
            let _original = OwnedHandle::from_raw_handle(original.0);
            let mut needed = 0;
            let _ = GetTokenInformation(original, TokenIntegrityLevel, None, 0, &mut needed);
            let mut buffer = vec![0usize; (needed as usize).div_ceil(size_of::<usize>())];
            GetTokenInformation(
                original,
                TokenIntegrityLevel,
                Some(buffer.as_mut_ptr().cast()),
                needed,
                &mut needed,
            )
            .expect("integrity level");
            let label = &*buffer.as_ptr().cast::<TOKEN_MANDATORY_LABEL>();
            assert!(
                *GetSidSubAuthority(label.Label.Sid, 0) >= 8192,
                "medium-server comparison requires a medium-integrity test runner"
            );

            for enabled in [false, true] {
                let instance = instance::allocate().expect("allocate");
                let router = Arc::new(RequestRouter::new(std::ptr::null_mut()));
                let mut server = NamedPipeServer::new(instance.pipe_name(), router, enabled);
                server.start().expect("start");
                let mut low = HANDLE::default();
                DuplicateTokenEx(
                    original,
                    TOKEN_QUERY | TOKEN_IMPERSONATE | TOKEN_ADJUST_DEFAULT,
                    None,
                    SecurityImpersonation,
                    TokenImpersonation,
                    &mut low,
                )
                .expect("duplicate token");
                let _low = OwnedHandle::from_raw_handle(low.0);
                let mut sid = SID {
                    Revision: 1,
                    SubAuthorityCount: 1,
                    IdentifierAuthority: SID_IDENTIFIER_AUTHORITY {
                        Value: [0, 0, 0, 0, 0, 16],
                    },
                    SubAuthority: [4096],
                };
                let label = TOKEN_MANDATORY_LABEL {
                    Label: SID_AND_ATTRIBUTES {
                        Sid: PSID((&mut sid as *mut SID).cast()),
                        Attributes: 0x20,
                    },
                };
                SetTokenInformation(
                    low,
                    TokenIntegrityLevel,
                    (&label as *const TOKEN_MANDATORY_LABEL).cast(),
                    (size_of::<TOKEN_MANDATORY_LABEL>() + size_of::<SID>()) as u32,
                )
                .expect("lower integrity");
                SetThreadToken(None, Some(low)).expect("impersonate low client");
                let revert = Revert;
                let result = ping(&instance.pipe_name());
                drop(revert);
                server.stop();
                if enabled {
                    result.expect("low client RPC with opt-in");
                } else {
                    assert_eq!(
                        result
                            .expect_err("low client must be denied by default")
                            .raw_os_error(),
                        Some(5)
                    );
                }
            }
        }
    }

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
        let mut server = NamedPipeServer::new(instance.pipe_name(), router, false);
        server.start().expect("start");
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
        server.start().expect("start");
        ping_until(&pipe_name, Duration::from_secs(2));
        for _ in 0..64 {
            ping(&pipe_name).expect("ping");
        }
        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(!server.running());
        server.stop();

        server.start().expect("restart");
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
            for _ in 0..3 {
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

    fn connect_timeout(pipe_name: &str, timeout: Duration) -> io::Result<File> {
        let (tx, rx) = mpsc::channel();
        let name = pipe_name.to_string();
        thread::spawn(move || {
            let _ = tx.send(connect(&name));
        });
        rx.recv_timeout(timeout)
            .map_err(|_| io::Error::new(io::ErrorKind::TimedOut, "connect timed out"))?
    }

    #[test]
    fn listen_failure_does_not_leave_server_running() {
        let (instance, occupying) = start_test_server();
        let router = Arc::new(RequestRouter::new(std::ptr::null_mut()));
        let mut server = NamedPipeServer::new(instance.pipe_name(), router, false);
        assert!(server.start().is_err());
        assert!(!server.running());
        assert!(server.start().is_err());
        assert!(!server.running());
        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(1));
        occupying.stop();
    }

    #[test]
    fn reaps_finished_clients_and_rejects_overflow() {
        let (instance, server) = start_test_server();
        let pipe_name = instance.pipe_name();
        ping_until(&pipe_name, Duration::from_secs(2));

        let mut idle = Vec::new();
        for _ in 0..MAX_CLIENTS {
            idle.push(connect(&pipe_name).expect("idle client"));
        }
        thread::sleep(Duration::from_millis(50));

        match connect_timeout(&pipe_name, Duration::from_millis(400)) {
            Err(_) => {}
            Ok(mut file) => {
                let request = Envelope {
                    request_id: 2,
                    body: Some(envelope::Body::PingRequest(Default::default())),
                };
                let encoded = framing::encode(&request).expect("encode");
                let overflow = file.write_all(&encoded).and_then(|_| {
                    let mut header = [0u8; 4];
                    file.read_exact(&mut header)
                });
                assert!(
                    overflow.is_err(),
                    "server should reject clients above {MAX_CLIENTS}"
                );
            }
        }

        idle.pop();
        thread::sleep(Duration::from_millis(50));
        ping_until(&pipe_name, Duration::from_secs(2));

        let started = Instant::now();
        server.stop();
        assert!(started.elapsed() < Duration::from_secs(1));
        assert!(!server.running());
    }
}
