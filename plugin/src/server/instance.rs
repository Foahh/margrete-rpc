use crate::error::{PluginError, Result};
use std::collections::HashSet;
use windows::Win32::Foundation::{
    CloseHandle, ERROR_ALREADY_EXISTS, GetLastError, HANDLE, SetLastError, WIN32_ERROR,
};
use windows::Win32::Storage::FileSystem::{
    FindClose, FindFirstFileW, FindNextFileW, WIN32_FIND_DATAW,
};
use windows::Win32::System::SystemInformation::GetTickCount64;
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
    let mut rng = Rng::new();
    let mut tried = [false; 10_000];
    for _ in 0..10_000 {
        let n = rng.uniform(10_000);
        if tried[n] {
            continue;
        }
        tried[n] = true;
        if let Some(instance) = try_code(n, &occupied) {
            return Ok(instance);
        }
    }
    for (n, already) in tried.iter().enumerate() {
        if *already {
            continue;
        }
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
    let wide: Vec<u16> = name.encode_utf16().chain(std::iter::once(0)).collect();
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
    let pattern: Vec<u16> = r"\\.\pipe\*"
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();
    let mut data = WIN32_FIND_DATAW::default();
    let Ok(handle) = (unsafe { FindFirstFileW(PCWSTR(pattern.as_ptr()), &mut data) }) else {
        return codes;
    };
    loop {
        if let Some(code) = parse_code(&wcharz_to_string(&data.cFileName)) {
            codes.insert(code.to_string());
        }
        if unsafe { FindNextFileW(handle, &mut data) }.is_err() {
            break;
        }
    }
    let _ = unsafe { FindClose(handle) };
    codes
}

fn wcharz_to_string(buf: &[u16]) -> String {
    let len = buf.iter().position(|&c| c == 0).unwrap_or(buf.len());
    String::from_utf16_lossy(&buf[..len])
}

struct Rng(u64);

impl Rng {
    fn new() -> Self {
        let seed = unsafe { GetTickCount64() } ^ (u64::from(std::process::id()) << 32);
        Self(seed | 1)
    }

    fn uniform(&mut self, max: usize) -> usize {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1);
        ((self.0 >> 33) as usize) % max
    }
}
