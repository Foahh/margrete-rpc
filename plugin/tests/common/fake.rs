use margrete_rpc::abi::*;
use std::ffi::c_void;
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};

pub static APPEND_CHILD_RESULT: AtomicI32 = AtomicI32::new(MP_TRUE);

fn bump(count: &AtomicI32) -> MpInteger {
    count.fetch_add(1, Ordering::SeqCst) + 1
}

fn drop_ref(count: &AtomicI32) -> MpInteger {
    count.fetch_sub(1, Ordering::SeqCst) - 1
}

#[repr(C)]
pub struct FakeNote {
    vtable: *const NoteVTable,
    ref_count: AtomicI32,
    pub id: MpInteger,
    pub info: NoteInfo,
    pub children: Vec<*mut FakeNote>,
}

impl FakeNote {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &NOTE_VT,
            ref_count: AtomicI32::new(1),
            id: 1,
            info: NoteInfo::default(),
            children: Vec::new(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }

    fn from_ptr<'a>(ptr: *mut Note) -> &'a mut Self {
        unsafe { &mut *(ptr as *mut Self) }
    }
}

#[repr(C)]
pub struct FakeBpmEvent {
    vtable: *const EventBpmVTable,
    ref_count: AtomicI32,
    pub info: EventBpmInfo,
}

impl FakeBpmEvent {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &BPM_VT,
            ref_count: AtomicI32::new(1),
            info: EventBpmInfo::default(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }
}

#[repr(C)]
pub struct FakeBeatEvent {
    vtable: *const EventBeatVTable,
    ref_count: AtomicI32,
    pub info: EventBcInfo,
}

impl FakeBeatEvent {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &BEAT_VT,
            ref_count: AtomicI32::new(1),
            info: EventBcInfo::default(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }
}

#[repr(C)]
pub struct FakeTlsEvent {
    vtable: *const EventTlsVTable,
    ref_count: AtomicI32,
    pub info: EventTlsInfo,
}

impl FakeTlsEvent {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &TLS_VT,
            ref_count: AtomicI32::new(1),
            info: EventTlsInfo::default(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }
}

#[repr(C)]
pub struct FakeNsmEvent {
    vtable: *const EventNsmVTable,
    ref_count: AtomicI32,
    pub info: EventNsmInfo,
}

impl FakeNsmEvent {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &NSM_VT,
            ref_count: AtomicI32::new(1),
            info: EventNsmInfo::default(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }
}

#[repr(C)]
pub struct FakeChart {
    vtable: *const ChartVTable,
    ref_count: AtomicI32,
    pub notes: Vec<*mut FakeNote>,
    pub detached_notes: Vec<*mut FakeNote>,
    pub existing_bpm: Vec<*mut FakeBpmEvent>,
    pub existing_beat: Vec<*mut FakeBeatEvent>,
    pub existing_tls: Vec<*mut FakeTlsEvent>,
    pub existing_nsm: Vec<*mut FakeNsmEvent>,
    pub created_notes: Vec<*mut FakeNote>,
    pub created_bpm: Vec<*mut FakeBpmEvent>,
    pub created_beat: Vec<*mut FakeBeatEvent>,
    pub created_tls: Vec<*mut FakeTlsEvent>,
    pub created_nsm: Vec<*mut FakeNsmEvent>,
    allocated_notes: Vec<*mut FakeNote>,
    allocated_bpm: Vec<*mut FakeBpmEvent>,
    allocated_beat: Vec<*mut FakeBeatEvent>,
    allocated_tls: Vec<*mut FakeTlsEvent>,
    allocated_nsm: Vec<*mut FakeNsmEvent>,
    pub appended_notes: i32,
    pub appended_events: i32,
    pub deleted_notes: i32,
    pub deleted_events: i32,
    pub append_note_result: MpBoolean,
    pub append_event_result: MpBoolean,
    pub deleted_event_pointers: Vec<*mut Event>,
}

impl FakeChart {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &CHART_VT,
            ref_count: AtomicI32::new(1),
            notes: Vec::new(),
            detached_notes: Vec::new(),
            existing_bpm: Vec::new(),
            existing_beat: Vec::new(),
            existing_tls: Vec::new(),
            existing_nsm: Vec::new(),
            created_notes: Vec::new(),
            created_bpm: Vec::new(),
            created_beat: Vec::new(),
            created_tls: Vec::new(),
            created_nsm: Vec::new(),
            allocated_notes: Vec::new(),
            allocated_bpm: Vec::new(),
            allocated_beat: Vec::new(),
            allocated_tls: Vec::new(),
            allocated_nsm: Vec::new(),
            appended_notes: 0,
            appended_events: 0,
            deleted_notes: 0,
            deleted_events: 0,
            append_note_result: MP_TRUE,
            append_event_result: MP_TRUE,
            deleted_event_pointers: Vec::new(),
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }

    pub fn as_ptr(&self) -> *mut Chart {
        self as *const Self as *mut Chart
    }

    pub fn add_existing_note(&mut self, id: MpInteger) -> &mut FakeNote {
        let mut note = FakeNote::new();
        note.id = id;
        let ptr = Box::into_raw(note);
        self.allocated_notes.push(ptr);
        self.notes.push(ptr);
        unsafe { &mut *ptr }
    }

    pub fn add_detached_note(&mut self, id: MpInteger) -> &mut FakeNote {
        let mut note = FakeNote::new();
        note.id = id;
        let ptr = Box::into_raw(note);
        self.allocated_notes.push(ptr);
        self.detached_notes.push(ptr);
        unsafe { &mut *ptr }
    }

    pub fn add_existing_bpm(&mut self, tick: MpInteger, bpm: f64) -> &mut FakeBpmEvent {
        let mut event = FakeBpmEvent::new();
        event.info.tick = tick;
        event.info.bpm = bpm;
        let ptr = Box::into_raw(event);
        self.allocated_bpm.push(ptr);
        self.existing_bpm.push(ptr);
        unsafe { &mut *ptr }
    }

    pub fn add_existing_beat(
        &mut self,
        bar: MpInteger,
        beats_per_bar: MpInteger,
        beat_unit: MpInteger,
    ) -> &mut FakeBeatEvent {
        let mut event = FakeBeatEvent::new();
        event.info.bar = bar;
        event.info.beats_per_bar = beats_per_bar;
        event.info.beat_unit = beat_unit;
        let ptr = Box::into_raw(event);
        self.allocated_beat.push(ptr);
        self.existing_beat.push(ptr);
        unsafe { &mut *ptr }
    }

    pub fn add_existing_tls(
        &mut self,
        tick: MpInteger,
        timeline_id: MpInteger,
        speed: f64,
    ) -> &mut FakeTlsEvent {
        let mut event = FakeTlsEvent::new();
        event.info.tick = tick;
        event.info.timeline_id = timeline_id;
        event.info.speed = speed;
        let ptr = Box::into_raw(event);
        self.allocated_tls.push(ptr);
        self.existing_tls.push(ptr);
        unsafe { &mut *ptr }
    }

    pub fn add_existing_nsm(&mut self, tick: MpInteger, speed: f64) -> &mut FakeNsmEvent {
        let mut event = FakeNsmEvent::new();
        event.info.tick = tick;
        event.info.speed = speed;
        let ptr = Box::into_raw(event);
        self.allocated_nsm.push(ptr);
        self.existing_nsm.push(ptr);
        unsafe { &mut *ptr }
    }

    fn from_ptr<'a>(ptr: *mut Chart) -> &'a mut Self {
        unsafe { &mut *(ptr as *mut Self) }
    }
}

impl Drop for FakeChart {
    fn drop(&mut self) {
        unsafe {
            for ptr in self.allocated_notes.drain(..) {
                drop(Box::from_raw(ptr));
            }
            for ptr in self.allocated_bpm.drain(..) {
                drop(Box::from_raw(ptr));
            }
            for ptr in self.allocated_beat.drain(..) {
                drop(Box::from_raw(ptr));
            }
            for ptr in self.allocated_tls.drain(..) {
                drop(Box::from_raw(ptr));
            }
            for ptr in self.allocated_nsm.drain(..) {
                drop(Box::from_raw(ptr));
            }
        }
    }
}

#[repr(C)]
pub struct FakeUndo {
    vtable: *const UndoVTable,
    ref_count: AtomicI32,
    pub begin_count: i32,
    pub commit_count: i32,
    pub discard_count: i32,
    pub undo_count: i32,
    pub redo_count: i32,
    pub undo_result: MpBoolean,
    pub redo_result: MpBoolean,
    pub can_undo_result: MpBoolean,
    pub can_redo_result: MpBoolean,
}

impl FakeUndo {
    fn new() -> Box<Self> {
        Box::new(Self {
            vtable: &UNDO_VT,
            ref_count: AtomicI32::new(1),
            begin_count: 0,
            commit_count: 0,
            discard_count: 0,
            undo_count: 0,
            redo_count: 0,
            undo_result: MP_TRUE,
            redo_result: MP_TRUE,
            can_undo_result: MP_TRUE,
            can_redo_result: MP_TRUE,
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }

    fn from_ptr<'a>(ptr: *mut UndoBuffer) -> &'a mut Self {
        unsafe { &mut *(ptr as *mut Self) }
    }
}

#[repr(C)]
pub struct FakeDocument {
    vtable: *const DocumentVTable,
    ref_count: AtomicI32,
    chart: *mut FakeChart,
    undo: *mut FakeUndo,
}

impl FakeDocument {
    fn new(chart: *mut FakeChart, undo: *mut FakeUndo) -> Box<Self> {
        Box::new(Self {
            vtable: &DOCUMENT_VT,
            ref_count: AtomicI32::new(1),
            chart,
            undo,
        })
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.ref_count.load(Ordering::SeqCst)
    }

    fn from_ptr<'a>(ptr: *mut Document) -> &'a mut Self {
        unsafe { &mut *(ptr as *mut Self) }
    }
}

#[repr(C)]
struct FakeContextInner {
    vtable: *const ContextVTable,
    ref_count: AtomicI32,
    document: *mut FakeDocument,
    current_tick: MpInteger,
    updated: AtomicBool,
}

pub struct FakeContext {
    inner: Box<FakeContextInner>,
    document: Box<FakeDocument>,
    pub chart: Box<FakeChart>,
    pub undo: Box<FakeUndo>,
}

impl FakeContext {
    pub fn new() -> Self {
        let mut chart = FakeChart::new();
        let mut undo = FakeUndo::new();
        let chart_raw = &mut *chart as *mut FakeChart;
        let undo_raw = &mut *undo as *mut FakeUndo;
        let mut document = FakeDocument::new(chart_raw, undo_raw);
        let document_raw = &mut *document as *mut FakeDocument;
        let inner = Box::new(FakeContextInner {
            vtable: &CONTEXT_VT,
            ref_count: AtomicI32::new(1),
            document: document_raw,
            current_tick: 960,
            updated: AtomicBool::new(false),
        });
        Self {
            inner,
            document,
            chart,
            undo,
        }
    }

    pub fn as_ptr(&self) -> *mut Context {
        &*self.inner as *const FakeContextInner as *mut Context
    }

    pub fn ref_count_value(&self) -> MpInteger {
        self.inner.ref_count.load(Ordering::SeqCst)
    }

    pub fn current_tick(&self) -> MpInteger {
        self.inner.current_tick
    }

    pub fn set_current_tick(&mut self, tick: MpInteger) {
        self.inner.current_tick = tick;
    }

    pub fn updated(&self) -> bool {
        self.inner.updated.load(Ordering::SeqCst)
    }

    pub fn document(&self) -> &FakeDocument {
        &self.document
    }
}

impl Default for FakeContext {
    fn default() -> Self {
        Self::new()
    }
}

fn inner_from_ctx<'a>(ptr: *mut Context) -> &'a mut FakeContextInner {
    unsafe { &mut *(ptr as *mut FakeContextInner) }
}

static NOTE_VT: NoteVTable = NoteVTable {
    add_ref: note_add_ref,
    release: note_release,
    query_interface: note_qi,
    get_id: note_get_id,
    get_info: note_get_info,
    set_info: note_set_info,
    get_children_count: note_children_count,
    get_child: note_get_child,
    get_parent: note_get_parent,
    append_child: note_append_child,
    delete_child: note_delete_child,
    clone: note_clone,
    replace_with: note_replace_with,
    copy_info_to: note_copy_info_to,
    get_base_note: note_get_base,
    offset_child: note_offset_child,
    flip_h: note_flip_h,
};

unsafe extern "C" fn note_add_ref(this: *mut Note) -> MpInteger {
    bump(&FakeNote::from_ptr(this).ref_count)
}
unsafe extern "C" fn note_release(this: *mut Note) -> MpInteger {
    drop_ref(&FakeNote::from_ptr(this).ref_count)
}
unsafe extern "C" fn note_qi(
    _this: *mut Note,
    _iid: *const MpGuid,
    _pp: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn note_get_id(this: *mut Note) -> MpInteger {
    FakeNote::from_ptr(this).id
}
unsafe extern "C" fn note_get_info(this: *mut Note, info: *mut NoteInfo) {
    unsafe {
        if !info.is_null() {
            *info = FakeNote::from_ptr(this).info;
        }
    }
}
unsafe extern "C" fn note_set_info(this: *mut Note, info: *const NoteInfo) {
    unsafe {
        if !info.is_null() {
            FakeNote::from_ptr(this).info = *info;
        }
    }
}
unsafe extern "C" fn note_children_count(this: *mut Note) -> MpInteger {
    FakeNote::from_ptr(this).children.len() as MpInteger
}
unsafe extern "C" fn note_get_child(
    this: *mut Note,
    index: MpInteger,
    ppobj: *mut *mut Note,
) -> MpBoolean {
    unsafe {
        let note = FakeNote::from_ptr(this);
        if index < 0 || index as usize >= note.children.len() {
            return MP_FALSE;
        }
        let child = note.children[index as usize];
        bump(&(*child).ref_count);
        *ppobj = child as *mut Note;
        MP_TRUE
    }
}
unsafe extern "C" fn note_get_parent(_this: *mut Note, _pp: *mut *mut Note) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn note_append_child(this: *mut Note, child: *mut Note) -> MpBoolean {
    let result = APPEND_CHILD_RESULT.load(Ordering::SeqCst);
    if result != MP_TRUE {
        return result;
    }
    FakeNote::from_ptr(this)
        .children
        .push(child as *mut FakeNote);
    MP_TRUE
}
unsafe extern "C" fn note_delete_child(_this: *mut Note, _child: *mut Note) -> MpBoolean {
    MP_TRUE
}
unsafe extern "C" fn note_clone(_this: *mut Note, _pp: *mut *mut Note) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn note_replace_with(_this: *mut Note, _src: *const Note, _sort: MpBoolean) {}
unsafe extern "C" fn note_copy_info_to(_this: *mut Note, _dest: *mut Note) {}
unsafe extern "C" fn note_get_base(_this: *mut Note, _pp: *mut *mut Note) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn note_offset_child(_this: *mut Note, _tick: MpInteger) {}
unsafe extern "C" fn note_flip_h(_this: *mut Note, _recursive: MpBoolean) {}

macro_rules! event_vt {
    ($add:ident, $rel:ident, $ty:ty, $iface:ty, $field:ident) => {
        unsafe extern "C" fn $add(this: *mut $iface) -> MpInteger {
            unsafe { bump(&(*(this as *mut $ty)).ref_count) }
        }
        unsafe extern "C" fn $rel(this: *mut $iface) -> MpInteger {
            unsafe { drop_ref(&(*(this as *mut $ty)).ref_count) }
        }
    };
}

event_vt!(bpm_add_ref, bpm_release, FakeBpmEvent, EventBpm, info);
event_vt!(beat_add_ref, beat_release, FakeBeatEvent, EventBeat, info);
event_vt!(tls_add_ref, tls_release, FakeTlsEvent, EventTls, info);
event_vt!(nsm_add_ref, nsm_release, FakeNsmEvent, EventNsm, info);

unsafe extern "C" fn bpm_qi(
    _t: *mut EventBpm,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn bpm_id(_t: *mut EventBpm) -> MpInteger {
    1
}
unsafe extern "C" fn bpm_get(this: *mut EventBpm, info: *mut EventBpmInfo) {
    unsafe {
        *info = (*(this as *mut FakeBpmEvent)).info;
    }
}
unsafe extern "C" fn bpm_set(this: *mut EventBpm, info: *const EventBpmInfo) {
    unsafe {
        (*(this as *mut FakeBpmEvent)).info = *info;
    }
}
unsafe extern "C" fn bpm_replace(_t: *mut EventBpm, _s: *const EventBpm) {}
unsafe extern "C" fn bpm_copy(_t: *mut EventBpm, _d: *mut EventBpm) {}

unsafe extern "C" fn beat_qi(
    _t: *mut EventBeat,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn beat_id(_t: *mut EventBeat) -> MpInteger {
    1
}
unsafe extern "C" fn beat_get(this: *mut EventBeat, info: *mut EventBcInfo) {
    unsafe {
        *info = (*(this as *mut FakeBeatEvent)).info;
    }
}
unsafe extern "C" fn beat_set(this: *mut EventBeat, info: *const EventBcInfo) {
    unsafe {
        (*(this as *mut FakeBeatEvent)).info = *info;
    }
}
unsafe extern "C" fn beat_replace(_t: *mut EventBeat, _s: *const EventBeat) {}
unsafe extern "C" fn beat_copy(_t: *mut EventBeat, _d: *mut EventBeat) {}

unsafe extern "C" fn tls_qi(
    _t: *mut EventTls,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn tls_id(_t: *mut EventTls) -> MpInteger {
    1
}
unsafe extern "C" fn tls_get(this: *mut EventTls, info: *mut EventTlsInfo) {
    unsafe {
        *info = (*(this as *mut FakeTlsEvent)).info;
    }
}
unsafe extern "C" fn tls_set(this: *mut EventTls, info: *const EventTlsInfo) {
    unsafe {
        (*(this as *mut FakeTlsEvent)).info = *info;
    }
}
unsafe extern "C" fn tls_replace(_t: *mut EventTls, _s: *const EventTls) {}
unsafe extern "C" fn tls_copy(_t: *mut EventTls, _d: *mut EventTls) {}

unsafe extern "C" fn nsm_qi(
    _t: *mut EventNsm,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn nsm_id(_t: *mut EventNsm) -> MpInteger {
    1
}
unsafe extern "C" fn nsm_get(this: *mut EventNsm, info: *mut EventNsmInfo) {
    unsafe {
        *info = (*(this as *mut FakeNsmEvent)).info;
    }
}
unsafe extern "C" fn nsm_set(this: *mut EventNsm, info: *const EventNsmInfo) {
    unsafe {
        (*(this as *mut FakeNsmEvent)).info = *info;
    }
}
unsafe extern "C" fn nsm_replace(_t: *mut EventNsm, _s: *const EventNsm) {}
unsafe extern "C" fn nsm_copy(_t: *mut EventNsm, _d: *mut EventNsm) {}

static BPM_VT: EventBpmVTable = EventBpmVTable {
    add_ref: bpm_add_ref,
    release: bpm_release,
    query_interface: bpm_qi,
    get_id: bpm_id,
    get_info: bpm_get,
    set_info: bpm_set,
    replace_with: bpm_replace,
    copy_info_to: bpm_copy,
};
static BEAT_VT: EventBeatVTable = EventBeatVTable {
    add_ref: beat_add_ref,
    release: beat_release,
    query_interface: beat_qi,
    get_id: beat_id,
    get_info: beat_get,
    set_info: beat_set,
    replace_with: beat_replace,
    copy_info_to: beat_copy,
};
static TLS_VT: EventTlsVTable = EventTlsVTable {
    add_ref: tls_add_ref,
    release: tls_release,
    query_interface: tls_qi,
    get_id: tls_id,
    get_info: tls_get,
    set_info: tls_set,
    replace_with: tls_replace,
    copy_info_to: tls_copy,
};
static NSM_VT: EventNsmVTable = EventNsmVTable {
    add_ref: nsm_add_ref,
    release: nsm_release,
    query_interface: nsm_qi,
    get_id: nsm_id,
    get_info: nsm_get,
    set_info: nsm_set,
    replace_with: nsm_replace,
    copy_info_to: nsm_copy,
};

static CHART_VT: ChartVTable = ChartVTable {
    add_ref: chart_add_ref,
    release: chart_release,
    query_interface: chart_qi,
    create_note: chart_create_note,
    get_notes_count: chart_notes_count,
    get_note: chart_get_note,
    append_note: chart_append_note,
    delete_note: chart_delete_note,
    offset_notes: chart_offset_notes,
    create_event: chart_create_event,
    append_event: chart_append_event,
    delete_event: chart_delete_event,
    find_event_timeline_speed: chart_find_tls,
    find_event_note_speed_modifier: chart_find_nsm,
    find_event_bpm: chart_find_bpm,
    find_event_beat_change: chart_find_beat,
};

unsafe extern "C" fn chart_add_ref(this: *mut Chart) -> MpInteger {
    bump(&FakeChart::from_ptr(this).ref_count)
}
unsafe extern "C" fn chart_release(this: *mut Chart) -> MpInteger {
    drop_ref(&FakeChart::from_ptr(this).ref_count)
}
unsafe extern "C" fn chart_qi(
    _t: *mut Chart,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn chart_create_note(this: *mut Chart, ppobj: *mut *mut Note) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        let note = Box::into_raw(FakeNote::new());
        chart.allocated_notes.push(note);
        chart.created_notes.push(note);
        *ppobj = note as *mut Note;
        MP_TRUE
    }
}
unsafe extern "C" fn chart_notes_count(this: *mut Chart) -> MpInteger {
    FakeChart::from_ptr(this).notes.len() as MpInteger
}
unsafe extern "C" fn chart_get_note(
    this: *mut Chart,
    index: MpInteger,
    ppobj: *mut *mut Note,
) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        if index < 0 || index as usize >= chart.notes.len() {
            return MP_FALSE;
        }
        let note = chart.notes[index as usize];
        bump(&(*note).ref_count);
        *ppobj = note as *mut Note;
        MP_TRUE
    }
}
unsafe extern "C" fn chart_append_note(this: *mut Chart, note: *mut Note) -> MpBoolean {
    let chart = FakeChart::from_ptr(this);
    chart.appended_notes += 1;
    if chart.append_note_result != MP_TRUE {
        return chart.append_note_result;
    }
    chart.notes.push(note as *mut FakeNote);
    MP_TRUE
}
unsafe extern "C" fn chart_delete_note(this: *mut Chart, note: *mut Note) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        chart.deleted_notes += 1;
        let fake = note as *mut FakeNote;
        let old = chart.notes.len();
        chart.notes.retain(|n| *n != fake);
        if chart.notes.len() != old {
            drop_ref(&(*fake).ref_count);
        }
        MP_TRUE
    }
}
unsafe extern "C" fn chart_offset_notes(_this: *mut Chart, _tick: MpInteger) {}
unsafe extern "C" fn chart_create_event(
    this: *mut Chart,
    iid: *const MpGuid,
    ppobj: *mut *mut c_void,
) -> MpBoolean {
    unsafe {
        if ppobj.is_null() || iid.is_null() {
            return MP_FALSE;
        }
        let chart = FakeChart::from_ptr(this);
        let iid = &*iid;
        if iid.eq_guid(&IID_EVENT_BPM) {
            let event = Box::into_raw(FakeBpmEvent::new());
            chart.allocated_bpm.push(event);
            chart.created_bpm.push(event);
            *ppobj = event as *mut c_void;
            return MP_TRUE;
        }
        if iid.eq_guid(&IID_EVENT_BEAT) {
            let event = Box::into_raw(FakeBeatEvent::new());
            chart.allocated_beat.push(event);
            chart.created_beat.push(event);
            *ppobj = event as *mut c_void;
            return MP_TRUE;
        }
        if iid.eq_guid(&IID_EVENT_TLS) {
            let event = Box::into_raw(FakeTlsEvent::new());
            chart.allocated_tls.push(event);
            chart.created_tls.push(event);
            *ppobj = event as *mut c_void;
            return MP_TRUE;
        }
        if iid.eq_guid(&IID_EVENT_NSM) {
            let event = Box::into_raw(FakeNsmEvent::new());
            chart.allocated_nsm.push(event);
            chart.created_nsm.push(event);
            *ppobj = event as *mut c_void;
            return MP_TRUE;
        }
        MP_FALSE
    }
}
unsafe extern "C" fn chart_append_event(this: *mut Chart, event: *mut Event) -> MpBoolean {
    let chart = FakeChart::from_ptr(this);
    chart.appended_events += 1;
    if chart.append_event_result != MP_TRUE {
        return chart.append_event_result;
    }
    if chart
        .allocated_bpm
        .iter()
        .any(|p| *p as *mut Event == event)
    {
        chart.existing_bpm.push(event as *mut FakeBpmEvent);
    } else if chart
        .allocated_beat
        .iter()
        .any(|p| *p as *mut Event == event)
    {
        chart.existing_beat.push(event as *mut FakeBeatEvent);
    } else if chart
        .allocated_tls
        .iter()
        .any(|p| *p as *mut Event == event)
    {
        chart.existing_tls.push(event as *mut FakeTlsEvent);
    } else if chart
        .allocated_nsm
        .iter()
        .any(|p| *p as *mut Event == event)
    {
        chart.existing_nsm.push(event as *mut FakeNsmEvent);
    }
    MP_TRUE
}
unsafe extern "C" fn chart_delete_event(this: *mut Chart, event: *mut Event) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        chart.deleted_events += 1;
        chart.deleted_event_pointers.push(event);
        let mut removed = false;
        let old = chart.existing_bpm.len();
        chart.existing_bpm.retain(|p| *p as *mut Event != event);
        removed |= chart.existing_bpm.len() != old;
        let old = chart.existing_beat.len();
        chart.existing_beat.retain(|p| *p as *mut Event != event);
        removed |= chart.existing_beat.len() != old;
        let old = chart.existing_tls.len();
        chart.existing_tls.retain(|p| *p as *mut Event != event);
        removed |= chart.existing_tls.len() != old;
        let old = chart.existing_nsm.len();
        chart.existing_nsm.retain(|p| *p as *mut Event != event);
        removed |= chart.existing_nsm.len() != old;
        if removed {
            let _ = Event::release(event);
        }
        MP_TRUE
    }
}
unsafe extern "C" fn chart_find_tls(
    this: *mut Chart,
    tick: MpInteger,
    timeline_id: MpInteger,
    ppobj: *mut *mut c_void,
) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        for event in &chart.existing_tls {
            if (**event).info.tick == tick && (**event).info.timeline_id == timeline_id {
                bump(&(**event).ref_count);
                *ppobj = *event as *mut c_void;
                return MP_TRUE;
            }
        }
        MP_FALSE
    }
}
unsafe extern "C" fn chart_find_nsm(
    this: *mut Chart,
    tick: MpInteger,
    ppobj: *mut *mut c_void,
) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        for event in &chart.existing_nsm {
            if (**event).info.tick == tick {
                bump(&(**event).ref_count);
                *ppobj = *event as *mut c_void;
                return MP_TRUE;
            }
        }
        MP_FALSE
    }
}
unsafe extern "C" fn chart_find_bpm(
    this: *mut Chart,
    tick: MpInteger,
    ppobj: *mut *mut c_void,
) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        for event in &chart.existing_bpm {
            if (**event).info.tick == tick {
                bump(&(**event).ref_count);
                *ppobj = *event as *mut c_void;
                return MP_TRUE;
            }
        }
        MP_FALSE
    }
}
unsafe extern "C" fn chart_find_beat(
    this: *mut Chart,
    bar: MpInteger,
    ppobj: *mut *mut c_void,
) -> MpBoolean {
    unsafe {
        let chart = FakeChart::from_ptr(this);
        for event in &chart.existing_beat {
            if (**event).info.bar == bar {
                bump(&(**event).ref_count);
                *ppobj = *event as *mut c_void;
                return MP_TRUE;
            }
        }
        MP_FALSE
    }
}

static UNDO_VT: UndoVTable = UndoVTable {
    add_ref: undo_add_ref,
    release: undo_release,
    query_interface: undo_qi,
    begin_recording: undo_begin,
    commit_recording: undo_commit,
    discard_recording: undo_discard,
    undo: undo_undo,
    redo: undo_redo,
    can_undo: undo_can_undo,
    can_redo: undo_can_redo,
    is_recording: undo_is_recording,
};

unsafe extern "C" fn undo_add_ref(this: *mut UndoBuffer) -> MpInteger {
    bump(&FakeUndo::from_ptr(this).ref_count)
}
unsafe extern "C" fn undo_release(this: *mut UndoBuffer) -> MpInteger {
    drop_ref(&FakeUndo::from_ptr(this).ref_count)
}
unsafe extern "C" fn undo_qi(
    _t: *mut UndoBuffer,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn undo_begin(this: *mut UndoBuffer) -> MpBoolean {
    FakeUndo::from_ptr(this).begin_count += 1;
    MP_TRUE
}
unsafe extern "C" fn undo_commit(this: *mut UndoBuffer) -> MpBoolean {
    FakeUndo::from_ptr(this).commit_count += 1;
    MP_TRUE
}
unsafe extern "C" fn undo_discard(this: *mut UndoBuffer) -> MpBoolean {
    FakeUndo::from_ptr(this).discard_count += 1;
    MP_TRUE
}
unsafe extern "C" fn undo_undo(this: *mut UndoBuffer) -> MpBoolean {
    let undo = FakeUndo::from_ptr(this);
    undo.undo_count += 1;
    undo.undo_result
}
unsafe extern "C" fn undo_redo(this: *mut UndoBuffer) -> MpBoolean {
    let undo = FakeUndo::from_ptr(this);
    undo.redo_count += 1;
    undo.redo_result
}
unsafe extern "C" fn undo_can_undo(this: *mut UndoBuffer) -> MpBoolean {
    FakeUndo::from_ptr(this).can_undo_result
}
unsafe extern "C" fn undo_can_redo(this: *mut UndoBuffer) -> MpBoolean {
    FakeUndo::from_ptr(this).can_redo_result
}
unsafe extern "C" fn undo_is_recording(this: *mut UndoBuffer) -> MpBoolean {
    let undo = FakeUndo::from_ptr(this);
    if undo.begin_count > undo.commit_count + undo.discard_count {
        MP_TRUE
    } else {
        MP_FALSE
    }
}

static DOCUMENT_VT: DocumentVTable = DocumentVTable {
    add_ref: doc_add_ref,
    release: doc_release,
    query_interface: doc_qi,
    get_chart: doc_get_chart,
    get_undo_buffer: doc_get_undo,
};

unsafe extern "C" fn doc_add_ref(this: *mut Document) -> MpInteger {
    bump(&FakeDocument::from_ptr(this).ref_count)
}
unsafe extern "C" fn doc_release(this: *mut Document) -> MpInteger {
    drop_ref(&FakeDocument::from_ptr(this).ref_count)
}
unsafe extern "C" fn doc_qi(
    _t: *mut Document,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn doc_get_chart(this: *mut Document, ppobj: *mut *mut Chart) -> MpBoolean {
    unsafe {
        let doc = FakeDocument::from_ptr(this);
        bump(&(*doc.chart).ref_count);
        *ppobj = doc.chart as *mut Chart;
        MP_TRUE
    }
}
unsafe extern "C" fn doc_get_undo(this: *mut Document, ppobj: *mut *mut UndoBuffer) -> MpBoolean {
    unsafe {
        let doc = FakeDocument::from_ptr(this);
        bump(&(*doc.undo).ref_count);
        *ppobj = doc.undo as *mut UndoBuffer;
        MP_TRUE
    }
}

static CONTEXT_VT: ContextVTable = ContextVTable {
    add_ref: ctx_add_ref,
    release: ctx_release,
    query_interface: ctx_qi,
    get_document: ctx_get_document,
    get_main_window_handle: ctx_hwnd,
    get_current_tick: ctx_tick,
    update: ctx_update,
};

unsafe extern "C" fn ctx_add_ref(this: *mut Context) -> MpInteger {
    bump(&inner_from_ctx(this).ref_count)
}
unsafe extern "C" fn ctx_release(this: *mut Context) -> MpInteger {
    drop_ref(&inner_from_ctx(this).ref_count)
}
unsafe extern "C" fn ctx_qi(
    _t: *mut Context,
    _i: *const MpGuid,
    _p: *mut *mut c_void,
) -> MpBoolean {
    MP_FALSE
}
unsafe extern "C" fn ctx_get_document(this: *mut Context, ppobj: *mut *mut Document) -> MpBoolean {
    unsafe {
        let inner = inner_from_ctx(this);
        bump(&(*inner.document).ref_count);
        *ppobj = inner.document as *mut Document;
        MP_TRUE
    }
}
unsafe extern "C" fn ctx_hwnd(_this: *mut Context) -> *mut c_void {
    std::ptr::null_mut()
}
unsafe extern "C" fn ctx_tick(this: *mut Context) -> MpInteger {
    inner_from_ctx(this).current_tick
}
unsafe extern "C" fn ctx_update(this: *mut Context) {
    inner_from_ctx(this).updated.store(true, Ordering::SeqCst);
}
