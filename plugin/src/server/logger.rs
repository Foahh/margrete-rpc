use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use windows::Win32::System::SystemInformation::GetLocalTime;

struct Inner {
    path: PathBuf,
    out: Option<File>,
}

pub struct Logger {
    inner: Mutex<Inner>,
}

impl Default for Logger {
    fn default() -> Self {
        Self::new()
    }
}

impl Logger {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(Inner {
                path: PathBuf::new(),
                out: None,
            }),
        }
    }

    pub fn configure(&self, path: Option<&Path>) {
        let Ok(mut inner) = self.inner.lock() else {
            return;
        };
        inner.out = None;
        inner.path = PathBuf::new();
        let Some(path) = path else {
            return;
        };
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        inner.path = path.to_path_buf();
        inner.out = OpenOptions::new().create(true).append(true).open(path).ok();
    }

    pub fn path(&self) -> PathBuf {
        self.inner
            .lock()
            .map(|inner| inner.path.clone())
            .unwrap_or_default()
    }

    pub fn info(&self, message: impl AsRef<str>) {
        self.write("INFO", message.as_ref());
    }

    pub fn error(&self, message: impl AsRef<str>) {
        self.write("ERROR", message.as_ref());
    }

    fn write(&self, level: &str, message: &str) {
        let Ok(mut inner) = self.inner.lock() else {
            return;
        };
        let Some(file) = inner.out.as_mut() else {
            return;
        };
        let stamp = local_stamp();
        let _ = writeln!(file, "{stamp} [{level}] {message}");
        let _ = file.flush();
    }
}

pub fn path_utf8(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn local_stamp() -> String {
    let st = unsafe { GetLocalTime() };
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond
    )
}
