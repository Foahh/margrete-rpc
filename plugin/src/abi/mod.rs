mod com;
mod types;
mod vtables;
mod wrappers;

pub use com::{ComPtr, Unknown};
pub use types::*;
pub use vtables::*;
pub use wrappers::*;

#[cfg(test)]
mod layout_tests {
    use super::*;
    use std::mem::{align_of, size_of};

    #[test]
    fn pod_layouts_match_msvc_x64() {
        assert_eq!(size_of::<MpGuid>(), 16);
        assert_eq!(align_of::<MpGuid>(), 4);

        assert_eq!(size_of::<NoteInfo>(), 44);
        assert_eq!(align_of::<NoteInfo>(), 4);

        assert_eq!(size_of::<EventTlsInfo>(), 16);
        assert_eq!(align_of::<EventTlsInfo>(), 8);

        assert_eq!(size_of::<EventNsmInfo>(), 16);
        assert_eq!(align_of::<EventNsmInfo>(), 8);
        assert_eq!(std::mem::offset_of!(EventNsmInfo, speed), 8);

        assert_eq!(size_of::<EventBpmInfo>(), 16);
        assert_eq!(align_of::<EventBpmInfo>(), 8);
        assert_eq!(std::mem::offset_of!(EventBpmInfo, bpm), 8);

        assert_eq!(size_of::<EventBcInfo>(), 12);
        assert_eq!(align_of::<EventBcInfo>(), 4);

        assert_eq!(size_of::<MpPluginInfo>(), 56);
        assert_eq!(align_of::<MpPluginInfo>(), 8);
    }

    #[test]
    fn vtable_slot_counts_match_sdk() {
        const PTR: usize = size_of::<*const ()>();
        assert_eq!(size_of::<BaseVTable>() / PTR, 3);
        assert_eq!(size_of::<CommandVTable>() / PTR, 5);
        assert_eq!(size_of::<ContextVTable>() / PTR, 7);
        assert_eq!(size_of::<DocumentVTable>() / PTR, 5);
        assert_eq!(size_of::<UndoVTable>() / PTR, 11);
        assert_eq!(size_of::<ChartVTable>() / PTR, 16);
        assert_eq!(size_of::<NoteVTable>() / PTR, 17);
        assert_eq!(size_of::<EventVTable>() / PTR, 4);
        assert_eq!(size_of::<EventBpmVTable>() / PTR, 8);
        assert_eq!(size_of::<EventBeatVTable>() / PTR, 8);
        assert_eq!(size_of::<EventTlsVTable>() / PTR, 8);
        assert_eq!(size_of::<EventNsmVTable>() / PTR, 8);
    }
}
