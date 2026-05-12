#pragma once

#include <cstdint>
#include <mutex>

#include <MargretePlugin.h>

#include "ChartMapper.h"
#include "margrete/rpc/v1/messages.pb.h"

class TransactionApplier {
public:
    std::uint32_t apply(IMargretePluginContext& context, const margrete::rpc::v1::AppendTransactionRequest& request);

private:
    std::mutex mutex_;
    ChartMapper mapper_;
};
