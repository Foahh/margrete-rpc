#include "RequestRouter.h"

#include <stdexcept>

#include "ChartMapper.h"
#include "MargreteSession.h"
#include "TransactionApplier.h"

RequestRouter::RequestRouter(IMargretePluginContext *context) : context_(context)
{
}

void RequestRouter::setContext(IMargretePluginContext *context)
{
    context_ = context;
}

margrete::rpc::v1::Envelope RequestRouter::route(const margrete::rpc::v1::Envelope &request)
{
    margrete::rpc::v1::Envelope response;
    response.set_request_id(request.request_id());

    try
    {
        if (request.has_ping_request())
        {
            response.mutable_ping_response()->set_server_name("Margrete RPC");
            return response;
        }
        if (!context_)
        {
            return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_UNAVAILABLE,
                         "Margrete context is unavailable");
        }
        if (request.has_begin_edit_request())
        {
            MargreteSession session(*context_);
            auto *begin = response.mutable_begin_edit_response();
            begin->set_current_tick(session.currentTick());
            for (const auto &note : ChartMapper::SnapshotNotes(session.chart()))
            {
                *begin->add_notes() = note;
            }
            return response;
        }
        if (request.has_begin_append_request())
        {
            MargreteSession session(*context_);
            response.mutable_begin_append_response()->set_current_tick(session.currentTick());
            return response;
        }
        if (request.has_apply_edit_patch_request())
        {
            MargreteSession session(*context_);
            TransactionApplier::ApplyEdit(session, request.apply_edit_patch_request());
            response.mutable_apply_edit_patch_response();
            return response;
        }
        if (request.has_apply_append_patch_request())
        {
            MargreteSession session(*context_);
            TransactionApplier::ApplyAppend(session, request.apply_append_patch_request());
            response.mutable_apply_append_patch_response();
            return response;
        }
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, "unsupported request");
    }
    catch (const std::invalid_argument &ex)
    {
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, ex.what());
    }
    catch (const std::runtime_error &ex)
    {
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT, ex.what());
    }
    catch (...)
    {
        return error(request.request_id(), margrete::rpc::v1::ERROR_CODE_INTERNAL, "unexpected plugin error");
    }
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
