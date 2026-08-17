use std::ffi::{OsStr, OsString};
use std::os::windows::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use windows::core::PCWSTR;

pub(crate) fn str_to_wide(text: &str) -> Vec<u16> {
    text.encode_utf16().collect()
}

pub(crate) fn str_to_wide_null(text: &str) -> Vec<u16> {
    let mut wide = str_to_wide(text);
    wide.push(0);
    wide
}

pub(crate) fn path_to_wide_null(path: &Path) -> Vec<u16> {
    os_str_to_wide_null(path.as_os_str())
}

fn os_str_to_wide_null(value: &OsStr) -> Vec<u16> {
    value.encode_wide().chain(std::iter::once(0)).collect()
}

pub(crate) fn wide_null_to_string(wide: &[u16]) -> String {
    let len = wide
        .iter()
        .position(|&unit| unit == 0)
        .unwrap_or(wide.len());
    String::from_utf16_lossy(&wide[..len])
}

pub(crate) fn wide_to_path(wide: &[u16]) -> PathBuf {
    PathBuf::from(OsString::from_wide(wide))
}

pub(crate) unsafe fn clone_pcwstr(text: PCWSTR) -> Vec<u16> {
    if text.0.is_null() {
        return vec![0];
    }
    let mut len = 0usize;
    while unsafe { *text.0.add(len) } != 0 {
        len += 1;
    }
    unsafe { std::slice::from_raw_parts(text.0, len + 1) }.to_vec()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn string_encoders_handle_non_bmp_text_and_termination() {
        let text = "Margrete \u{1f3bc}";
        let wide = str_to_wide(text);
        let terminated = str_to_wide_null(text);

        assert_eq!(terminated[..terminated.len() - 1], wide);
        assert_eq!(terminated.last(), Some(&0));
        assert_eq!(String::from_utf16(&wide).unwrap(), text);
    }

    #[test]
    fn null_terminated_decoder_stops_at_first_nul() {
        let wide = [b'M' as u16, b'G' as u16, 0, b'X' as u16];

        assert_eq!(wide_null_to_string(&wide), "MG");
    }

    #[test]
    fn path_encoding_preserves_windows_code_units() {
        let original = PathBuf::from(OsString::from_wide(&[
            b'C' as u16,
            b':' as u16,
            b'\\' as u16,
            0xd800,
        ]));
        let encoded = path_to_wide_null(&original);

        assert_eq!(encoded.last(), Some(&0));
        assert_eq!(wide_to_path(&encoded[..encoded.len() - 1]), original);
    }
}
