use flexi_logger::{
    DeferredNow, FileSpec, LogSpecification, Logger, LoggerHandle, WriteMode,
    writers::FileLogWriter,
};
use log::Record;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};

struct State {
    handle: Option<LoggerHandle>,
    path: PathBuf,
    writer_path: Option<PathBuf>,
}

fn state() -> &'static Mutex<State> {
    static STATE: OnceLock<Mutex<State>> = OnceLock::new();
    STATE.get_or_init(|| {
        Mutex::new(State {
            handle: None,
            path: PathBuf::new(),
            writer_path: None,
        })
    })
}

fn log_format(
    output: &mut dyn Write,
    now: &mut DeferredNow,
    record: &Record<'_>,
) -> std::io::Result<()> {
    write!(
        output,
        "{} [{}] {}",
        now.format("%Y-%m-%d %H:%M:%S"),
        record.level(),
        record.args()
    )
}

pub fn configure(path: Option<&Path>, enabled: bool) {
    let Ok(mut state) = state().lock() else {
        return;
    };
    state.path.clear();

    let Some(path) = path.filter(|_| enabled) else {
        if let Some(handle) = state.handle.as_ref() {
            handle.set_new_spec(LogSpecification::off());
            handle.flush();
        }
        return;
    };
    state.path = path.to_path_buf();

    let writer_is_current = state.writer_path.as_deref() == Some(path);
    if let Some(handle) = state.handle.as_ref() {
        if writer_is_current {
            handle.set_new_spec(LogSpecification::info());
            return;
        }

        handle.set_new_spec(LogSpecification::off());
        handle.flush();
        let Ok(file_spec) = FileSpec::try_from(path.to_path_buf()) else {
            return;
        };
        let writer = FileLogWriter::builder(file_spec)
            .append()
            .write_mode(WriteMode::Direct)
            .format(log_format);
        if handle.reset_flw(&writer).is_ok() {
            handle.set_new_spec(LogSpecification::info());
            state.writer_path = Some(path.to_path_buf());
        }
        return;
    }

    let Ok(file_spec) = FileSpec::try_from(path.to_path_buf()) else {
        return;
    };
    if let Ok(handle) = Logger::with(LogSpecification::info())
        .log_to_file(file_spec)
        .append()
        .write_mode(WriteMode::Direct)
        .format_for_files(log_format)
        .start()
    {
        state.handle = Some(handle);
        state.writer_path = Some(path.to_path_buf());
    }
}

pub fn path() -> PathBuf {
    state()
        .lock()
        .map(|state| state.path.clone())
        .unwrap_or_default()
}

pub fn path_utf8(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

pub fn local_date() -> String {
    DeferredNow::new().format("%Y-%m-%d").to_string()
}
