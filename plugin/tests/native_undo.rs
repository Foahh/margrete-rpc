mod common;

use common::fake::{FakeContext, FakeNote};
use margrete_rpc::abi::MP_FALSE;
use margrete_rpc::chart::session::MargreteSession;
use margrete_rpc::chart::transaction::apply_edit;
use margrete_rpc::rpc::proto::{ApplyEditRequest, Note, NoteType};
use margrete_rpc::ui::undo::NativeUndoGuard;
use std::cell::RefCell;
use std::sync::Once;
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::UI::WindowsAndMessaging::*;
use windows::core::w;

const UNDO: usize = 0xE12B;
const REDO: usize = 0xE12C;

fn assert_roots(actual: &[*mut FakeNote], expected: &[*mut FakeNote]) {
    let mut actual = actual.to_vec();
    let mut expected = expected.to_vec();
    actual.sort_unstable();
    expected.sort_unstable();
    assert_eq!(actual, expected);
}

struct Host {
    context: FakeContext,
    before: Vec<*mut FakeNote>,
    after: Vec<*mut FakeNote>,
    guard: RefCell<Option<NativeUndoGuard>>,
    release_during_command: bool,
    destroy_during_command: bool,
    simulate_history: bool,
}

struct Window {
    hwnd: HWND,
    host: Box<Host>,
}

impl Window {
    fn new() -> Self {
        let mut context = FakeContext::new();
        context.chart.add_existing_note(10);
        context.chart.add_existing_note(11); // Same contents, different ID: keep it.
        let before = context.chart.notes.clone();
        let session = MargreteSession::new(context.as_ptr()).unwrap();
        apply_edit(
            &session,
            &ApplyEditRequest {
                note_ids_delete: vec![10],
                notes_upsert: vec![Note {
                    r#type: NoteType::Aircrush as i32,
                    children: (1..=4)
                        .map(|tick| Note {
                            tick,
                            r#type: NoteType::Aircrush as i32,
                            ..Default::default()
                        })
                        .collect(),
                    ..Default::default()
                }],
                ..Default::default()
            },
        )
        .unwrap();
        drop(session);
        let after = context.chart.notes.clone();
        let mut host = Box::new(Host {
            context,
            before,
            after,
            guard: RefCell::new(None),
            release_during_command: false,
            destroy_during_command: false,
            simulate_history: true,
        });
        static REGISTER: Once = Once::new();
        let instance = unsafe { GetModuleHandleW(None).unwrap() };
        REGISTER.call_once(|| unsafe {
            assert_ne!(
                RegisterClassW(&WNDCLASSW {
                    lpfnWndProc: Some(host_proc),
                    hInstance: instance.into(),
                    lpszClassName: w!("MargreteRpcNativeUndoTest"),
                    ..Default::default()
                }),
                0
            );
        });
        let hwnd = unsafe {
            CreateWindowExW(
                WINDOW_EX_STYLE::default(),
                w!("MargreteRpcNativeUndoTest"),
                w!(""),
                WINDOW_STYLE::default(),
                0,
                0,
                0,
                0,
                None,
                None,
                Some(instance.into()),
                Some((&mut *host as *mut Host).cast()),
            )
            .unwrap()
        };
        host.context.set_main_window(hwnd.0);
        *host.guard.borrow_mut() = Some(NativeUndoGuard::install(host.context.as_ptr()).unwrap());
        Self { hwnd, host }
    }

    fn command(&self, command: usize, lparam: isize) -> LRESULT {
        unsafe {
            SendMessageW(
                self.hwnd,
                WM_COMMAND,
                Some(WPARAM(command)),
                Some(LPARAM(lparam)),
            )
        }
    }
}

impl Drop for Window {
    fn drop(&mut self) {
        unsafe {
            let _ = DestroyWindow(self.hwnd);
        }
    }
}

unsafe extern "system" fn host_proc(hwnd: HWND, msg: u32, wp: WPARAM, lp: LPARAM) -> LRESULT {
    unsafe {
        if msg == WM_NCCREATE {
            let create = &*(lp.0 as *const CREATESTRUCTW);
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, create.lpCreateParams as isize);
        }
        let ptr = GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *mut Host;
        if msg == WM_COMMAND && !ptr.is_null() {
            let host = &mut *ptr;
            if host.release_during_command {
                host.guard.borrow_mut().take();
            }
            if host.destroy_during_command {
                let _ = DestroyWindow(hwnd);
            }
            if host.simulate_history {
                match wp.0 & 0xffff {
                    UNDO => {
                        host.context.chart.notes = host.before.clone();
                        // Model the two SDK delete records restoring the same object.
                        host.context.chart.notes.push(host.before[0]);
                    }
                    REDO => host.context.chart.notes = host.after.clone(),
                    _ => {}
                }
            }
            return LRESULT(77);
        }
        DefWindowProcW(hwnd, msg, wp, lp)
    }
}

#[test]
fn native_menu_and_accelerator_undo_redo_repair_sdk_duplicates() {
    let window = Window::new();
    for source in [0, 1 << 16, 0, 1 << 16] {
        assert_eq!(window.command(UNDO | source, 0), LRESULT(77));
        assert_roots(&window.host.context.chart.notes, &window.host.before);
        assert_eq!(window.command(REDO | source, 0), LRESULT(77));
        assert_roots(&window.host.context.chart.notes, &window.host.after);
    }
    // Repair is not an extra undoable edit and does not consume history itself.
    assert_eq!(window.host.context.undo.begin_count, 1);
    assert_eq!(window.host.context.undo.undo_count, 0);
    assert_eq!(window.host.context.undo.redo_count, 0);
}

#[test]
fn unrelated_commands_and_control_notifications_do_not_repair() {
    let mut window = Window::new();
    window.host.simulate_history = false;
    window.host.context.chart.notes.push(window.host.before[1]);
    let before = window.host.context.chart.notes.clone();
    for (command, lparam) in [(0xE122, 0), (UNDO, 1), (UNDO | 2 << 16, 0)] {
        assert_eq!(window.command(command, lparam), LRESULT(77));
        assert_eq!(window.host.context.chart.notes, before);
    }
}

#[test]
fn active_recording_is_not_modified_by_native_repair() {
    let window = Window::new();
    let session = MargreteSession::new(window.host.context.as_ptr()).unwrap();
    session.undo_buffer().begin_recording().unwrap();
    window.command(UNDO, 0);
    assert_eq!(window.host.context.chart.notes.len(), 3);
    session.undo_buffer().commit_recording().unwrap();
    window.command(UNDO, 0);
    assert_roots(&window.host.context.chart.notes, &window.host.before);
}

#[test]
fn releasing_guard_during_forwarding_is_safe_and_detaches() {
    let mut window = Window::new();
    window.host.release_during_command = true;
    assert_eq!(window.command(UNDO, 0), LRESULT(77));
    assert_eq!(window.host.context.ref_count_value(), 1);
    assert_eq!(window.host.context.chart.notes.len(), 3);
    assert_eq!(window.command(REDO, 0), LRESULT(77));
}

#[test]
fn destroying_host_during_forwarding_is_safe() {
    let mut window = Window::new();
    window.host.destroy_during_command = true;
    assert_eq!(window.command(UNDO, 0), LRESULT(77));
    window.host.guard.borrow_mut().take();
    assert_eq!(window.host.context.ref_count_value(), 1);
}

#[test]
fn repair_failure_does_not_swallow_host_command_result() {
    let mut window = Window::new();
    window.host.context.chart.delete_note_result = MP_FALSE;
    assert_eq!(window.command(UNDO, 0), LRESULT(77));
    assert_eq!(window.host.context.chart.notes.len(), 3);
    assert_eq!(window.host.context.undo.begin_count, 1);
}

#[test]
fn sdk_view_context_observes_frame_commands_and_detaches_when_view_closes() {
    let mut window = Window::new();
    window.host.guard.borrow_mut().take();
    let child = unsafe {
        CreateWindowExW(
            WINDOW_EX_STYLE::default(),
            w!("STATIC"),
            w!(""),
            WS_CHILD,
            0,
            0,
            0,
            0,
            Some(window.hwnd),
            None,
            None,
            None,
        )
        .unwrap()
    };
    window.host.context.set_main_window(child.0);
    *window.host.guard.borrow_mut() =
        Some(NativeUndoGuard::install(window.host.context.as_ptr()).unwrap());
    assert_eq!(window.command(UNDO | 1 << 16, 0), LRESULT(77));
    assert_roots(&window.host.context.chart.notes, &window.host.before);
    unsafe {
        DestroyWindow(child).unwrap();
    }
    window.command(UNDO, 0);
    assert_eq!(window.host.context.chart.notes.len(), 3);
    window.host.guard.borrow_mut().take();
    assert_eq!(window.host.context.ref_count_value(), 1);
}

#[test]
fn replacing_guard_does_not_detach_new_registration() {
    let window = Window::new();
    let replacement = NativeUndoGuard::install(window.host.context.as_ptr()).unwrap();
    *window.host.guard.borrow_mut() = Some(replacement);
    assert_eq!(window.host.context.ref_count_value(), 2);
    window.command(UNDO, 0);
    assert_roots(&window.host.context.chart.notes, &window.host.before);
}
