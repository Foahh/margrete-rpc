#include "RequestRouter.h"

#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "ChartMapper.h"
#include "MargreteSession.h"
#include "RootNoteDeduper.h"
#include "TransactionApplier.h"
#include "meta.h"

namespace
{
constexpr MpInteger kDefaultEventScanLookaheadTicks = 19200;

std::vector<std::int32_t> DefaultEventScanTilIds()
{
    std::vector<std::int32_t> tils;
    tils.reserve(16);
    for (std::int32_t til = 0; til <= 15; ++til)
    {
        tils.push_back(til);
    }
    return tils;
}
} // namespace

RequestRouter::RequestRouter(IMargretePluginContext *context) : RequestRouter(context, ServerConfig{})
{
}

RequestRouter::RequestRouter(IMargretePluginContext *context, ServerConfig config) : config_(std::move(config))
{
    setContext(context);
}

RequestRouter::~RequestRouter()
{
    setContext(nullptr);
}

void RequestRouter::setContext(IMargretePluginContext *context)
{
    std::scoped_lock lock(contextMutex_);
    if (context)
    {
        context->addRef();
    }
    if (context_)
    {
        context_->release();
    }
    context_ = context;
}

void RequestRouter::setConfig(ServerConfig config)
{
    std::scoped_lock lock(contextMutex_);
    config_ = std::move(config);
}

void RequestRouter::setInstanceId(std::string instanceId)
{
    std::scoped_lock lock(contextMutex_);
    instanceId_ = std::move(instanceId);
}

void RequestRouter::setStatusSnapshotProvider(StatusSnapshotProvider provider)
{
    std::scoped_lock lock(contextMutex_);
    statusSnapshotProvider_ = std::move(provider);
}

void RequestRouter::setLogger(Logger *logger)
{
    std::scoped_lock lock(contextMutex_);
    logger_ = logger;
}

margrete::rpc::v1::Envelope RequestRouter::route(const margrete::rpc::v1::Envelope &request)
{
    margrete::rpc::v1::Envelope response;
    response.set_request_id(request.request_id());

    try
    {
        logInfo("request received id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request));
        if (request.has_ping_request())
        {
            response.mutable_ping_response();
            return response;
        }
        if (request.has_status_request())
        {
            auto *status = response.mutable_status_response();
            status->set_server_name("Margrete RPC");
            status->set_server_version(PRODUCT_VERSION);
            status->set_server_build_time(BUILD_TIME);
            status->set_instance_id(instanceId_);

            RouterStatusSnapshot snapshot;
            {
                std::scoped_lock lock(contextMutex_);
                if (statusSnapshotProvider_)
                {
                    snapshot = statusSnapshotProvider_();
                }
            }
            status->set_uptime(snapshot.uptime);
            status->set_pid(snapshot.pid);
            status->set_log_path(snapshot.logPath);
            status->set_config_path(snapshot.configPath);
            logInfo("request handled id=" + std::to_string(request.request_id()) + " kind=status ok");
            return response;
        }

        auto context = retainContext();
        if (!context)
        {
            auto resp = error(request.request_id(), margrete::rpc::v1::ERROR_CODE_UNAVAILABLE,
                              "Margrete context is unavailable");
            logError("request failed id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request) +
                     " code=UNAVAILABLE msg=\"Margrete context is unavailable\"");
            return resp;
        }
        if (request.has_begin_edit_request())
        {
            MargreteSession session(*context);
            const auto &req = request.begin_edit_request();
            auto *begin = response.mutable_begin_edit_response();
            begin->set_current_tick(session.currentTick());

            MpInteger scanLookaheadTicks = req.event_scan_lookahead_ticks();
            if (scanLookaheadTicks <= 0)
            {
                scanLookaheadTicks = kDefaultEventScanLookaheadTicks;
            }

            std::vector<std::int32_t> scanTilIds;
            bool noteTilOnly = false;
            if (req.has_event_scan_til_ids())
            {
                const auto &tilIds = req.event_scan_til_ids();
                if (tilIds.ids_size() > 0)
                {
                    scanTilIds.reserve(static_cast<std::size_t>(tilIds.ids_size()));
                    for (const auto til : tilIds.ids())
                    {
                        scanTilIds.push_back(til);
                    }
                }
                else
                {
                    scanTilIds = DefaultEventScanTilIds();
                }
            }
            else
            {
                scanTilIds = DefaultEventScanTilIds();
                noteTilOnly = true;
            }

            const bool snapshot = req.snapshot();
            begin->set_snapshot(snapshot);
            if (snapshot)
            {
                ChartMapper::SnapshotForEdit(session.chart(), scanLookaheadTicks, scanTilIds, noteTilOnly, *begin);
            }
            else
            {
                begin->set_event_scan_lookahead_ticks(scanLookaheadTicks);
                begin->mutable_event_scan_til_ids()->Assign(scanTilIds.begin(), scanTilIds.end());
            }
            logInfo("begin_edit ok id=" + std::to_string(request.request_id()) + " current_tick=" +
                    std::to_string(begin->current_tick()) + " notes=" + std::to_string(begin->notes_size()) +
                    " bpm_events=" + std::to_string(begin->bpm_events_size()) +
                    " beat_change_events=" + std::to_string(begin->beat_change_events_size()) +
                    " timeline_speed_events=" + std::to_string(begin->timeline_speed_events_size()) +
                    " note_speed_events=" + std::to_string(begin->note_speed_events_size()) +
                    " event_scan_lookahead_ticks=" +
                    std::to_string(begin->event_scan_lookahead_ticks()) + " event_scan_til_ids_count=" +
                    std::to_string(begin->event_scan_til_ids_size()) + " snapshot=" +
                    std::to_string(begin->snapshot()) +
                    " note_til_only=" + std::to_string(noteTilOnly));
            return response;
        }
        if (request.has_apply_edit_request())
        {
            MargreteSession session(*context);
            const auto &req = request.apply_edit_request();
            logInfo("apply_edit start id=" + std::to_string(request.request_id()) +
                    " replace_all_notes=" + std::to_string(req.replace_all_notes()) +
                    " notes_upsert=" + std::to_string(req.notes_upsert_size()) +
                    " note_ids_delete=" + std::to_string(req.note_ids_delete_size()) + " bpm_upsert=" +
                    std::to_string(req.bpm_upsert_size()) + " beat_upsert=" + std::to_string(req.beat_upsert_size()) +
                    " til_upsert=" + std::to_string(req.til_upsert_size()) +
                    " note_speed_upsert=" + std::to_string(req.note_speed_upsert_size()) +
                    " bpm_ticks_delete=" + std::to_string(req.bpm_ticks_delete_size()) +
                    " beat_bars_delete=" + std::to_string(req.beat_bars_delete_size()) +
                    " til_keys_delete=" + std::to_string(req.til_keys_delete_size()) +
                    " note_speed_ticks_delete=" + std::to_string(req.note_speed_ticks_delete_size()));
            TransactionApplier::ApplyEdit(session, req);
            response.mutable_apply_edit_response();
            logInfo("apply_edit ok id=" + std::to_string(request.request_id()));
            return response;
        }
        if (request.has_undo_request())
        {
            MargreteSession session(*context);
            const bool success = session.undoBuffer().canUndo() == MP_TRUE && session.undoBuffer().undo() == MP_TRUE;
            if (success)
            {
                RootNoteDeduper::Deduplicate(session.chart());
                session.update();
            }
            response.mutable_undo_response()->set_success(success);
            logInfo("undo ok id=" + std::to_string(request.request_id()) + " success=" + std::to_string(success));
            return response;
        }
        if (request.has_redo_request())
        {
            MargreteSession session(*context);
            const bool success = session.undoBuffer().canRedo() == MP_TRUE && session.undoBuffer().redo() == MP_TRUE;
            if (success)
            {
                RootNoteDeduper::Deduplicate(session.chart());
                session.update();
            }
            response.mutable_redo_response()->set_success(success);
            logInfo("redo ok id=" + std::to_string(request.request_id()) + " success=" + std::to_string(success));
            return response;
        }
        if (request.has_current_tick_request())
        {
            response.mutable_current_tick_response()->set_current_tick(context->getCurrentTick());
            logInfo("current_tick ok id=" + std::to_string(request.request_id()) +
                    " current_tick=" + std::to_string(response.current_tick_response().current_tick()));
            return response;
        }
        auto resp = error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, "unsupported request");
        logError("request failed id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request) +
                 " code=INVALID_ARGUMENT msg=\"unsupported request\"");
        return resp;
    }
    catch (const std::invalid_argument &ex)
    {
        logError("request exception id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request) +
                 " type=invalid_argument msg=\"" + std::string(ex.what()) + "\"");
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, ex.what());
    }
    catch (const std::runtime_error &ex)
    {
        logError("request exception id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request) +
                 " type=runtime_error msg=\"" + std::string(ex.what()) + "\"");
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INTERNAL, ex.what());
    }
    catch (...)
    {
        logError("request exception id=" + std::to_string(request.request_id()) + " kind=" + requestKind(request) +
                 " type=unknown");
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INTERNAL, "unexpected plugin error");
    }
}

MargreteComPtr<IMargretePluginContext> RequestRouter::retainContext() const
{
    std::scoped_lock lock(contextMutex_);
    if (!context_)
    {
        return {};
    }
    context_->addRef();
    return MargreteComPtr<IMargretePluginContext>(context_);
}

margrete::rpc::v1::Envelope RequestRouter::error(std::uint64_t requestId, margrete::rpc::v1::ErrorCode code,
                                                 const std::string &message) const
{
    margrete::rpc::v1::Envelope response;
    response.set_request_id(requestId);
    auto *err = response.mutable_error_response();
    err->set_code(code);
    err->set_message(message);
    return response;
}

void RequestRouter::logInfo(const std::string &message) const
{
    std::scoped_lock lock(contextMutex_);
    if (logger_)
    {
        logger_->info(message);
    }
}

void RequestRouter::logError(const std::string &message) const
{
    std::scoped_lock lock(contextMutex_);
    if (logger_)
    {
        logger_->error(message);
    }
}

const char *RequestRouter::requestKind(const margrete::rpc::v1::Envelope &request) noexcept
{
    if (request.has_ping_request())
        return "ping";
    if (request.has_status_request())
        return "status";
    if (request.has_begin_edit_request())
        return "begin_edit";
    if (request.has_apply_edit_request())
        return "apply_edit";
    if (request.has_undo_request())
        return "undo";
    if (request.has_redo_request())
        return "redo";
    if (request.has_current_tick_request())
        return "current_tick";
    if (request.has_error_response())
        return "error_response";
    return "unknown";
}
