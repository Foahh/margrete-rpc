use super::types::{
    EventBcInfo, EventBpmInfo, EventNsmInfo, EventTlsInfo, MpBoolean, MpGuid, MpInteger, NoteInfo,
};
use std::ffi::c_void;

macro_rules! iface {
    ($name:ident, $vtable:ident) => {
        #[repr(C)]
        pub struct $name {
            pub vtable: *const $vtable,
        }
    };
}

pub type AddRefFn<T> = unsafe extern "C" fn(this: *mut T) -> MpInteger;
pub type ReleaseFn<T> = unsafe extern "C" fn(this: *mut T) -> MpInteger;
pub type QueryInterfaceFn<T> =
    unsafe extern "C" fn(this: *mut T, iid: *const MpGuid, ppobj: *mut *mut c_void) -> MpBoolean;

#[repr(C)]
pub struct BaseVTable {
    pub add_ref: AddRefFn<Base>,
    pub release: ReleaseFn<Base>,
    pub query_interface: QueryInterfaceFn<Base>,
}
iface!(Base, BaseVTable);

#[repr(C)]
pub struct CommandVTable {
    pub add_ref: AddRefFn<Command>,
    pub release: ReleaseFn<Command>,
    pub query_interface: QueryInterfaceFn<Command>,
    pub get_command_name: unsafe extern "C" fn(
        this: *mut Command,
        text: *mut u16,
        text_length: MpInteger,
    ) -> MpBoolean,
    pub invoke: unsafe extern "C" fn(this: *mut Command, ctx: *mut Context) -> MpBoolean,
}
iface!(Command, CommandVTable);

#[repr(C)]
pub struct ContextVTable {
    pub add_ref: AddRefFn<Context>,
    pub release: ReleaseFn<Context>,
    pub query_interface: QueryInterfaceFn<Context>,
    pub get_document:
        unsafe extern "C" fn(this: *mut Context, ppobj: *mut *mut Document) -> MpBoolean,
    pub get_main_window_handle: unsafe extern "C" fn(this: *mut Context) -> *mut c_void,
    pub get_current_tick: unsafe extern "C" fn(this: *mut Context) -> MpInteger,
    pub update: unsafe extern "C" fn(this: *mut Context),
}
iface!(Context, ContextVTable);

#[repr(C)]
pub struct DocumentVTable {
    pub add_ref: AddRefFn<Document>,
    pub release: ReleaseFn<Document>,
    pub query_interface: QueryInterfaceFn<Document>,
    pub get_chart: unsafe extern "C" fn(this: *mut Document, ppobj: *mut *mut Chart) -> MpBoolean,
    pub get_undo_buffer:
        unsafe extern "C" fn(this: *mut Document, ppobj: *mut *mut UndoBuffer) -> MpBoolean,
}
iface!(Document, DocumentVTable);

#[repr(C)]
pub struct UndoVTable {
    pub add_ref: AddRefFn<UndoBuffer>,
    pub release: ReleaseFn<UndoBuffer>,
    pub query_interface: QueryInterfaceFn<UndoBuffer>,
    pub begin_recording: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub commit_recording: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub discard_recording: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub undo: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub redo: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub can_undo: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub can_redo: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
    pub is_recording: unsafe extern "C" fn(this: *mut UndoBuffer) -> MpBoolean,
}
iface!(UndoBuffer, UndoVTable);

#[repr(C)]
pub struct ChartVTable {
    pub add_ref: AddRefFn<Chart>,
    pub release: ReleaseFn<Chart>,
    pub query_interface: QueryInterfaceFn<Chart>,
    pub create_note: unsafe extern "C" fn(this: *mut Chart, ppobj: *mut *mut Note) -> MpBoolean,
    pub get_notes_count: unsafe extern "C" fn(this: *mut Chart) -> MpInteger,
    pub get_note: unsafe extern "C" fn(
        this: *mut Chart,
        index: MpInteger,
        ppobj: *mut *mut Note,
    ) -> MpBoolean,
    pub append_note: unsafe extern "C" fn(this: *mut Chart, note: *mut Note) -> MpBoolean,
    pub delete_note: unsafe extern "C" fn(this: *mut Chart, note: *mut Note) -> MpBoolean,
    pub offset_notes: unsafe extern "C" fn(this: *mut Chart, tick: MpInteger),
    pub create_event: unsafe extern "C" fn(
        this: *mut Chart,
        iid: *const MpGuid,
        ppobj: *mut *mut c_void,
    ) -> MpBoolean,
    pub append_event: unsafe extern "C" fn(this: *mut Chart, event: *mut Event) -> MpBoolean,
    pub delete_event: unsafe extern "C" fn(this: *mut Chart, event: *mut Event) -> MpBoolean,
    pub find_event_timeline_speed: unsafe extern "C" fn(
        this: *mut Chart,
        tick: MpInteger,
        timeline_id: MpInteger,
        ppobj: *mut *mut c_void,
    ) -> MpBoolean,
    pub find_event_note_speed_modifier: unsafe extern "C" fn(
        this: *mut Chart,
        tick: MpInteger,
        ppobj: *mut *mut c_void,
    ) -> MpBoolean,
    pub find_event_bpm: unsafe extern "C" fn(
        this: *mut Chart,
        tick: MpInteger,
        ppobj: *mut *mut c_void,
    ) -> MpBoolean,
    pub find_event_beat_change: unsafe extern "C" fn(
        this: *mut Chart,
        bar: MpInteger,
        ppobj: *mut *mut c_void,
    ) -> MpBoolean,
}
iface!(Chart, ChartVTable);

#[repr(C)]
pub struct NoteVTable {
    pub add_ref: AddRefFn<Note>,
    pub release: ReleaseFn<Note>,
    pub query_interface: QueryInterfaceFn<Note>,
    pub get_id: unsafe extern "C" fn(this: *mut Note) -> MpInteger,
    pub get_info: unsafe extern "C" fn(this: *mut Note, note_info: *mut NoteInfo),
    pub set_info: unsafe extern "C" fn(this: *mut Note, note_info: *const NoteInfo),
    pub get_children_count: unsafe extern "C" fn(this: *mut Note) -> MpInteger,
    pub get_child:
        unsafe extern "C" fn(this: *mut Note, index: MpInteger, ppobj: *mut *mut Note) -> MpBoolean,
    pub get_parent: unsafe extern "C" fn(this: *mut Note, ppobj: *mut *mut Note) -> MpBoolean,
    pub append_child: unsafe extern "C" fn(this: *mut Note, note: *mut Note) -> MpBoolean,
    pub delete_child: unsafe extern "C" fn(this: *mut Note, child: *mut Note) -> MpBoolean,
    pub clone: unsafe extern "C" fn(this: *mut Note, ppobj: *mut *mut Note) -> MpBoolean,
    pub replace_with:
        unsafe extern "C" fn(this: *mut Note, src_note: *const Note, requires_sort: MpBoolean),
    pub copy_info_to: unsafe extern "C" fn(this: *mut Note, dest_note: *mut Note),
    pub get_base_note: unsafe extern "C" fn(this: *mut Note, ppobj: *mut *mut Note) -> MpBoolean,
    pub offset_child: unsafe extern "C" fn(this: *mut Note, offset_tick: MpInteger),
    pub flip_h: unsafe extern "C" fn(this: *mut Note, recursive: MpBoolean),
}
iface!(Note, NoteVTable);

#[repr(C)]
pub struct EventVTable {
    pub add_ref: AddRefFn<Event>,
    pub release: ReleaseFn<Event>,
    pub query_interface: QueryInterfaceFn<Event>,
    pub get_id: unsafe extern "C" fn(this: *mut Event) -> MpInteger,
}
iface!(Event, EventVTable);

#[repr(C)]
pub struct EventBpmVTable {
    pub add_ref: AddRefFn<EventBpm>,
    pub release: ReleaseFn<EventBpm>,
    pub query_interface: QueryInterfaceFn<EventBpm>,
    pub get_id: unsafe extern "C" fn(this: *mut EventBpm) -> MpInteger,
    pub get_info: unsafe extern "C" fn(this: *mut EventBpm, info: *mut EventBpmInfo),
    pub set_info: unsafe extern "C" fn(this: *mut EventBpm, info: *const EventBpmInfo),
    pub replace_with: unsafe extern "C" fn(this: *mut EventBpm, src: *const EventBpm),
    pub copy_info_to: unsafe extern "C" fn(this: *mut EventBpm, dest: *mut EventBpm),
}
iface!(EventBpm, EventBpmVTable);

#[repr(C)]
pub struct EventBeatVTable {
    pub add_ref: AddRefFn<EventBeat>,
    pub release: ReleaseFn<EventBeat>,
    pub query_interface: QueryInterfaceFn<EventBeat>,
    pub get_id: unsafe extern "C" fn(this: *mut EventBeat) -> MpInteger,
    pub get_info: unsafe extern "C" fn(this: *mut EventBeat, info: *mut EventBcInfo),
    pub set_info: unsafe extern "C" fn(this: *mut EventBeat, info: *const EventBcInfo),
    pub replace_with: unsafe extern "C" fn(this: *mut EventBeat, src: *const EventBeat),
    pub copy_info_to: unsafe extern "C" fn(this: *mut EventBeat, dest: *mut EventBeat),
}
iface!(EventBeat, EventBeatVTable);

#[repr(C)]
pub struct EventTlsVTable {
    pub add_ref: AddRefFn<EventTls>,
    pub release: ReleaseFn<EventTls>,
    pub query_interface: QueryInterfaceFn<EventTls>,
    pub get_id: unsafe extern "C" fn(this: *mut EventTls) -> MpInteger,
    pub get_info: unsafe extern "C" fn(this: *mut EventTls, info: *mut EventTlsInfo),
    pub set_info: unsafe extern "C" fn(this: *mut EventTls, info: *const EventTlsInfo),
    pub replace_with: unsafe extern "C" fn(this: *mut EventTls, src: *const EventTls),
    pub copy_info_to: unsafe extern "C" fn(this: *mut EventTls, dest: *mut EventTls),
}
iface!(EventTls, EventTlsVTable);

#[repr(C)]
pub struct EventNsmVTable {
    pub add_ref: AddRefFn<EventNsm>,
    pub release: ReleaseFn<EventNsm>,
    pub query_interface: QueryInterfaceFn<EventNsm>,
    pub get_id: unsafe extern "C" fn(this: *mut EventNsm) -> MpInteger,
    pub get_info: unsafe extern "C" fn(this: *mut EventNsm, info: *mut EventNsmInfo),
    pub set_info: unsafe extern "C" fn(this: *mut EventNsm, info: *const EventNsmInfo),
    pub replace_with: unsafe extern "C" fn(this: *mut EventNsm, src: *const EventNsm),
    pub copy_info_to: unsafe extern "C" fn(this: *mut EventNsm, dest: *mut EventNsm),
}
iface!(EventNsm, EventNsmVTable);
