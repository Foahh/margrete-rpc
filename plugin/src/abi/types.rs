use std::ffi::c_void;

pub type MpBoolean = i32;
pub type MpInteger = i32;

pub const MP_TRUE: MpBoolean = 1;
pub const MP_FALSE: MpBoolean = 0;
pub const MP_SDK_VERSION: MpInteger = 2;

pub const MP_NOTETYPE_UNKNOWN: MpInteger = 0;
pub const MP_NOTETYPE_TAP: MpInteger = 1;
pub const MP_NOTETYPE_EXTAP: MpInteger = 2;
pub const MP_NOTETYPE_FLICK: MpInteger = 3;
pub const MP_NOTETYPE_DAMAGE: MpInteger = 4;
pub const MP_NOTETYPE_HOLD: MpInteger = 5;
pub const MP_NOTETYPE_SLIDE: MpInteger = 6;
pub const MP_NOTETYPE_AIR: MpInteger = 7;
pub const MP_NOTETYPE_AIRHOLD: MpInteger = 8;
pub const MP_NOTETYPE_AIRSLIDE: MpInteger = 9;
pub const MP_NOTETYPE_AIRCRUSH: MpInteger = 10;
pub const MP_NOTETYPE_CLICK: MpInteger = 11;

pub const MP_NOTELONGATTR_NONE: MpInteger = 0;
pub const MP_NOTELONGATTR_BEGIN: MpInteger = 1;
pub const MP_NOTELONGATTR_STEP: MpInteger = 2;
pub const MP_NOTELONGATTR_CONTROL: MpInteger = 3;
pub const MP_NOTELONGATTR_CURVE_CONTROL: MpInteger = 4;
pub const MP_NOTELONGATTR_END: MpInteger = 5;
pub const MP_NOTELONGATTR_END_NOACT: MpInteger = 6;

pub const MP_NOTEDIR_NONE: MpInteger = 0;
pub const MP_NOTEDIR_AUTO: MpInteger = 1;
pub const MP_NOTEDIR_UP: MpInteger = 2;
pub const MP_NOTEDIR_DOWN: MpInteger = 3;
pub const MP_NOTEDIR_CENTER: MpInteger = 4;
pub const MP_NOTEDIR_LEFT: MpInteger = 5;
pub const MP_NOTEDIR_RIGHT: MpInteger = 6;
pub const MP_NOTEDIR_UPLEFT: MpInteger = 7;
pub const MP_NOTEDIR_UPRIGHT: MpInteger = 8;
pub const MP_NOTEDIR_DOWNLEFT: MpInteger = 9;
pub const MP_NOTEDIR_DOWNRIGHT: MpInteger = 10;
pub const MP_NOTEDIR_ROTATE_LEFT: MpInteger = 11;
pub const MP_NOTEDIR_ROTATE_RIGHT: MpInteger = 12;
pub const MP_NOTEDIR_INOUT: MpInteger = 13;
pub const MP_NOTEDIR_OUTIN: MpInteger = 14;

pub const MP_NOTEEXATTR_NONE: MpInteger = 0;
pub const MP_NOTEEXATTR_INVERT: MpInteger = 1;
pub const MP_NOTEEXATTR_HAS_NOTE: MpInteger = 2;
pub const MP_NOTEEXATTR_EXJDG: MpInteger = 3;

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct MpGuid {
    pub data1: u32,
    pub data2: u16,
    pub data3: u16,
    pub data4: [u8; 8],
}

impl MpGuid {
    pub const fn from_fields(data1: u32, data2: u16, data3: u16, data4: [u8; 8]) -> Self {
        Self {
            data1,
            data2,
            data3,
            data4,
        }
    }

    pub fn eq_guid(&self, other: &MpGuid) -> bool {
        self.data1 == other.data1
            && self.data2 == other.data2
            && self.data3 == other.data3
            && self.data4 == other.data4
    }
}

macro_rules! mp_guid {
    ($l:expr, $w1:expr, $w2:expr, $b1:expr, $b2:expr, $b3:expr, $b4:expr, $b5:expr, $b6:expr, $b7:expr, $b8:expr) => {
        MpGuid::from_fields($l, $w1, $w2, [$b1, $b2, $b3, $b4, $b5, $b6, $b7, $b8])
    };
}

pub const IID_BASE: MpGuid =
    mp_guid!(0xb2f76848, 0xfb04, 0x4cfc, 0x9e, 0x5a, 0xb5, 0xe4, 0xfd, 0x47, 0x47, 0xca);
pub const IID_UNDO: MpGuid =
    mp_guid!(0xe9200b48, 0xfee7, 0x4332, 0x98, 0x11, 0xe4, 0xb6, 0x3b, 0x96, 0x50, 0x8f);
pub const IID_NOTE: MpGuid =
    mp_guid!(0x7bf6174e, 0xddf7, 0x498c, 0xae, 0x30, 0xa9, 0x2d, 0xce, 0x2b, 0x94, 0xd9);
pub const IID_EVENT: MpGuid =
    mp_guid!(0x4607aa39, 0x1ad7, 0x4fae, 0x90, 0x0f, 0xd7, 0x86, 0x95, 0x3e, 0x2f, 0x1f);
pub const IID_EVENT_TLS: MpGuid =
    mp_guid!(0x8a7c2e24, 0xf055, 0x4f41, 0xa7, 0xa4, 0x2f, 0x73, 0x69, 0xe6, 0x33, 0xfe);
pub const IID_EVENT_NSM: MpGuid =
    mp_guid!(0xf1656785, 0x2f74, 0x4efb, 0x8a, 0xbb, 0x90, 0x16, 0x94, 0x0e, 0xfa, 0xd1);
pub const IID_EVENT_BPM: MpGuid =
    mp_guid!(0xd25bee92, 0xca99, 0x4d62, 0xa9, 0x61, 0x26, 0xbf, 0xfd, 0x5b, 0x6e, 0xee);
pub const IID_EVENT_BEAT: MpGuid =
    mp_guid!(0xf4c8269e, 0x0c08, 0x46a8, 0x96, 0xf6, 0xf2, 0xaa, 0xaf, 0x78, 0x64, 0x2d);
pub const IID_CHART: MpGuid =
    mp_guid!(0x6db9dd3f, 0x631b, 0x4496, 0xbf, 0x5b, 0x53, 0x5f, 0xf1, 0xf0, 0xee, 0xb0);
pub const IID_DOCUMENT: MpGuid =
    mp_guid!(0xf90dce72, 0x71ca, 0x412d, 0x94, 0xce, 0xb4, 0xae, 0x89, 0xfe, 0x5a, 0x12);
pub const IID_CONTEXT: MpGuid =
    mp_guid!(0x577c993c, 0x679c, 0x4ecd, 0xb2, 0x05, 0x31, 0xc6, 0x4e, 0x57, 0x4d, 0xb2);
pub const IID_COMMAND: MpGuid =
    mp_guid!(0x2e868db6, 0xff3a, 0x46c8, 0x96, 0x09, 0x18, 0xea, 0x41, 0x94, 0x7d, 0x42);

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct MpPluginInfo {
    pub sdk_version: MpInteger,
    pub name_buffer: *mut u16,
    pub name_buffer_length: MpInteger,
    pub desc_buffer: *mut u16,
    pub desc_buffer_length: MpInteger,
    pub developer_buffer: *mut u16,
    pub developer_buffer_length: MpInteger,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct NoteInfo {
    pub r#type: MpInteger,
    pub long_attr: MpInteger,
    pub direction: MpInteger,
    pub ex_attr: MpInteger,
    pub variation_id: MpInteger,
    pub x: MpInteger,
    pub width: MpInteger,
    pub height: MpInteger,
    pub tick: MpInteger,
    pub timeline_id: MpInteger,
    pub option_value: MpInteger,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct EventTlsInfo {
    pub timeline_id: MpInteger,
    pub tick: MpInteger,
    pub speed: f64,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct EventNsmInfo {
    pub tick: MpInteger,
    pub speed: f64,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct EventBpmInfo {
    pub tick: MpInteger,
    pub bpm: f64,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct EventBcInfo {
    pub bar: MpInteger,
    pub beats_per_bar: MpInteger,
    pub beat_unit: MpInteger,
}

pub fn copy_wide(dest: *mut u16, dest_len: MpInteger, src: &str) {
    if dest.is_null() || dest_len <= 0 {
        return;
    }
    let mut wide: Vec<u16> = src.encode_utf16().collect();
    let max = dest_len as usize;
    if wide.len() >= max {
        wide.truncate(max.saturating_sub(1));
    }
    unsafe {
        for (i, ch) in wide.iter().enumerate() {
            *dest.add(i) = *ch;
        }
        *dest.add(wide.len()) = 0;
    }
}

pub fn utf16_to_string(ptr: *const u16, len: usize) -> String {
    if ptr.is_null() || len == 0 {
        return String::new();
    }
    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
    let end = slice.iter().position(|&c| c == 0).unwrap_or(len);
    String::from_utf16_lossy(&slice[..end])
}

pub type RawPtr = *mut c_void;
