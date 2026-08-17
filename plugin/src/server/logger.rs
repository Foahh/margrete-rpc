use log::{LevelFilter, Log, Metadata, Record};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, Once};
use windows::Win32::System::SystemInformation::GetLocalTime;

struct Inner {
    path: PathBuf,
    out: Option<File>,
}

struct Logger {
    inner: Mutex<Inner>,
}

static LOGGER: Logger = Logger::new();
static INIT: Once = Once::new();

impl Logger {
    const fn new() -> Self {
        Self {
            inner: Mutex::new(Inner {
                path: PathBuf::new(),
                out: None,
            }),
        }
    }

    fn configure(&self, path: Option<&Path>) {
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

    fn path(&self) -> PathBuf {
        self.inner
            .lock()
            .map(|inner| inner.path.clone())
            .unwrap_or_default()
    }

    fn write(&self, level: &str, message: &std::fmt::Arguments<'_>) {
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

impl Log for Logger {
    fn enabled(&self, metadata: &Metadata<'_>) -> bool {
        metadata.level() <= log::Level::Info
    }

    fn log(&self, record: &Record<'_>) {
        if !self.enabled(record.metadata()) {
            return;
        }
        self.write(record.level().as_str(), record.args());
    }

    fn flush(&self) {
        if let Ok(mut inner) = self.inner.lock()
            && let Some(file) = inner.out.as_mut()
        {
            let _ = file.flush();
        }
    }
}

pub fn configure(path: Option<&Path>) {
    INIT.call_once(|| {
        let _ = log::set_logger(&LOGGER);
    });
    LOGGER.configure(path);
    log::set_max_level(if path.is_some() {
        LevelFilter::Info
    } else {
        LevelFilter::Off
    });
}

pub fn path() -> PathBuf {
    LOGGER.path()
}

pub fn path_utf8(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

pub fn local_date() -> String {
    let st = unsafe { GetLocalTime() };
    format!("{:04}-{:02}-{:02}", st.wYear, st.wMonth, st.wDay)
}

fn local_stamp() -> String {
    let st = unsafe { GetLocalTime() };
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond
    )
}
