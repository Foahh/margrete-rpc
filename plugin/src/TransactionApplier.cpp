#include "TransactionApplier.h"

#include <stdexcept>

#include "MargreteSession.h"

std::uint32_t TransactionApplier::apply(IMargretePluginContext& context,
                                        const margrete::rpc::v1::AppendTransactionRequest& request) {
    std::scoped_lock lock(mutex_);
    if (request.items().empty()) {
        throw std::runtime_error("transaction is empty");
    }

    MargreteSession session(context);
    bool recording = false;
    try {
        if (session.undo().beginRecording() != MP_TRUE) {
            throw std::runtime_error("failed to begin undo recording");
        }
        recording = true;
        for (const auto& item : request.items()) {
            mapper_.appendItem(session.chart(), item);
        }
        if (session.undo().commitRecording() != MP_TRUE) {
            throw std::runtime_error("failed to commit undo recording");
        }
        recording = false;
        session.update();
        return static_cast<std::uint32_t>(request.items().size());
    } catch (...) {
        if (recording) {
            session.undo().discardRecording();
            session.update();
        }
        throw;
    }
}
