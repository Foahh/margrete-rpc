#include "RequestRouter.h"

#include <stdexcept>
#include <string>
#include <utility>

#include "ChartMapper.h"
#include "MargreteSession.h"
#include "TransactionApplier.h"

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
            response.mutable_ping_response()->set_server_name("Margrete RPC");
            logInfo("request handled id=" + std::to_string(request.request_id()) + " kind=ping ok");
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
            auto *begin = response.mutable_begin_edit_response();
            begin->set_current_tick(session.currentTick());
            ChartMapper::SnapshotForEdit(session.chart(), config_.eventScanExtraTicks, config_.eventScanMaxTil, *begin);
            logInfo("begin_edit ok id=" + std::to_string(request.request_id()) + " current_tick=" +
                    std::to_string(begin->current_tick()) + " notes=" + std::to_string(begin->notes_size()) +
                    " bpm_events=" + std::to_string(begin->bpm_events_size()) +
                    " beat_change_events=" + std::to_string(begin->beat_change_events_size()) +
                    " timeline_speed_events=" + std::to_string(begin->timeline_speed_events_size()) +
                    " note_speed_events=" + std::to_string(begin->note_speed_events_size()) +
                    " scan_until_tick=" + std::to_string(begin->event_scan_until_tick()) +
                    " scan_max_til=" + std::to_string(begin->event_scan_max_til()));
            return response;
        }
        if (request.has_begin_append_request())
        {
            MargreteSession session(*context);
            response.mutable_begin_append_response()->set_current_tick(session.currentTick());
            logInfo("begin_append ok id=" + std::to_string(request.request_id()) +
                    " current_tick=" + std::to_string(response.begin_append_response().current_tick()));
            return response;
        }
        if (request.has_apply_edit_patch_request())
        {
            MargreteSession session(*context);
            const auto &req = request.apply_edit_patch_request();
            logInfo("apply_edit start id=" + std::to_string(request.request_id()) + " notes=" +
                    std::to_string(req.notes_size()) + " bpm_events=" + std::to_string(req.bpm_events_size()) +
                    " beat_change_events=" + std::to_string(req.beat_change_events_size()) +
                    " timeline_speed_events=" + std::to_string(req.timeline_speed_events_size()) +
                    " note_speed_events=" + std::to_string(req.note_speed_events_size()) +
                    " scan_until_tick=" + std::to_string(req.event_scan_until_tick()) +
                    " scan_max_til=" + std::to_string(req.event_scan_max_til()));
            TransactionApplier::ApplyEdit(session, request.apply_edit_patch_request());
            response.mutable_apply_edit_patch_response();
            logInfo("apply_edit ok id=" + std::to_string(request.request_id()));
            return response;
        }
        if (request.has_apply_append_patch_request())
        {
            MargreteSession session(*context);
            const auto &req = request.apply_append_patch_request();
            logInfo("apply_append start id=" + std::to_string(request.request_id()) + " notes=" +
                    std::to_string(req.notes_size()) + " bpm_events=" + std::to_string(req.bpm_events_size()) +
                    " beat_change_events=" + std::to_string(req.beat_change_events_size()) +
                    " timeline_speed_events=" + std::to_string(req.timeline_speed_events_size()) +
                    " note_speed_events=" + std::to_string(req.note_speed_events_size()));
            TransactionApplier::ApplyAppend(session, request.apply_append_patch_request());
            response.mutable_apply_append_patch_response();
            logInfo("apply_append ok id=" + std::to_string(request.request_id()));
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
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, ex.what());
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
    if (request.has_begin_edit_request())
        return "begin_edit";
    if (request.has_begin_append_request())
        return "begin_append";
    if (request.has_apply_edit_patch_request())
        return "apply_edit";
    if (request.has_apply_append_patch_request())
        return "apply_append";
    if (request.has_error_response())
        return "error_response";
    return "unknown";
}
