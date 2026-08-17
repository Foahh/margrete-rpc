use crate::error::{PluginError, Result};
use crate::wide::{str_to_wide_null, wide_null_to_string};
use rand::seq::SliceRandom;
use std::collections::HashSet;
use windows::Win32::Foundation::{
    CloseHandle, ERROR_ALREADY_EXISTS, GetLastError, HANDLE, SetLastError, WIN32_ERROR,
};
use windows::Win32::Storage::FileSystem::{
    FindClose, FindFirstFileW, FindNextFileW, WIN32_FIND_DATAW,
};
use windows::Win32::System::Threading::CreateMutexW;
use windows::core::PCWSTR;

pub const PIPE_NAME_PREFIX: &str = "margrete-";

pub struct AllocatedInstance {
    pub code: String,
    _lock: InstanceLock,
}

impl AllocatedInstance {
    pub fn pipe_name(&self) -> String {
        format!("{PIPE_NAME_PREFIX}{}", self.code)
    }
}

struct InstanceLock {
    handle: HANDLE,
}

unsafe impl Send for InstanceLock {}
unsafe impl Sync for InstanceLock {}

impl Drop for InstanceLock {
    fn drop(&mut self) {
        if !self.handle.is_invalid() {
            let _ = unsafe { CloseHandle(self.handle) };
        }
    }
}

pub fn pipe_name(code: &str) -> String {
    format!("{PIPE_NAME_PREFIX}{code}")
}

pub fn parse_code(name: &str) -> Option<&str> {
    let rest = name.strip_prefix(PIPE_NAME_PREFIX)?;
    if rest.len() == 4 && rest.bytes().all(|b| b.is_ascii_digit()) {
        Some(rest)
    } else {
        None
    }
}

pub fn allocate() -> Result<AllocatedInstance> {
    let occupied = occupied_pipe_codes();
    let mut candidates: Vec<_> = (0..10_000).collect();
    candidates.shuffle(&mut rand::rng());
    for n in candidates {
        if let Some(instance) = try_code(n, &occupied) {
            return Ok(instance);
        }
    }
    Err(PluginError::internal("no free margrete-XXXX pipe name"))
}

fn try_code(n: usize, occupied: &HashSet<String>) -> Option<AllocatedInstance> {
    let code = format!("{n:04}");
    if occupied.contains(&code) {
        return None;
    }
    let lock = try_claim(&code)?;
    Some(AllocatedInstance { code, _lock: lock })
}

fn try_claim(code: &str) -> Option<InstanceLock> {
    let name = format!("Local\\{PIPE_NAME_PREFIX}{code}");
    let wide = str_to_wide_null(&name);
    unsafe {
        SetLastError(WIN32_ERROR(0));
        let handle = CreateMutexW(None, true, PCWSTR(wide.as_ptr())).ok()?;
        if GetLastError() == ERROR_ALREADY_EXISTS {
            let _ = CloseHandle(handle);
            return None;
        }
        Some(InstanceLock { handle })
    }
}

pub fn occupied_pipe_codes() -> HashSet<String> {
    let mut codes = HashSet::new();
    let pattern = str_to_wide_null(r"\\.\pipe\*");
    let mut data = WIN32_FIND_DATAW::default();
    let Ok(handle) = (unsafe { FindFirstFileW(PCWSTR(pattern.as_ptr()), &mut data) }) else {
        return codes;
    };
    loop {
        if let Some(code) = parse_code(&wide_null_to_string(&data.cFileName)) {
            codes.insert(code.to_string());
        }
        if unsafe { FindNextFileW(handle, &mut data) }.is_err() {
            break;
        }
    }
    let _ = unsafe { FindClose(handle) };
    codes
}
