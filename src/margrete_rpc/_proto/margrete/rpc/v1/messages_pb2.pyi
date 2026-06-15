from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_CODE_UNSPECIFIED: _ClassVar[ErrorCode]
    ERROR_CODE_UNAVAILABLE: _ClassVar[ErrorCode]
    ERROR_CODE_INVALID_ARGUMENT: _ClassVar[ErrorCode]
    ERROR_CODE_FAILED_PRECONDITION: _ClassVar[ErrorCode]
    ERROR_CODE_INTERNAL: _ClassVar[ErrorCode]

class NoteType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOTE_TYPE_UNKNOWN: _ClassVar[NoteType]
    NOTE_TYPE_TAP: _ClassVar[NoteType]
    NOTE_TYPE_EXTAP: _ClassVar[NoteType]
    NOTE_TYPE_FLICK: _ClassVar[NoteType]
    NOTE_TYPE_DAMAGE: _ClassVar[NoteType]
    NOTE_TYPE_HOLD: _ClassVar[NoteType]
    NOTE_TYPE_SLIDE: _ClassVar[NoteType]
    NOTE_TYPE_AIR: _ClassVar[NoteType]
    NOTE_TYPE_AIRHOLD: _ClassVar[NoteType]
    NOTE_TYPE_AIRSLIDE: _ClassVar[NoteType]
    NOTE_TYPE_AIRCRUSH: _ClassVar[NoteType]
    NOTE_TYPE_CLICK: _ClassVar[NoteType]

class LongAttr(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LONG_ATTR_NONE: _ClassVar[LongAttr]
    LONG_ATTR_BEGIN: _ClassVar[LongAttr]
    LONG_ATTR_STEP: _ClassVar[LongAttr]
    LONG_ATTR_CONTROL: _ClassVar[LongAttr]
    LONG_ATTR_CURVE_CONTROL: _ClassVar[LongAttr]
    LONG_ATTR_END: _ClassVar[LongAttr]
    LONG_ATTR_END_NOACT: _ClassVar[LongAttr]

class Direction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DIRECTION_NONE: _ClassVar[Direction]
    DIRECTION_AUTO: _ClassVar[Direction]
    DIRECTION_UP: _ClassVar[Direction]
    DIRECTION_DOWN: _ClassVar[Direction]
    DIRECTION_CENTER: _ClassVar[Direction]
    DIRECTION_LEFT: _ClassVar[Direction]
    DIRECTION_RIGHT: _ClassVar[Direction]
    DIRECTION_UPLEFT: _ClassVar[Direction]
    DIRECTION_UPRIGHT: _ClassVar[Direction]
    DIRECTION_DOWNLEFT: _ClassVar[Direction]
    DIRECTION_DOWNRIGHT: _ClassVar[Direction]
    DIRECTION_ROTATE_LEFT: _ClassVar[Direction]
    DIRECTION_ROTATE_RIGHT: _ClassVar[Direction]
    DIRECTION_INOUT: _ClassVar[Direction]
    DIRECTION_OUTIN: _ClassVar[Direction]

class ExAttr(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EX_ATTR_NONE: _ClassVar[ExAttr]
    EX_ATTR_INVERT: _ClassVar[ExAttr]
    EX_ATTR_HAS_NOTE: _ClassVar[ExAttr]
    EX_ATTR_EXJDG: _ClassVar[ExAttr]

class Color(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COLOR_DEFAULT: _ClassVar[Color]
    COLOR_RED: _ClassVar[Color]
    COLOR_ORANGE: _ClassVar[Color]
    COLOR_YELLOW: _ClassVar[Color]
    COLOR_GREEN: _ClassVar[Color]
    COLOR_SKY: _ClassVar[Color]
    COLOR_BLUE: _ClassVar[Color]
    COLOR_VIOLET: _ClassVar[Color]
    COLOR_PINK: _ClassVar[Color]
    COLOR_WHITE: _ClassVar[Color]
    COLOR_BLACK: _ClassVar[Color]
    COLOR_GRASS: _ClassVar[Color]
    COLOR_SKY_BLUE: _ClassVar[Color]
    COLOR_COBALT_BLUE: _ClassVar[Color]
    COLOR_PURPLE: _ClassVar[Color]
    COLOR_NONE: _ClassVar[Color]
ERROR_CODE_UNSPECIFIED: ErrorCode
ERROR_CODE_UNAVAILABLE: ErrorCode
ERROR_CODE_INVALID_ARGUMENT: ErrorCode
ERROR_CODE_FAILED_PRECONDITION: ErrorCode
ERROR_CODE_INTERNAL: ErrorCode
NOTE_TYPE_UNKNOWN: NoteType
NOTE_TYPE_TAP: NoteType
NOTE_TYPE_EXTAP: NoteType
NOTE_TYPE_FLICK: NoteType
NOTE_TYPE_DAMAGE: NoteType
NOTE_TYPE_HOLD: NoteType
NOTE_TYPE_SLIDE: NoteType
NOTE_TYPE_AIR: NoteType
NOTE_TYPE_AIRHOLD: NoteType
NOTE_TYPE_AIRSLIDE: NoteType
NOTE_TYPE_AIRCRUSH: NoteType
NOTE_TYPE_CLICK: NoteType
LONG_ATTR_NONE: LongAttr
LONG_ATTR_BEGIN: LongAttr
LONG_ATTR_STEP: LongAttr
LONG_ATTR_CONTROL: LongAttr
LONG_ATTR_CURVE_CONTROL: LongAttr
LONG_ATTR_END: LongAttr
LONG_ATTR_END_NOACT: LongAttr
DIRECTION_NONE: Direction
DIRECTION_AUTO: Direction
DIRECTION_UP: Direction
DIRECTION_DOWN: Direction
DIRECTION_CENTER: Direction
DIRECTION_LEFT: Direction
DIRECTION_RIGHT: Direction
DIRECTION_UPLEFT: Direction
DIRECTION_UPRIGHT: Direction
DIRECTION_DOWNLEFT: Direction
DIRECTION_DOWNRIGHT: Direction
DIRECTION_ROTATE_LEFT: Direction
DIRECTION_ROTATE_RIGHT: Direction
DIRECTION_INOUT: Direction
DIRECTION_OUTIN: Direction
EX_ATTR_NONE: ExAttr
EX_ATTR_INVERT: ExAttr
EX_ATTR_HAS_NOTE: ExAttr
EX_ATTR_EXJDG: ExAttr
COLOR_DEFAULT: Color
COLOR_RED: Color
COLOR_ORANGE: Color
COLOR_YELLOW: Color
COLOR_GREEN: Color
COLOR_SKY: Color
COLOR_BLUE: Color
COLOR_VIOLET: Color
COLOR_PINK: Color
COLOR_WHITE: Color
COLOR_BLACK: Color
COLOR_GRASS: Color
COLOR_SKY_BLUE: Color
COLOR_COBALT_BLUE: Color
COLOR_PURPLE: Color
COLOR_NONE: Color

class Envelope(_message.Message):
    __slots__ = ("request_id", "ping_request", "ping_response", "begin_edit_request", "begin_edit_response", "apply_edit_request", "apply_edit_response", "undo_request", "undo_response", "redo_request", "redo_response", "current_tick_request", "current_tick_response", "status_request", "status_response", "error_response")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    PING_REQUEST_FIELD_NUMBER: _ClassVar[int]
    PING_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    BEGIN_EDIT_REQUEST_FIELD_NUMBER: _ClassVar[int]
    BEGIN_EDIT_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    APPLY_EDIT_REQUEST_FIELD_NUMBER: _ClassVar[int]
    APPLY_EDIT_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    UNDO_REQUEST_FIELD_NUMBER: _ClassVar[int]
    UNDO_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    REDO_REQUEST_FIELD_NUMBER: _ClassVar[int]
    REDO_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TICK_REQUEST_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TICK_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    STATUS_REQUEST_FIELD_NUMBER: _ClassVar[int]
    STATUS_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    ERROR_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    request_id: int
    ping_request: PingRequest
    ping_response: PingResponse
    begin_edit_request: BeginEditRequest
    begin_edit_response: BeginEditResponse
    apply_edit_request: ApplyEditRequest
    apply_edit_response: ApplyEditResponse
    undo_request: UndoRequest
    undo_response: UndoResponse
    redo_request: RedoRequest
    redo_response: RedoResponse
    current_tick_request: CurrentTickRequest
    current_tick_response: CurrentTickResponse
    status_request: StatusRequest
    status_response: StatusResponse
    error_response: ErrorResponse
    def __init__(self, request_id: _Optional[int] = ..., ping_request: _Optional[_Union[PingRequest, _Mapping]] = ..., ping_response: _Optional[_Union[PingResponse, _Mapping]] = ..., begin_edit_request: _Optional[_Union[BeginEditRequest, _Mapping]] = ..., begin_edit_response: _Optional[_Union[BeginEditResponse, _Mapping]] = ..., apply_edit_request: _Optional[_Union[ApplyEditRequest, _Mapping]] = ..., apply_edit_response: _Optional[_Union[ApplyEditResponse, _Mapping]] = ..., undo_request: _Optional[_Union[UndoRequest, _Mapping]] = ..., undo_response: _Optional[_Union[UndoResponse, _Mapping]] = ..., redo_request: _Optional[_Union[RedoRequest, _Mapping]] = ..., redo_response: _Optional[_Union[RedoResponse, _Mapping]] = ..., current_tick_request: _Optional[_Union[CurrentTickRequest, _Mapping]] = ..., current_tick_response: _Optional[_Union[CurrentTickResponse, _Mapping]] = ..., status_request: _Optional[_Union[StatusRequest, _Mapping]] = ..., status_response: _Optional[_Union[StatusResponse, _Mapping]] = ..., error_response: _Optional[_Union[ErrorResponse, _Mapping]] = ...) -> None: ...

class PingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PingResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StatusResponse(_message.Message):
    __slots__ = ("server_name", "server_version", "server_build_time", "instance_id", "uptime", "pid", "log_path", "config_path")
    SERVER_NAME_FIELD_NUMBER: _ClassVar[int]
    SERVER_VERSION_FIELD_NUMBER: _ClassVar[int]
    SERVER_BUILD_TIME_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    UPTIME_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    LOG_PATH_FIELD_NUMBER: _ClassVar[int]
    CONFIG_PATH_FIELD_NUMBER: _ClassVar[int]
    server_name: str
    server_version: str
    server_build_time: str
    instance_id: str
    uptime: int
    pid: int
    log_path: str
    config_path: str
    def __init__(self, server_name: _Optional[str] = ..., server_version: _Optional[str] = ..., server_build_time: _Optional[str] = ..., instance_id: _Optional[str] = ..., uptime: _Optional[int] = ..., pid: _Optional[int] = ..., log_path: _Optional[str] = ..., config_path: _Optional[str] = ...) -> None: ...

class Note(_message.Message):
    __slots__ = ("id", "type", "long_attr", "direction", "ex_attr", "variation_id", "x", "width", "height", "tick", "timeline_id", "option_value", "children")
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LONG_ATTR_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    EX_ATTR_FIELD_NUMBER: _ClassVar[int]
    VARIATION_ID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TICK_FIELD_NUMBER: _ClassVar[int]
    TIMELINE_ID_FIELD_NUMBER: _ClassVar[int]
    OPTION_VALUE_FIELD_NUMBER: _ClassVar[int]
    CHILDREN_FIELD_NUMBER: _ClassVar[int]
    id: int
    type: NoteType
    long_attr: LongAttr
    direction: Direction
    ex_attr: ExAttr
    variation_id: Color
    x: int
    width: int
    height: int
    tick: int
    timeline_id: int
    option_value: int
    children: _containers.RepeatedCompositeFieldContainer[Note]
    def __init__(self, id: _Optional[int] = ..., type: _Optional[_Union[NoteType, str]] = ..., long_attr: _Optional[_Union[LongAttr, str]] = ..., direction: _Optional[_Union[Direction, str]] = ..., ex_attr: _Optional[_Union[ExAttr, str]] = ..., variation_id: _Optional[_Union[Color, str]] = ..., x: _Optional[int] = ..., width: _Optional[int] = ..., height: _Optional[int] = ..., tick: _Optional[int] = ..., timeline_id: _Optional[int] = ..., option_value: _Optional[int] = ..., children: _Optional[_Iterable[_Union[Note, _Mapping]]] = ...) -> None: ...

class BpmEvent(_message.Message):
    __slots__ = ("tick", "bpm")
    TICK_FIELD_NUMBER: _ClassVar[int]
    BPM_FIELD_NUMBER: _ClassVar[int]
    tick: int
    bpm: float
    def __init__(self, tick: _Optional[int] = ..., bpm: _Optional[float] = ...) -> None: ...

class BeatChangeEvent(_message.Message):
    __slots__ = ("bar", "beats_per_bar", "beat_unit")
    BAR_FIELD_NUMBER: _ClassVar[int]
    BEATS_PER_BAR_FIELD_NUMBER: _ClassVar[int]
    BEAT_UNIT_FIELD_NUMBER: _ClassVar[int]
    bar: int
    beats_per_bar: int
    beat_unit: int
    def __init__(self, bar: _Optional[int] = ..., beats_per_bar: _Optional[int] = ..., beat_unit: _Optional[int] = ...) -> None: ...

class TimelineSpeedEvent(_message.Message):
    __slots__ = ("tick", "timeline_id", "speed")
    TICK_FIELD_NUMBER: _ClassVar[int]
    TIMELINE_ID_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    tick: int
    timeline_id: int
    speed: float
    def __init__(self, tick: _Optional[int] = ..., timeline_id: _Optional[int] = ..., speed: _Optional[float] = ...) -> None: ...

class NoteSpeedEvent(_message.Message):
    __slots__ = ("tick", "speed")
    TICK_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    tick: int
    speed: float
    def __init__(self, tick: _Optional[int] = ..., speed: _Optional[float] = ...) -> None: ...

class BeginEditRequest(_message.Message):
    __slots__ = ("name", "event_scan_extra_tick", "event_scan_til", "scan", "event_scan_note_til_only")
    NAME_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_EXTRA_TICK_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_TIL_FIELD_NUMBER: _ClassVar[int]
    SCAN_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_NOTE_TIL_ONLY_FIELD_NUMBER: _ClassVar[int]
    name: str
    event_scan_extra_tick: int
    event_scan_til: _containers.RepeatedScalarFieldContainer[int]
    scan: bool
    event_scan_note_til_only: bool
    def __init__(self, name: _Optional[str] = ..., event_scan_extra_tick: _Optional[int] = ..., event_scan_til: _Optional[_Iterable[int]] = ..., scan: _Optional[bool] = ..., event_scan_note_til_only: _Optional[bool] = ...) -> None: ...

class BeginEditResponse(_message.Message):
    __slots__ = ("current_tick", "notes", "bpm_events", "beat_change_events", "timeline_speed_events", "note_speed_events", "event_scan_extra_tick", "event_scan_til", "scan", "event_scan_note_til_only")
    CURRENT_TICK_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    BPM_EVENTS_FIELD_NUMBER: _ClassVar[int]
    BEAT_CHANGE_EVENTS_FIELD_NUMBER: _ClassVar[int]
    TIMELINE_SPEED_EVENTS_FIELD_NUMBER: _ClassVar[int]
    NOTE_SPEED_EVENTS_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_EXTRA_TICK_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_TIL_FIELD_NUMBER: _ClassVar[int]
    SCAN_FIELD_NUMBER: _ClassVar[int]
    EVENT_SCAN_NOTE_TIL_ONLY_FIELD_NUMBER: _ClassVar[int]
    current_tick: int
    notes: _containers.RepeatedCompositeFieldContainer[Note]
    bpm_events: _containers.RepeatedCompositeFieldContainer[BpmEvent]
    beat_change_events: _containers.RepeatedCompositeFieldContainer[BeatChangeEvent]
    timeline_speed_events: _containers.RepeatedCompositeFieldContainer[TimelineSpeedEvent]
    note_speed_events: _containers.RepeatedCompositeFieldContainer[NoteSpeedEvent]
    event_scan_extra_tick: int
    event_scan_til: _containers.RepeatedScalarFieldContainer[int]
    scan: bool
    event_scan_note_til_only: bool
    def __init__(self, current_tick: _Optional[int] = ..., notes: _Optional[_Iterable[_Union[Note, _Mapping]]] = ..., bpm_events: _Optional[_Iterable[_Union[BpmEvent, _Mapping]]] = ..., beat_change_events: _Optional[_Iterable[_Union[BeatChangeEvent, _Mapping]]] = ..., timeline_speed_events: _Optional[_Iterable[_Union[TimelineSpeedEvent, _Mapping]]] = ..., note_speed_events: _Optional[_Iterable[_Union[NoteSpeedEvent, _Mapping]]] = ..., event_scan_extra_tick: _Optional[int] = ..., event_scan_til: _Optional[_Iterable[int]] = ..., scan: _Optional[bool] = ..., event_scan_note_til_only: _Optional[bool] = ...) -> None: ...

class TimelineSpeedKey(_message.Message):
    __slots__ = ("tick", "timeline_id")
    TICK_FIELD_NUMBER: _ClassVar[int]
    TIMELINE_ID_FIELD_NUMBER: _ClassVar[int]
    tick: int
    timeline_id: int
    def __init__(self, tick: _Optional[int] = ..., timeline_id: _Optional[int] = ...) -> None: ...

class ApplyEditRequest(_message.Message):
    __slots__ = ("name", "replace_all_notes", "notes_upsert", "note_ids_delete", "bpm_upsert", "beat_upsert", "til_upsert", "note_speed_upsert", "bpm_ticks_delete", "beat_bars_delete", "til_keys_delete", "note_speed_ticks_delete")
    NAME_FIELD_NUMBER: _ClassVar[int]
    REPLACE_ALL_NOTES_FIELD_NUMBER: _ClassVar[int]
    NOTES_UPSERT_FIELD_NUMBER: _ClassVar[int]
    NOTE_IDS_DELETE_FIELD_NUMBER: _ClassVar[int]
    BPM_UPSERT_FIELD_NUMBER: _ClassVar[int]
    BEAT_UPSERT_FIELD_NUMBER: _ClassVar[int]
    TIL_UPSERT_FIELD_NUMBER: _ClassVar[int]
    NOTE_SPEED_UPSERT_FIELD_NUMBER: _ClassVar[int]
    BPM_TICKS_DELETE_FIELD_NUMBER: _ClassVar[int]
    BEAT_BARS_DELETE_FIELD_NUMBER: _ClassVar[int]
    TIL_KEYS_DELETE_FIELD_NUMBER: _ClassVar[int]
    NOTE_SPEED_TICKS_DELETE_FIELD_NUMBER: _ClassVar[int]
    name: str
    replace_all_notes: bool
    notes_upsert: _containers.RepeatedCompositeFieldContainer[Note]
    note_ids_delete: _containers.RepeatedScalarFieldContainer[int]
    bpm_upsert: _containers.RepeatedCompositeFieldContainer[BpmEvent]
    beat_upsert: _containers.RepeatedCompositeFieldContainer[BeatChangeEvent]
    til_upsert: _containers.RepeatedCompositeFieldContainer[TimelineSpeedEvent]
    note_speed_upsert: _containers.RepeatedCompositeFieldContainer[NoteSpeedEvent]
    bpm_ticks_delete: _containers.RepeatedScalarFieldContainer[int]
    beat_bars_delete: _containers.RepeatedScalarFieldContainer[int]
    til_keys_delete: _containers.RepeatedCompositeFieldContainer[TimelineSpeedKey]
    note_speed_ticks_delete: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, name: _Optional[str] = ..., replace_all_notes: _Optional[bool] = ..., notes_upsert: _Optional[_Iterable[_Union[Note, _Mapping]]] = ..., note_ids_delete: _Optional[_Iterable[int]] = ..., bpm_upsert: _Optional[_Iterable[_Union[BpmEvent, _Mapping]]] = ..., beat_upsert: _Optional[_Iterable[_Union[BeatChangeEvent, _Mapping]]] = ..., til_upsert: _Optional[_Iterable[_Union[TimelineSpeedEvent, _Mapping]]] = ..., note_speed_upsert: _Optional[_Iterable[_Union[NoteSpeedEvent, _Mapping]]] = ..., bpm_ticks_delete: _Optional[_Iterable[int]] = ..., beat_bars_delete: _Optional[_Iterable[int]] = ..., til_keys_delete: _Optional[_Iterable[_Union[TimelineSpeedKey, _Mapping]]] = ..., note_speed_ticks_delete: _Optional[_Iterable[int]] = ...) -> None: ...

class ApplyEditResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UndoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UndoResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: _Optional[bool] = ...) -> None: ...

class RedoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RedoResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: _Optional[bool] = ...) -> None: ...

class CurrentTickRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CurrentTickResponse(_message.Message):
    __slots__ = ("current_tick",)
    CURRENT_TICK_FIELD_NUMBER: _ClassVar[int]
    current_tick: int
    def __init__(self, current_tick: _Optional[int] = ...) -> None: ...

class ErrorResponse(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: ErrorCode
    message: str
    def __init__(self, code: _Optional[_Union[ErrorCode, str]] = ..., message: _Optional[str] = ...) -> None: ...
