use super::com::ComPtr;
use super::types::{
    EventBcInfo, EventBpmInfo, EventNsmInfo, EventTlsInfo, MpBoolean, MpGuid, MpInteger, NoteInfo,
    MP_FALSE, MP_TRUE,
};
use super::vtables::*;
use crate::error::{check, PluginError, Result};
use std::ffi::c_void;

macro_rules! call {
    ($this:expr, $field:ident $(, $arg:expr)* $(,)?) => {{
        let vtable = (*$this).vtable;
        ((*vtable).$field)($this $(, $arg)*)
    }};
}

impl Context {
    pub fn get_document(&self) -> Result<ComPtr<Document>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            check(
                call!(self as *const _ as *mut Self, get_document, &mut ptr),
                "document is unavailable",
            )?;
            if ptr.is_null() {
                return Err(PluginError::internal("document is unavailable"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }

    pub fn main_window_handle(&self) -> *mut c_void {
        unsafe { call!(self as *const _ as *mut Self, get_main_window_handle) }
    }

    pub fn current_tick(&self) -> MpInteger {
        unsafe { call!(self as *const _ as *mut Self, get_current_tick) }
    }

    pub fn update(&self) {
        unsafe { call!(self as *const _ as *mut Self, update) }
    }
}

impl Document {
    pub fn get_chart(&self) -> Result<ComPtr<Chart>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            check(
                call!(self as *const _ as *mut Self, get_chart, &mut ptr),
                "chart is unavailable",
            )?;
            if ptr.is_null() {
                return Err(PluginError::internal("chart is unavailable"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }

    pub fn get_undo_buffer(&self) -> Result<ComPtr<UndoBuffer>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            check(
                call!(self as *const _ as *mut Self, get_undo_buffer, &mut ptr),
                "undoBuffer buffer is unavailable",
            )?;
            if ptr.is_null() {
                return Err(PluginError::internal("undoBuffer buffer is unavailable"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }
}

impl UndoBuffer {
    pub fn begin_recording(&self) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, begin_recording),
                "failed to begin undo recording",
            )
        }
    }

    pub fn commit_recording(&self) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, commit_recording),
                "failed to commit undo recording",
            )
        }
    }

    pub fn discard_recording(&self) {
        unsafe {
            let _ = call!(self as *const _ as *mut Self, discard_recording);
        }
    }

    pub fn undo(&self) -> MpBoolean {
        unsafe { call!(self as *const _ as *mut Self, undo) }
    }

    pub fn redo(&self) -> MpBoolean {
        unsafe { call!(self as *const _ as *mut Self, redo) }
    }

    pub fn can_undo(&self) -> bool {
        unsafe { call!(self as *const _ as *mut Self, can_undo) == MP_TRUE }
    }

    pub fn can_redo(&self) -> bool {
        unsafe { call!(self as *const _ as *mut Self, can_redo) == MP_TRUE }
    }
}

impl Chart {
    pub fn create_note(&self) -> Result<ComPtr<Note>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            check(
                call!(self as *const _ as *mut Self, create_note, &mut ptr),
                "failed to create note",
            )?;
            if ptr.is_null() {
                return Err(PluginError::internal("failed to create note"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }

    pub fn notes_count(&self) -> MpInteger {
        unsafe { call!(self as *const _ as *mut Self, get_notes_count) }
    }

    pub fn get_note(&self, index: MpInteger) -> Result<ComPtr<Note>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(self as *const _ as *mut Self, get_note, index, &mut ptr);
            if ok != MP_TRUE || ptr.is_null() {
                return Err(PluginError::internal("failed to read note from chart"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }

    pub fn append_note(&self, note: *mut Note) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, append_note, note),
                "failed to append desired root note",
            )
        }
    }

    pub fn delete_note(&self, note: *mut Note) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, delete_note, note),
                "failed to delete note",
            )
        }
    }

    pub fn create_event(&self, iid: &MpGuid) -> Result<*mut c_void> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            check(
                call!(self as *const _ as *mut Self, create_event, iid, &mut ptr),
                "failed to create event",
            )?;
            if ptr.is_null() {
                return Err(PluginError::internal("failed to create event"));
            }
            Ok(ptr)
        }
    }

    pub fn append_event(&self, event: *mut Event) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, append_event, event),
                "failed to append event",
            )
        }
    }

    pub fn delete_event(&self, event: *mut Event) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, delete_event, event),
                "failed to delete event",
            )
        }
    }

    pub fn find_event_bpm(&self, tick: MpInteger) -> Option<ComPtr<EventBpm>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(
                self as *const _ as *mut Self,
                find_event_bpm,
                tick,
                &mut ptr
            );
            if ok == MP_TRUE && !ptr.is_null() {
                Some(ComPtr::from_raw(ptr as *mut EventBpm))
            } else {
                None
            }
        }
    }

    pub fn find_event_beat_change(&self, bar: MpInteger) -> Option<ComPtr<EventBeat>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(
                self as *const _ as *mut Self,
                find_event_beat_change,
                bar,
                &mut ptr
            );
            if ok == MP_TRUE && !ptr.is_null() {
                Some(ComPtr::from_raw(ptr as *mut EventBeat))
            } else {
                None
            }
        }
    }

    pub fn find_event_timeline_speed(
        &self,
        tick: MpInteger,
        timeline_id: MpInteger,
    ) -> Option<ComPtr<EventTls>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(
                self as *const _ as *mut Self,
                find_event_timeline_speed,
                tick,
                timeline_id,
                &mut ptr
            );
            if ok == MP_TRUE && !ptr.is_null() {
                Some(ComPtr::from_raw(ptr as *mut EventTls))
            } else {
                None
            }
        }
    }

    pub fn find_event_note_speed(&self, tick: MpInteger) -> Option<ComPtr<EventNsm>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(
                self as *const _ as *mut Self,
                find_event_note_speed_modifier,
                tick,
                &mut ptr
            );
            if ok == MP_TRUE && !ptr.is_null() {
                Some(ComPtr::from_raw(ptr as *mut EventNsm))
            } else {
                None
            }
        }
    }
}

impl Note {
    pub fn id(&self) -> MpInteger {
        unsafe { call!(self as *const _ as *mut Self, get_id) }
    }

    pub fn info(&self) -> NoteInfo {
        unsafe {
            let mut info = NoteInfo::default();
            call!(self as *const _ as *mut Self, get_info, &mut info);
            info
        }
    }

    pub fn set_info(&self, info: &NoteInfo) {
        unsafe {
            call!(self as *const _ as *mut Self, set_info, info);
        }
    }

    pub fn children_count(&self) -> MpInteger {
        unsafe { call!(self as *const _ as *mut Self, get_children_count) }
    }

    pub fn get_child(&self, index: MpInteger) -> Result<ComPtr<Note>> {
        unsafe {
            let mut ptr = std::ptr::null_mut();
            let ok = call!(self as *const _ as *mut Self, get_child, index, &mut ptr);
            if ok != MP_TRUE || ptr.is_null() {
                return Err(PluginError::internal("failed to read child note"));
            }
            Ok(ComPtr::from_raw(ptr))
        }
    }

    pub fn append_child(&self, child: *mut Note) -> Result<()> {
        unsafe {
            check(
                call!(self as *const _ as *mut Self, append_child, child),
                "failed to append child note",
            )
        }
    }
}

impl EventBpm {
    pub fn info(&self) -> EventBpmInfo {
        unsafe {
            let mut info = EventBpmInfo::default();
            call!(self as *const _ as *mut Self, get_info, &mut info);
            info
        }
    }

    pub fn set_info(&self, info: &EventBpmInfo) {
        unsafe {
            call!(self as *const _ as *mut Self, set_info, info);
        }
    }

    pub fn as_event(&self) -> *mut Event {
        self as *const _ as *mut Event
    }
}

impl EventBeat {
    pub fn info(&self) -> EventBcInfo {
        unsafe {
            let mut info = EventBcInfo::default();
            call!(self as *const _ as *mut Self, get_info, &mut info);
            info
        }
    }

    pub fn set_info(&self, info: &EventBcInfo) {
        unsafe {
            call!(self as *const _ as *mut Self, set_info, info);
        }
    }

    pub fn as_event(&self) -> *mut Event {
        self as *const _ as *mut Event
    }
}

impl EventTls {
    pub fn info(&self) -> EventTlsInfo {
        unsafe {
            let mut info = EventTlsInfo::default();
            call!(self as *const _ as *mut Self, get_info, &mut info);
            info
        }
    }

    pub fn set_info(&self, info: &EventTlsInfo) {
        unsafe {
            call!(self as *const _ as *mut Self, set_info, info);
        }
    }

    pub fn as_event(&self) -> *mut Event {
        self as *const _ as *mut Event
    }
}

impl EventNsm {
    pub fn info(&self) -> EventNsmInfo {
        unsafe {
            let mut info = EventNsmInfo::default();
            call!(self as *const _ as *mut Self, get_info, &mut info);
            info
        }
    }

    pub fn set_info(&self, info: &EventNsmInfo) {
        unsafe {
            call!(self as *const _ as *mut Self, set_info, info);
        }
    }

    pub fn as_event(&self) -> *mut Event {
        self as *const _ as *mut Event
    }
}

impl ComPtr<Note> {
    pub fn note(&self) -> &Note {
        self.as_ref().expect("note")
    }
}

impl ComPtr<Chart> {
    pub fn chart(&self) -> &Chart {
        self.as_ref().expect("chart")
    }
}

impl ComPtr<Context> {
    pub fn context(&self) -> &Context {
        self.as_ref().expect("context")
    }
}

impl ComPtr<UndoBuffer> {
    pub fn undo(&self) -> &UndoBuffer {
        self.as_ref().expect("undo")
    }
}

impl ComPtr<Document> {
    pub fn document(&self) -> &Document {
        self.as_ref().expect("document")
    }
}

pub fn is_true(value: MpBoolean) -> bool {
    value == MP_TRUE
}

pub fn is_false(value: MpBoolean) -> bool {
    value == MP_FALSE
}
