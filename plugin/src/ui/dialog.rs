use crate::abi::Context;
use crate::meta;
use crate::server::{ServerController, ServerControllerStatus};
use crate::wide::{clone_pcwstr, path_to_wide_null, str_to_wide, str_to_wide_null};
use std::ffi::c_void;
use windows::Win32::Foundation::{COLORREF, HWND, LPARAM, LRESULT, RECT, SIZE, WPARAM};
use windows::Win32::Graphics::Gdi::{
    CreateFontIndirectW, CreateSolidBrush, DeleteObject, FW_NORMAL, FW_SEMIBOLD, FillRect, GetDC,
    GetDeviceCaps, GetTextExtentPoint32W, HBRUSH, HDC, HFONT, InvalidateRect, LOGFONTW, LOGPIXELSY,
    ReleaseDC, SelectObject, SetBkColor, SetTextColor, UpdateWindow,
};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::System::SystemServices::{SS_CENTERIMAGE, SS_LEFT, SS_NOPREFIX};
use windows::Win32::System::WindowsProgramming::MulDiv;
use windows::Win32::UI::Controls::{
    ICC_STANDARD_CLASSES, INITCOMMONCONTROLSEX, InitCommonControlsEx,
};
use windows::Win32::UI::Input::KeyboardAndMouse::{EnableWindow, SetActiveWindow};
use windows::Win32::UI::Shell::ShellExecuteW;
use windows::Win32::UI::WindowsAndMessaging::{
    AdjustWindowRectEx, BS_PUSHBUTTON, CREATESTRUCTW, CW_USEDEFAULT, CreateWindowExW,
    DefWindowProcW, DestroyWindow, DispatchMessageW, ES_AUTOHSCROLL, ES_AUTOVSCROLL, ES_MULTILINE,
    ES_NOHIDESEL, ES_READONLY, GWL_EXSTYLE, GWL_STYLE, GWLP_USERDATA, GetClientRect, GetMessageW,
    GetSystemMetrics, GetWindowLongPtrW, GetWindowTextLengthW, GetWindowTextW, HMENU, IDC_ARROW,
    IsDialogMessageW, IsWindow, KillTimer, LoadCursorW, MSG, NONCLIENTMETRICSW, RegisterClassExW,
    SM_CXPADDEDBORDER, SM_CXSIZE, SM_CXSMICON, SPI_GETNONCLIENTMETRICS, SW_HIDE, SW_SHOW,
    SW_SHOWNORMAL, SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOZORDER, SYSTEM_PARAMETERS_INFO_UPDATE_FLAGS,
    SendMessageW, SetTimer, SetWindowLongPtrW, SetWindowPos, SetWindowTextW, ShowWindow,
    SystemParametersInfoW, TranslateMessage, WINDOW_EX_STYLE, WINDOW_STYLE, WM_CLOSE, WM_COMMAND,
    WM_CREATE, WM_CTLCOLORSTATIC, WM_DESTROY, WM_ERASEBKGND, WM_NCCREATE, WM_SETFONT, WM_TIMER,
    WNDCLASSEXW, WS_CAPTION, WS_CHILD, WS_EX_CLIENTEDGE, WS_EX_DLGMODALFRAME, WS_SYSMENU,
    WS_TABSTOP, WS_VISIBLE, WS_VSCROLL,
};
use windows::core::{PCWSTR, w};

const CLASS_NAME: PCWSTR = w!("MargreteRpcServerStatusWindow");
const REFRESH_TIMER_ID: usize = 1;
const REFRESH_INTERVAL_MS: u32 = 1000;
const START_STOP_ID: i32 = 1001;
const OPEN_LOG_ID: i32 = 1004;
const CONTROL_HEIGHT: i32 = 30;
const SECTION_HEIGHT: i32 = 28;
const ERROR_HEIGHT: i32 = 56;
const PADDING: i32 = 20;
const TOP_PADDING: i32 = 12;
const ROW_GAP: i32 = 8;
const SECTION_GAP: i32 = 14;
const LABEL_WIDTH: i32 = 36;
const ID_VALUE_WIDTH: i32 = 64;
const BUTTON_WIDTH: i32 = 95;

struct ServerStatusWindow {
    context: *mut Context,
    controller: *const ServerController,
    config_error: String,
    hwnd: HWND,
    parent: HWND,
    instance_value: HWND,
    log_label: HWND,
    log_value: HWND,
    error_label: HWND,
    error_value: HWND,
    start_stop: HWND,
    open_log: HWND,
    font: HFONT,
    bold_font: HFONT,
    background: HBRUSH,
    normal_height: i32,
    message_height: i32,
    message_visible: bool,
    log_visible: bool,
    log_path_text: Vec<u16>,
}

pub fn show_server_status_dialog(
    context: *mut Context,
    controller: &ServerController,
    config_error: String,
) {
    unsafe {
        let cc = INITCOMMONCONTROLSEX {
            dwSize: std::mem::size_of::<INITCOMMONCONTROLSEX>() as u32,
            dwICC: ICC_STANDARD_CLASSES,
        };
        let _ = InitCommonControlsEx(&cc);
    }
    let mut window = ServerStatusWindow::new(context, controller, config_error);
    window.show_modal();
}

impl ServerStatusWindow {
    fn new(context: *mut Context, controller: &ServerController, config_error: String) -> Self {
        let parent = if context.is_null() {
            HWND::default()
        } else {
            HWND(unsafe { (*context).main_window_handle() })
        };
        Self {
            context,
            controller: controller as *const ServerController,
            config_error,
            hwnd: HWND::default(),
            parent,
            instance_value: HWND::default(),
            log_label: HWND::default(),
            log_value: HWND::default(),
            error_label: HWND::default(),
            error_value: HWND::default(),
            start_stop: HWND::default(),
            open_log: HWND::default(),
            font: create_message_font(0, FW_NORMAL.0 as i32),
            bold_font: create_message_font(0, FW_SEMIBOLD.0 as i32),
            background: unsafe { CreateSolidBrush(COLORREF(0x00F8F8F8)) },
            normal_height: 0,
            message_height: 0,
            message_visible: true,
            log_visible: true,
            log_path_text: Vec::new(),
        }
    }

    fn show_modal(&mut self) {
        unsafe {
            ensure_window_class();
            let title = str_to_wide_null(meta::DIALOG_TITLE);
            let style = WS_CAPTION | WS_SYSMENU;
            let ex = WS_EX_DLGMODALFRAME;
            let (width, height) = outer_size_for_client(client_width(), 80, style, ex);
            let hwnd = CreateWindowExW(
                ex,
                CLASS_NAME,
                PCWSTR(title.as_ptr()),
                style,
                CW_USEDEFAULT,
                CW_USEDEFAULT,
                width,
                height,
                Some(self.parent),
                Some(HMENU::default()),
                Some(GetModuleHandleW(None).unwrap_or_default().into()),
                Some(self as *mut Self as *const c_void),
            )
            .unwrap_or_default();
            if hwnd.0.is_null() {
                return;
            }
            if !self.parent.0.is_null() {
                let _ = EnableWindow(self.parent, false);
            }
            let _ = ShowWindow(hwnd, SW_SHOW);
            let _ = UpdateWindow(hwnd);
            let mut msg = MSG::default();
            while IsWindow(Some(hwnd)).as_bool() && GetMessageW(&mut msg, None, 0, 0).0 > 0 {
                if !IsDialogMessageW(hwnd, &msg).as_bool() {
                    let _ = TranslateMessage(&msg);
                    let _ = DispatchMessageW(&msg);
                }
            }
            if !self.parent.0.is_null() {
                let _ = EnableWindow(self.parent, true);
                let _ = SetActiveWindow(self.parent);
            }
        }
    }

    fn create_controls(&mut self) {
        let label_x = PADDING;
        let label_width = LABEL_WIDTH;
        let value_x = label_x + label_width + ROW_GAP;
        let button_width = BUTTON_WIDTH;
        let action_x = client_width() - PADDING - button_width;
        let value_width = action_x - ROW_GAP - value_x;
        let mut y = TOP_PADDING;
        add_label(
            self.hwnd,
            w!("ID"),
            label_x,
            y,
            label_width,
            CONTROL_HEIGHT,
            self.font,
        );
        self.instance_value = add_value(
            self.hwnd,
            value_x,
            y,
            value_width,
            CONTROL_HEIGHT,
            self.font,
        );
        self.start_stop = add_button(
            self.hwnd,
            w!(""),
            START_STOP_ID,
            action_x,
            y,
            button_width,
            CONTROL_HEIGHT,
            self.font,
        );
        y += CONTROL_HEIGHT + ROW_GAP;
        self.log_label = add_label(
            self.hwnd,
            w!("Log"),
            label_x,
            y,
            label_width,
            CONTROL_HEIGHT,
            self.font,
        );
        self.log_value = add_value(
            self.hwnd,
            value_x,
            y,
            value_width,
            CONTROL_HEIGHT,
            self.font,
        );
        self.open_log = add_button(
            self.hwnd,
            w!("Open"),
            OPEN_LOG_ID,
            action_x,
            y,
            button_width,
            CONTROL_HEIGHT,
            self.font,
        );
        y += CONTROL_HEIGHT;
        self.normal_height = y + PADDING;
        y += SECTION_GAP;
        self.error_label = add_label(
            self.hwnd,
            w!("Config reload failed"),
            label_x,
            y,
            180,
            SECTION_HEIGHT,
            self.bold_font,
        );
        y += SECTION_HEIGHT + ROW_GAP;
        self.error_value = add_control(
            self.hwnd,
            w!("EDIT"),
            w!(""),
            ES_MULTILINE as u32 | ES_READONLY as u32 | ES_AUTOVSCROLL as u32 | WS_VSCROLL.0,
            WS_EX_CLIENTEDGE,
            0,
            label_x,
            y,
            client_width() - PADDING * 2,
            ERROR_HEIGHT,
            self.font,
        );
        self.message_height = y + ERROR_HEIGHT + PADDING;
    }

    fn refresh(&mut self) {
        let Some(controller) = (unsafe { self.controller.as_ref() }) else {
            return;
        };
        let status = controller.status();
        let log_path = if status.loaded_config.logging && !status.log_path.as_os_str().is_empty() {
            Some(path_to_wide_null(&status.log_path))
        } else {
            None
        };
        set_text_if_changed(
            self.start_stop,
            if status.running {
                w!("Stop")
            } else {
                w!("Start")
            },
        );
        set_text_wide_if_changed(self.instance_value, &str_to_wide_null(&status.instance_id));
        self.update_log_visibility(log_path.is_some());
        if let Some(log_path) = log_path {
            set_text_wide_if_changed(self.log_value, &log_path);
            self.log_path_text = log_path;
        } else {
            self.log_path_text = Vec::new();
        }
        unsafe {
            let _ = EnableWindow(self.open_log, self.log_visible);
        }
        let pending = active_config_differs(&status);
        let has_message = !self.config_error.is_empty() || pending;
        self.update_message_visibility(has_message);
        if !self.config_error.is_empty() {
            set_text_if_changed(self.error_label, w!("Config reload failed"));
            set_text_wide_if_changed(self.error_value, &str_to_wide_null(&self.config_error));
        } else if pending {
            set_text_if_changed(self.error_label, w!("Config changes pending"));
            set_text_if_changed(
                self.error_value,
                w!("Loaded config differs from the running server. Restart to apply."),
            );
        } else {
            set_text_if_changed(self.error_value, w!(""));
        }
        unsafe {
            let _ = InvalidateRect(Some(self.error_label), None, true);
        }
    }

    fn update_log_visibility(&mut self, visible: bool) {
        if self.log_visible == visible {
            return;
        }
        self.log_visible = visible;
        unsafe {
            let cmd = if visible { SW_SHOW } else { SW_HIDE };
            let _ = ShowWindow(self.log_label, cmd);
            let _ = ShowWindow(self.log_value, cmd);
            let _ = ShowWindow(self.open_log, cmd);
        }
        self.relayout_below_rows();
    }

    fn content_bottom(&self) -> i32 {
        let mut y = TOP_PADDING + CONTROL_HEIGHT;
        if self.log_visible {
            y += ROW_GAP + CONTROL_HEIGHT;
        }
        y
    }

    fn relayout_below_rows(&mut self) {
        let mut y = self.content_bottom();
        self.normal_height = y + PADDING;
        y += SECTION_GAP;
        move_control(self.error_label, PADDING, y, 180, SECTION_HEIGHT);
        y += SECTION_HEIGHT + ROW_GAP;
        move_control(
            self.error_value,
            PADDING,
            y,
            client_width() - PADDING * 2,
            ERROR_HEIGHT,
        );
        self.message_height = y + ERROR_HEIGHT + PADDING;
    }

    fn update_message_visibility(&mut self, visible: bool) {
        if self.message_visible != visible {
            unsafe {
                let _ = ShowWindow(self.error_label, if visible { SW_SHOW } else { SW_HIDE });
                let _ = ShowWindow(self.error_value, if visible { SW_SHOW } else { SW_HIDE });
            }
            self.message_visible = visible;
        }
        self.resize_to_client_height(if visible {
            self.message_height
        } else {
            self.normal_height
        });
    }

    fn resize_to_client_height(&self, client_height: i32) {
        let mut client = RECT::default();
        unsafe {
            let _ = GetClientRect(self.hwnd, &mut client);
        }
        if client.right == client_width() && client.bottom == client_height {
            return;
        }
        unsafe {
            let style = WINDOW_STYLE(GetWindowLongPtrW(self.hwnd, GWL_STYLE) as u32);
            let ex = WINDOW_EX_STYLE(GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE) as u32);
            let (width, height) = outer_size_for_client(client_width(), client_height, style, ex);
            let _ = SetWindowPos(
                self.hwnd,
                None,
                0,
                0,
                width,
                height,
                SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE,
            );
        }
    }

    fn toggle_server(&mut self) {
        let Some(controller) = (unsafe { self.controller.as_ref() }) else {
            return;
        };
        self.config_error.clear();
        if controller.running() {
            controller.stop();
            self.refresh();
            return;
        }
        match crate::server::config::load_server_config(
            controller.status().loaded_config.source_path.clone(),
        ) {
            Ok(config) => controller.set_config(config),
            Err(err) => self.config_error = err.to_string(),
        }
        if self.config_error.is_empty() {
            controller.start(self.context);
        }
        self.refresh();
    }

    fn open_path(&self, path: &[u16]) {
        if path.is_empty() {
            return;
        }
        unsafe {
            let _ = ShellExecuteW(
                Some(self.hwnd),
                w!("open"),
                PCWSTR(path.as_ptr()),
                None,
                None,
                SW_SHOWNORMAL,
            );
        }
    }

    fn handle_command(&mut self, wparam: WPARAM) {
        match (wparam.0 & 0xffff) as i32 {
            START_STOP_ID => self.toggle_server(),
            OPEN_LOG_ID => self.open_path(&self.log_path_text),
            _ => {}
        }
    }

    fn handle_message(&mut self, message: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        match message {
            WM_CREATE => {
                self.create_controls();
                unsafe {
                    let _ = SetTimer(Some(self.hwnd), REFRESH_TIMER_ID, REFRESH_INTERVAL_MS, None);
                }
                self.refresh();
                LRESULT(0)
            }
            WM_TIMER if wparam.0 == REFRESH_TIMER_ID => {
                self.refresh();
                LRESULT(0)
            }
            WM_COMMAND => {
                self.handle_command(wparam);
                LRESULT(0)
            }
            WM_CTLCOLORSTATIC => {
                let hdc = HDC(wparam.0 as *mut c_void);
                unsafe {
                    if HWND(lparam.0 as *mut c_void) == self.error_label {
                        let _ = SetTextColor(hdc, COLORREF(0x002346A5));
                    }
                    let _ = SetBkColor(hdc, COLORREF(0x00F8F8F8));
                }
                LRESULT(self.background.0 as isize)
            }
            WM_ERASEBKGND => {
                let mut rect = RECT::default();
                unsafe {
                    let _ = GetClientRect(self.hwnd, &mut rect);
                    let _ = FillRect(HDC(wparam.0 as *mut c_void), &rect, self.background);
                }
                LRESULT(1)
            }
            WM_CLOSE => {
                unsafe {
                    let _ = DestroyWindow(self.hwnd);
                }
                LRESULT(0)
            }
            WM_DESTROY => {
                unsafe {
                    let _ = KillTimer(Some(self.hwnd), REFRESH_TIMER_ID);
                }
                self.hwnd = HWND::default();
                LRESULT(0)
            }
            _ => unsafe { DefWindowProcW(self.hwnd, message, wparam, lparam) },
        }
    }
}

impl Drop for ServerStatusWindow {
    fn drop(&mut self) {
        unsafe {
            if !self.background.is_invalid() {
                let _ = DeleteObject(self.background.into());
            }
            if !self.bold_font.is_invalid() {
                let _ = DeleteObject(self.bold_font.into());
            }
            if !self.font.is_invalid() {
                let _ = DeleteObject(self.font.into());
            }
        }
    }
}

unsafe extern "system" fn window_proc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    unsafe {
        let window = if message == WM_NCCREATE {
            let create = &*(lparam.0 as *const CREATESTRUCTW);
            let window = create.lpCreateParams as *mut ServerStatusWindow;
            (*window).hwnd = hwnd;
            let _ = SetWindowLongPtrW(hwnd, GWLP_USERDATA, window as isize);
            window
        } else {
            GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *mut ServerStatusWindow
        };
        if window.is_null() {
            return DefWindowProcW(hwnd, message, wparam, lparam);
        }
        (*window).handle_message(message, wparam, lparam)
    }
}

fn ensure_window_class() {
    static REGISTERED: std::sync::Once = std::sync::Once::new();
    REGISTERED.call_once(|| unsafe {
        let instance = GetModuleHandleW(None).unwrap_or_default();
        let wc = WNDCLASSEXW {
            cbSize: std::mem::size_of::<WNDCLASSEXW>() as u32,
            lpfnWndProc: Some(window_proc),
            hInstance: instance.into(),
            hCursor: LoadCursorW(None, IDC_ARROW).unwrap_or_default(),
            hbrBackground: HBRUSH((COLORREF(0).0 as isize + 1) as *mut c_void),
            lpszClassName: CLASS_NAME,
            ..Default::default()
        };
        let _ = RegisterClassExW(&wc);
    });
}

fn create_message_font(point_delta: i32, weight: i32) -> HFONT {
    unsafe {
        let mut metrics = NONCLIENTMETRICSW {
            cbSize: std::mem::size_of::<NONCLIENTMETRICSW>() as u32,
            ..Default::default()
        };
        if SystemParametersInfoW(
            SPI_GETNONCLIENTMETRICS,
            metrics.cbSize,
            Some(&mut metrics as *mut _ as *mut c_void),
            SYSTEM_PARAMETERS_INFO_UPDATE_FLAGS(0),
        )
        .is_err()
        {
            return HFONT::default();
        }
        let mut font: LOGFONTW = metrics.lfMessageFont;
        font.lfWeight = weight;
        if point_delta != 0 {
            let dc = GetDC(None);
            let dpi = if !dc.0.is_null() {
                GetDeviceCaps(Some(dc), LOGPIXELSY)
            } else {
                96
            };
            if !dc.0.is_null() {
                let _ = ReleaseDC(None, dc);
            }
            let current_points = MulDiv(-font.lfHeight, 72, dpi);
            font.lfHeight = -MulDiv(current_points + point_delta, dpi, 72);
        }
        CreateFontIndirectW(&font)
    }
}

fn add_control(
    parent: HWND,
    class: PCWSTR,
    text: PCWSTR,
    style: u32,
    ex: WINDOW_EX_STYLE,
    id: i32,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    font: HFONT,
) -> HWND {
    unsafe {
        let hwnd = CreateWindowExW(
            ex,
            class,
            text,
            WS_CHILD | WS_VISIBLE | WINDOW_STYLE(style),
            x,
            y,
            width,
            height,
            Some(parent),
            Some(HMENU(id as isize as *mut c_void)),
            Some(GetModuleHandleW(None).unwrap_or_default().into()),
            None,
        )
        .unwrap_or_default();
        if !font.is_invalid() {
            SendMessageW(
                hwnd,
                WM_SETFONT,
                Some(WPARAM(font.0 as usize)),
                Some(LPARAM(1)),
            );
        }
        hwnd
    }
}

fn add_label(
    parent: HWND,
    text: PCWSTR,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    font: HFONT,
) -> HWND {
    add_control(
        parent,
        w!("STATIC"),
        text,
        SS_LEFT.0 | SS_NOPREFIX.0 | SS_CENTERIMAGE.0,
        WINDOW_EX_STYLE(0),
        0,
        x,
        y,
        width,
        height,
        font,
    )
}

fn add_value(parent: HWND, x: i32, y: i32, width: i32, height: i32, font: HFONT) -> HWND {
    add_control(
        parent,
        w!("EDIT"),
        w!(""),
        ES_READONLY as u32 | ES_AUTOHSCROLL as u32 | ES_NOHIDESEL as u32 | WS_TABSTOP.0,
        WS_EX_CLIENTEDGE,
        0,
        x,
        y,
        width,
        height,
        font,
    )
}

fn add_button(
    parent: HWND,
    text: PCWSTR,
    id: i32,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    font: HFONT,
) -> HWND {
    add_control(
        parent,
        w!("BUTTON"),
        text,
        BS_PUSHBUTTON as u32,
        WINDOW_EX_STYLE(0),
        id,
        x,
        y,
        width,
        height,
        font,
    )
}

fn client_width() -> i32 {
    static WIDTH: std::sync::OnceLock<i32> = std::sync::OnceLock::new();
    *WIDTH.get_or_init(|| {
        let content =
            PADDING + LABEL_WIDTH + ROW_GAP + ID_VALUE_WIDTH + ROW_GAP + BUTTON_WIDTH + PADDING;
        content.max(title_text_width() + caption_extra_width())
    })
}

fn title_text_width() -> i32 {
    unsafe {
        let mut metrics = NONCLIENTMETRICSW {
            cbSize: std::mem::size_of::<NONCLIENTMETRICSW>() as u32,
            ..Default::default()
        };
        if SystemParametersInfoW(
            SPI_GETNONCLIENTMETRICS,
            metrics.cbSize,
            Some(&mut metrics as *mut _ as *mut c_void),
            SYSTEM_PARAMETERS_INFO_UPDATE_FLAGS(0),
        )
        .is_err()
        {
            return 0;
        }
        let font = CreateFontIndirectW(&metrics.lfCaptionFont);
        if font.is_invalid() {
            return 0;
        }
        let dc = GetDC(None);
        if dc.0.is_null() {
            let _ = DeleteObject(font.into());
            return 0;
        }
        let old = SelectObject(dc, font.into());
        let title = str_to_wide(meta::DIALOG_TITLE);
        let mut size = SIZE::default();
        let _ = GetTextExtentPoint32W(dc, &title, &mut size);
        let _ = SelectObject(dc, old);
        let _ = ReleaseDC(None, dc);
        let _ = DeleteObject(font.into());
        size.cx
    }
}

fn caption_extra_width() -> i32 {
    unsafe {
        GetSystemMetrics(SM_CXSMICON)
            + GetSystemMetrics(SM_CXSIZE) * 2
            + GetSystemMetrics(SM_CXPADDEDBORDER) * 2
            + 16
    }
}

fn outer_size_for_client(
    client_width: i32,
    client_height: i32,
    style: WINDOW_STYLE,
    ex: WINDOW_EX_STYLE,
) -> (i32, i32) {
    let mut target = RECT {
        left: 0,
        top: 0,
        right: client_width,
        bottom: client_height,
    };
    unsafe {
        let _ = AdjustWindowRectEx(&mut target, style, false, ex);
    }
    (target.right - target.left, target.bottom - target.top)
}

fn move_control(hwnd: HWND, x: i32, y: i32, width: i32, height: i32) {
    unsafe {
        let _ = SetWindowPos(
            hwnd,
            None,
            x,
            y,
            width,
            height,
            SWP_NOZORDER | SWP_NOACTIVATE,
        );
    }
}

fn set_text_if_changed(hwnd: HWND, text: PCWSTR) {
    set_text_wide_if_changed(hwnd, &unsafe { clone_pcwstr(text) });
}

fn set_text_wide(hwnd: HWND, text: &[u16]) {
    unsafe {
        let _ = SetWindowTextW(hwnd, PCWSTR(text.as_ptr()));
    }
}

fn set_text_wide_if_changed(hwnd: HWND, text: &[u16]) {
    if window_text(hwnd) != text {
        set_text_wide(hwnd, text);
    }
}

fn window_text(hwnd: HWND) -> Vec<u16> {
    unsafe {
        let len = GetWindowTextLengthW(hwnd);
        if len <= 0 {
            return vec![0];
        }
        let mut buf = vec![0u16; len as usize + 1];
        let written = GetWindowTextW(hwnd, &mut buf);
        buf.truncate(written as usize + 1);
        if buf.last() != Some(&0) {
            buf.push(0);
        }
        buf
    }
}

fn active_config_differs(status: &ServerControllerStatus) -> bool {
    status.running
        && status.has_active_config
        && status.loaded_config.logging != status.active_config.logging
}
