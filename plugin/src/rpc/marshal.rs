use crate::error::{PluginError, Result};
use std::collections::VecDeque;
use std::ffi::c_void;
use std::panic::{self, AssertUnwindSafe};
use std::sync::atomic::{AtomicBool, AtomicIsize, Ordering};
use std::sync::mpsc::{self, SyncSender};
use std::sync::{Arc, Mutex, Once};
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::System::Threading::GetCurrentThreadId;
use windows::Win32::UI::WindowsAndMessaging::{
    CREATESTRUCTW, CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GWLP_USERDATA,
    GetMessageW, GetWindowLongPtrW, HWND_MESSAGE, MSG, PM_REMOVE, PeekMessageW, PostThreadMessageW,
    RegisterClassExW, SendMessageW, SetWindowLongPtrW, WINDOW_EX_STYLE, WINDOW_STYLE, WM_APP,
    WM_NCCREATE, WM_QUIT, WNDCLASSEXW,
};
use windows::core::{PCWSTR, w};

const CLASS_NAME: PCWSTR = w!("MargreteRpcUiMarshal");
const WM_DRAIN: u32 = WM_APP + 1;
const WM_SHUTDOWN: u32 = WM_APP + 2;

struct SendPtr(*mut ());

unsafe impl Send for SendPtr {}

struct Job {
    run: unsafe fn(*mut ()),
    data: SendPtr,
    done: SyncSender<()>,
}

struct Inner {
    hwnd: AtomicIsize,
    thread_id: u32,
    queue: Mutex<VecDeque<Job>>,
    draining: AtomicBool,
    shutting_down: AtomicBool,
}

/// Runs closures on the thread that created the dispatcher (Margrete's UI thread).
#[derive(Clone)]
pub struct UiDispatcher {
    inner: Arc<Inner>,
}

impl UiDispatcher {
    pub fn create() -> Result<Self> {
        register_class();
        let inner = Arc::new(Inner {
            hwnd: AtomicIsize::new(0),
            thread_id: unsafe { GetCurrentThreadId() },
            queue: Mutex::new(VecDeque::new()),
            draining: AtomicBool::new(false),
            shutting_down: AtomicBool::new(false),
        });
        let hwnd = unsafe {
            CreateWindowExW(
                WINDOW_EX_STYLE(0),
                CLASS_NAME,
                PCWSTR::null(),
                WINDOW_STYLE(0),
                0,
                0,
                0,
                0,
                Some(HWND_MESSAGE),
                None,
                Some(GetModuleHandleW(None).unwrap_or_default().into()),
                Some(Arc::as_ptr(&inner) as *const c_void),
            )
        }
        .map_err(|err| {
            PluginError::internal(format!("failed to create UI marshal window: {err}"))
        })?;
        inner.hwnd.store(hwnd.0 as isize, Ordering::SeqCst);
        log::info!("UI marshal window created thread={}", inner.thread_id);
        Ok(Self { inner })
    }

    pub fn thread_id(&self) -> u32 {
        self.inner.thread_id
    }

    pub fn call<R, F>(&self, f: F) -> Result<R>
    where
        R: Send,
        F: FnOnce() -> R + Send,
    {
        if self.inner.shutting_down.load(Ordering::SeqCst) {
            return Err(PluginError::unavailable(
                "Margrete UI thread is unavailable",
            ));
        }
        if self.is_owner_thread() || self.hwnd().0.is_null() {
            return Ok(f());
        }

        struct Data<F, R> {
            f: Option<F>,
            result: Option<R>,
            panic: Option<Box<dyn std::any::Any + Send>>,
        }

        let mut data = Data {
            f: Some(f),
            result: None,
            panic: None,
        };
        let (done_tx, done_rx) = mpsc::sync_channel(1);
        unsafe fn run<F: FnOnce() -> R, R>(ptr: *mut ()) {
            let data = unsafe { &mut *ptr.cast::<Data<F, R>>() };
            match panic::catch_unwind(AssertUnwindSafe(|| (data.f.take().unwrap())())) {
                Ok(value) => data.result = Some(value),
                Err(payload) => data.panic = Some(payload),
            }
        }
        self.inner.queue.lock().expect("ui marshal").push_back(Job {
            run: run::<F, R>,
            data: SendPtr(std::ptr::from_mut(&mut data).cast()),
            done: done_tx,
        });
        let _ = self.wake(WM_DRAIN);
        done_rx
            .recv()
            .map_err(|_| PluginError::unavailable("Margrete UI thread is unavailable"))?;
        if let Some(payload) = data.panic.take() {
            panic::resume_unwind(payload);
        }
        data.result
            .take()
            .ok_or_else(|| PluginError::unavailable("Margrete UI thread is unavailable"))
    }

    pub fn pump(&self) {
        let hwnd = self.hwnd();
        if hwnd.0.is_null() {
            return;
        }
        let mut msg = MSG::default();
        unsafe {
            while PeekMessageW(&mut msg, Some(hwnd), 0, 0, PM_REMOVE).as_bool() {
                let _ = DispatchMessageW(&msg);
            }
        }
    }

    pub fn shutdown(&self) {
        if self.inner.shutting_down.swap(true, Ordering::SeqCst) {
            return;
        }
        if self.is_owner_thread() {
            self.inner.shutdown_on_ui();
            return;
        }
        let _ = self.wake(WM_SHUTDOWN);
    }

    pub fn run_message_loop(&self) {
        let mut msg = MSG::default();
        unsafe {
            while GetMessageW(&mut msg, None, 0, 0).0 > 0 {
                let _ = DispatchMessageW(&msg);
            }
        }
    }

    pub fn quit_message_loop(&self) {
        unsafe {
            let _ = PostThreadMessageW(self.inner.thread_id, WM_QUIT, WPARAM(0), LPARAM(0));
        }
    }

    fn is_owner_thread(&self) -> bool {
        unsafe { GetCurrentThreadId() == self.inner.thread_id }
    }

    fn hwnd(&self) -> HWND {
        HWND(self.inner.hwnd.load(Ordering::SeqCst) as *mut c_void)
    }

    fn wake(&self, message: u32) -> Result<()> {
        let hwnd = self.hwnd();
        if hwnd.0.is_null() {
            return Err(PluginError::unavailable(
                "Margrete UI thread is unavailable",
            ));
        }
        unsafe {
            SendMessageW(hwnd, message, Some(WPARAM(0)), Some(LPARAM(0)));
        }
        Ok(())
    }
}

impl Inner {
    fn drain(&self) {
        if self.draining.swap(true, Ordering::SeqCst) {
            return;
        }
        loop {
            while let Some(job) = self.queue.lock().expect("ui marshal").pop_front() {
                unsafe {
                    (job.run)(job.data.0);
                }
                let _ = job.done.send(());
            }
            self.draining.store(false, Ordering::SeqCst);
            if self.queue.lock().expect("ui marshal").is_empty() {
                break;
            }
            if self.draining.swap(true, Ordering::SeqCst) {
                break;
            }
        }
    }

    fn shutdown_on_ui(&self) {
        self.shutting_down.store(true, Ordering::SeqCst);
        while let Some(job) = self.queue.lock().expect("ui marshal").pop_front() {
            let _ = job.done.send(());
        }
        let hwnd = HWND(self.hwnd.load(Ordering::SeqCst) as *mut c_void);
        self.hwnd.store(0, Ordering::SeqCst);
        if !hwnd.0.is_null() {
            unsafe {
                let _ = SetWindowLongPtrW(hwnd, GWLP_USERDATA, 0);
                let _ = DestroyWindow(hwnd);
            }
        }
        log::info!("UI marshal window destroyed");
    }
}

unsafe impl Send for Inner {}
unsafe impl Sync for Inner {}

fn register_class() {
    static REGISTERED: Once = Once::new();
    REGISTERED.call_once(|| unsafe {
        let instance = GetModuleHandleW(None).unwrap_or_default();
        let class = WNDCLASSEXW {
            cbSize: std::mem::size_of::<WNDCLASSEXW>() as u32,
            lpfnWndProc: Some(window_proc),
            hInstance: instance.into(),
            lpszClassName: CLASS_NAME,
            ..Default::default()
        };
        let _ = RegisterClassExW(&class);
    });
}

unsafe extern "system" fn window_proc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    unsafe {
        if message == WM_NCCREATE {
            let create = &*(lparam.0 as *const CREATESTRUCTW);
            let _ = SetWindowLongPtrW(hwnd, GWLP_USERDATA, create.lpCreateParams as isize);
        }
        let inner = GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *const Inner;
        if inner.is_null() {
            return DefWindowProcW(hwnd, message, wparam, lparam);
        }
        match message {
            WM_DRAIN => {
                (*inner).drain();
                LRESULT(0)
            }
            WM_SHUTDOWN => {
                (*inner).shutdown_on_ui();
                LRESULT(0)
            }
            _ => DefWindowProcW(hwnd, message, wparam, lparam),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicU32;
    use std::thread;
    use std::time::Duration;

    fn with_dispatcher<F>(f: F)
    where
        F: FnOnce(UiDispatcher) + Send,
    {
        let (tx, rx) = mpsc::channel();
        thread::scope(|scope| {
            scope.spawn(|| {
                let dispatcher = UiDispatcher::create().expect("create marshal");
                tx.send(dispatcher.clone()).expect("send dispatcher");
                dispatcher.run_message_loop();
            });
            let dispatcher = rx.recv().expect("dispatcher");
            f(dispatcher.clone());
            dispatcher.shutdown();
            dispatcher.quit_message_loop();
        });
    }

    #[test]
    fn call_from_another_thread_runs_on_owner_thread() {
        with_dispatcher(|dispatcher| {
            let owner = dispatcher.thread_id();
            let ran_on = dispatcher
                .call(|| unsafe { GetCurrentThreadId() })
                .expect("call");
            assert_eq!(ran_on, owner);
            assert_ne!(ran_on, unsafe { GetCurrentThreadId() });
        });
    }

    #[test]
    fn concurrent_calls_do_not_overlap_on_the_ui_thread() {
        with_dispatcher(|dispatcher| {
            let busy = Arc::new(AtomicBool::new(false));
            let overlapped = Arc::new(AtomicBool::new(false));
            let completed = Arc::new(AtomicU32::new(0));
            thread::scope(|scope| {
                for _ in 0..8 {
                    let dispatcher = dispatcher.clone();
                    let busy = Arc::clone(&busy);
                    let overlapped = Arc::clone(&overlapped);
                    let completed = Arc::clone(&completed);
                    scope.spawn(move || {
                        dispatcher
                            .call(|| {
                                if busy.swap(true, Ordering::SeqCst) {
                                    overlapped.store(true, Ordering::SeqCst);
                                }
                                thread::sleep(Duration::from_millis(5));
                                busy.store(false, Ordering::SeqCst);
                                completed.fetch_add(1, Ordering::SeqCst);
                            })
                            .expect("call");
                    });
                }
            });
            assert!(!overlapped.load(Ordering::SeqCst));
            assert_eq!(completed.load(Ordering::SeqCst), 8);
        });
    }

    #[test]
    fn owner_thread_runs_inline() {
        let dispatcher = UiDispatcher::create().expect("create marshal");
        let owner = dispatcher.thread_id();
        let ran_on = dispatcher
            .call(|| unsafe { GetCurrentThreadId() })
            .expect("inline");
        assert_eq!(ran_on, owner);
        dispatcher.shutdown();
    }
}
