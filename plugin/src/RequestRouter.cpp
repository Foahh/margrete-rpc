#include "RequestRouter.h"

#include <stdexcept>

#include "MargreteSession.h"

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
        if (request.has_get_current_tick_request())
        {
            MargreteSession session(*context_);
            response.mutable_get_current_tick_response()->set_tick(session.currentTick());
            return response;
        }
        if (request.has_append_transaction_request())
        {
            const std::uint32_t count = applier_.apply(*context_, request.append_transaction_request());
            response.mutable_append_transaction_response()->set_appended_items(count);
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
