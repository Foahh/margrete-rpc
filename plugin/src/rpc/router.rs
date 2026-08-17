use crate::abi::{ComPtr, Context, MP_TRUE, Unknown};
use crate::chart::deduper::deduplicate;
use crate::chart::mapper::snapshot_for_edit;
use crate::chart::session::MargreteSession;
use crate::chart::transaction::apply_edit;
use crate::meta;
use crate::rpc::proto::{Envelope, ErrorCode, ErrorResponse, StatusResponse, envelope};
use crate::server::config::ServerConfig;
use std::sync::Mutex;

const DEFAULT_EVENT_SCAN_LOOKAHEAD_TICKS: i32 = 19200;

#[derive(Clone, Default)]
pub struct RouterStatusSnapshot {
    pub uptime: u64,
    pub pid: u32,
    pub log_path: String,
    pub config_path: String,
}

pub struct RequestRouter {
    inner: Mutex<RouterInner>,
}

struct RouterInner {
    context: *mut Context,
    config: ServerConfig,
    instance_id: String,
    status_snapshot: Option<Box<dyn Fn() -> RouterStatusSnapshot + Send + Sync>>,
}

unsafe impl Send for RouterInner {}
unsafe impl Sync for RouterInner {}

impl RequestRouter {
    pub fn new(context: *mut Context) -> Self {
        Self::with_config(context, ServerConfig::default())
    }

    pub fn with_config(context: *mut Context, config: ServerConfig) -> Self {
        let router = Self {
            inner: Mutex::new(RouterInner {
                context: std::ptr::null_mut(),
                config,
                instance_id: String::new(),
                status_snapshot: None,
            }),
        };
        router.set_context(context);
        router
    }

    pub fn set_context(&self, context: *mut Context) {
        let mut inner = self.inner.lock().expect("router");
        if !context.is_null() {
            unsafe {
                let _ = Context::add_ref(context);
            }
        }
        if !inner.context.is_null() {
            unsafe {
                let _ = Context::release(inner.context);
            }
        }
        inner.context = context;
    }

    pub fn set_config(&self, config: ServerConfig) {
        self.inner.lock().expect("router").config = config;
    }

    pub fn set_instance_id(&self, instance_id: impl Into<String>) {
        self.inner.lock().expect("router").instance_id = instance_id.into();
    }

    pub fn set_status_snapshot_provider<F>(&self, provider: F)
    where
        F: Fn() -> RouterStatusSnapshot + Send + Sync + 'static,
    {
        self.inner.lock().expect("router").status_snapshot = Some(Box::new(provider));
    }

    pub fn route(&self, request: &Envelope) -> Envelope {
        match self.route_inner(request) {
            Ok(response) => response,
            Err(err) => {
                let code = err.code();
                log::error!(
                    "request exception id={} kind={} msg=\"{}\"",
                    request.request_id,
                    request_kind(request),
                    err
                );
                error_envelope(request.request_id, code, err.to_string())
            }
        }
    }

    fn route_inner(&self, request: &Envelope) -> crate::error::Result<Envelope> {
        log::info!(
            "request received id={} kind={}",
            request.request_id,
            request_kind(request)
        );
        match &request.body {
            Some(envelope::Body::PingRequest(_)) => {
                return Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::PingResponse(Default::default())),
                });
            }
            Some(envelope::Body::StatusRequest(_)) => {
                let (instance_id, snapshot) = {
                    let inner = self.inner.lock().expect("router");
                    let snapshot = inner
                        .status_snapshot
                        .as_ref()
                        .map(|p| p())
                        .unwrap_or_default();
                    (inner.instance_id.clone(), snapshot)
                };
                let status = StatusResponse {
                    server_version: meta::PRODUCT_VERSION.into(),
                    server_build_time: meta::BUILD_TIME.into(),
                    instance_id,
                    api_version: meta::RPC_API_VERSION,
                    uptime: snapshot.uptime,
                    pid: snapshot.pid,
                    log_path: snapshot.log_path,
                    config_path: snapshot.config_path,
                };
                log::info!("request handled id={} kind=status ok", request.request_id);
                return Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::StatusResponse(status)),
                });
            }
            _ => {}
        }

        let Some(context) = self.retain_context() else {
            log::error!(
                "request failed id={} kind={} code=UNAVAILABLE msg=\"Margrete context is unavailable\"",
                request.request_id,
                request_kind(request)
            );
            return Ok(error_envelope(
                request.request_id,
                ErrorCode::Unavailable,
                "Margrete context is unavailable",
            ));
        };

        match &request.body {
            Some(envelope::Body::BeginEditRequest(req)) => {
                let session = MargreteSession::new(context.as_ptr())?;
                let mut begin = crate::rpc::proto::BeginEditResponse {
                    current_tick: session.current_tick(),
                    snapshot: req.snapshot,
                    ..Default::default()
                };
                let mut scan_lookahead = req.event_scan_lookahead_ticks;
                if scan_lookahead <= 0 {
                    scan_lookahead = DEFAULT_EVENT_SCAN_LOOKAHEAD_TICKS;
                }
                let (scan_til_ids, note_til_only) = match &req.event_scan_til_ids {
                    Some(til_ids) if !til_ids.ids.is_empty() => (til_ids.ids.clone(), false),
                    Some(_) => (default_event_scan_til_ids(), false),
                    None => (default_event_scan_til_ids(), true),
                };
                if req.snapshot {
                    snapshot_for_edit(
                        session.chart(),
                        scan_lookahead,
                        &scan_til_ids,
                        note_til_only,
                        &mut begin,
                    )?;
                } else {
                    begin.event_scan_lookahead_ticks = scan_lookahead;
                    begin.event_scan_til_ids = scan_til_ids;
                }
                log::info!(
                    "begin_edit ok id={} current_tick={} notes={} bpm_events={} beat_change_events={} timeline_speed_events={} note_speed_events={} event_scan_lookahead_ticks={} event_scan_til_ids_count={} snapshot={} note_til_only={}",
                    request.request_id,
                    begin.current_tick,
                    begin.notes.len(),
                    begin.bpm_events.len(),
                    begin.beat_change_events.len(),
                    begin.timeline_speed_events.len(),
                    begin.note_speed_events.len(),
                    begin.event_scan_lookahead_ticks,
                    begin.event_scan_til_ids.len(),
                    u8::from(begin.snapshot),
                    u8::from(note_til_only)
                );
                Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::BeginEditResponse(begin)),
                })
            }
            Some(envelope::Body::ApplyEditRequest(req)) => {
                let session = MargreteSession::new(context.as_ptr())?;
                apply_edit(&session, req)?;
                log::info!("apply_edit ok id={}", request.request_id);
                Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::ApplyEditResponse(Default::default())),
                })
            }
            Some(envelope::Body::UndoRequest(_)) => {
                let session = MargreteSession::new(context.as_ptr())?;
                let success =
                    session.undo_buffer().can_undo() && session.undo_buffer().undo() == MP_TRUE;
                if success {
                    let _ = deduplicate(session.chart());
                    session.update();
                }
                log::info!(
                    "undo ok id={} success={}",
                    request.request_id,
                    u8::from(success)
                );
                Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::UndoResponse(
                        crate::rpc::proto::UndoResponse { success },
                    )),
                })
            }
            Some(envelope::Body::RedoRequest(_)) => {
                let session = MargreteSession::new(context.as_ptr())?;
                let success =
                    session.undo_buffer().can_redo() && session.undo_buffer().redo() == MP_TRUE;
                if success {
                    let _ = deduplicate(session.chart());
                    session.update();
                }
                log::info!(
                    "redo ok id={} success={}",
                    request.request_id,
                    u8::from(success)
                );
                Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::RedoResponse(
                        crate::rpc::proto::RedoResponse { success },
                    )),
                })
            }
            Some(envelope::Body::CurrentTickRequest(_)) => {
                let tick = context.context().current_tick();
                log::info!(
                    "current_tick ok id={} current_tick={tick}",
                    request.request_id
                );
                Ok(Envelope {
                    request_id: request.request_id,
                    body: Some(envelope::Body::CurrentTickResponse(
                        crate::rpc::proto::CurrentTickResponse { current_tick: tick },
                    )),
                })
            }
            _ => {
                log::error!(
                    "request failed id={} kind={} code=INVALID_ARGUMENT msg=\"unsupported request\"",
                    request.request_id,
                    request_kind(request)
                );
                Ok(error_envelope(
                    request.request_id,
                    ErrorCode::InvalidArgument,
                    "unsupported request",
                ))
            }
        }
    }

    fn retain_context(&self) -> Option<ComPtr<Context>> {
        let inner = self.inner.lock().expect("router");
        if inner.context.is_null() {
            None
        } else {
            Some(unsafe { ComPtr::retain(inner.context) })
        }
    }
}

impl Drop for RequestRouter {
    fn drop(&mut self) {
        self.set_context(std::ptr::null_mut());
    }
}

fn default_event_scan_til_ids() -> Vec<i32> {
    (0..=15).collect()
}

fn error_envelope(request_id: u64, code: ErrorCode, message: impl Into<String>) -> Envelope {
    Envelope {
        request_id,
        body: Some(envelope::Body::ErrorResponse(ErrorResponse {
            code: code as i32,
            message: message.into(),
        })),
    }
}

fn request_kind(request: &Envelope) -> &'static str {
    match &request.body {
        Some(envelope::Body::PingRequest(_)) => "ping",
        Some(envelope::Body::StatusRequest(_)) => "status",
        Some(envelope::Body::BeginEditRequest(_)) => "begin_edit",
        Some(envelope::Body::ApplyEditRequest(_)) => "apply_edit",
        Some(envelope::Body::UndoRequest(_)) => "undo",
        Some(envelope::Body::RedoRequest(_)) => "redo",
        Some(envelope::Body::CurrentTickRequest(_)) => "current_tick",
        Some(envelope::Body::ErrorResponse(_)) => "error_response",
        _ => "unknown",
    }
}
