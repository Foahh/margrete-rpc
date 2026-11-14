use crate::abi::{ComPtr, Context};
use crate::chart::deduper::deduplicate;
use crate::chart::session::MargreteSession;
use crate::error::{PluginError, Result};
use std::cell::Cell;
use std::rc::Rc;
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::System::Threading::GetCurrentThreadId;
use windows::Win32::UI::Shell::{DefSubclassProc, RemoveWindowSubclass, SetWindowSubclass};
use windows::Win32::UI::WindowsAndMessaging::{
    GA_ROOT, GetAncestor, GetWindowThreadProcessId, WM_COMMAND, WM_NCDESTROY,
};

// MFC's menu, ribbon and accelerator commands (afxres.h).
const ID_EDIT_UNDO: usize = 0xE12B;
const ID_EDIT_REDO: usize = 0xE12C;

struct State {
    windows: [HWND; 2],
    attached: Cell<bool>,
    context: ComPtr<Context>,
}

impl State {
    fn detach(&self) {
        if self.attached.replace(false) {
            for hwnd in self.windows {
                unsafe {
                    let _ =
                        RemoveWindowSubclass(hwnd, Some(window_proc), self as *const _ as usize);
                }
            }
        }
    }
}

/// Repairs the duplicate roots produced by Margrete's SDK delete undo records.
/// Keep this alive after the RPC server stops: its edits remain in host history.
pub struct NativeUndoGuard(Rc<State>);

impl NativeUndoGuard {
    /// Install on the host UI thread; the context must remain a valid SDK interface.
    pub fn install(context: *mut Context) -> Result<Self> {
        if context.is_null() {
            return Err(PluginError::internal("undo guard requires a context"));
        }
        let hwnd = HWND(unsafe { (*context).main_window_handle() });
        if hwnd.is_invalid()
            || unsafe { GetWindowThreadProcessId(hwnd, None) != GetCurrentThreadId() }
        {
            return Err(PluginError::internal(
                "undo guard requires the host UI thread",
            ));
        }
        let state = Rc::new(State {
            // MFC routes frame commands directly to the view's OnCmdMsg. The SDK
            // can return a view HWND, so observing only that HWND misses Ctrl+Z.
            windows: [hwnd, unsafe { GetAncestor(hwnd, GA_ROOT) }],
            attached: Cell::new(true),
            context: unsafe { ComPtr::retain(context) },
        });
        let id = Rc::as_ptr(&state) as usize;
        for hwnd in state.windows {
            if !unsafe { SetWindowSubclass(hwnd, Some(window_proc), id, id) }.as_bool() {
                state.detach();
                return Err(PluginError::internal("failed to install native undo guard"));
            }
        }
        Ok(Self(state))
    }
}

impl Drop for NativeUndoGuard {
    fn drop(&mut self) {
        self.0.detach();
    }
}

unsafe extern "system" fn window_proc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
    _id: usize,
    data: usize,
) -> LRESULT {
    // The host may destroy its window or release the plugin while forwarding.
    let state = unsafe {
        let ptr = data as *const State;
        Rc::increment_strong_count(ptr);
        Rc::from_raw(ptr)
    };
    if message == WM_NCDESTROY {
        state.detach();
    }
    let history_command = message == WM_COMMAND
        && lparam.0 == 0
        && wparam.0 >> 16 <= 1
        && matches!(wparam.0 & 0xffff, ID_EDIT_UNDO | ID_EDIT_REDO);
    let session = history_command
        .then(|| MargreteSession::new(state.context.as_ptr()).ok())
        .flatten();
    let result = unsafe { DefSubclassProc(hwnd, message, wparam, lparam) };
    if state.attached.get()
        && let Some(session) = session
        && !session.undo_buffer().is_recording()
    {
        match deduplicate(session.chart()) {
            Ok(0) => {}
            Ok(removed) => {
                log::info!("native undo/redo removed {removed} duplicate roots");
                session.update();
            }
            Err(err) => {
                log::error!("native undo/redo repair failed: {err}");
                session.update();
            }
        }
    }
    result
}
