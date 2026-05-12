#pragma once

#include <MargretePlugin.h>

#include "margrete/rpc/v1/messages.pb.h"

class ChartMapper {
public:
    void appendItem(IMargretePluginChart& chart, const margrete::rpc::v1::AppendItem& item) const;

private:
    void appendTap(IMargretePluginChart& chart, const margrete::rpc::v1::Tap& tap) const;
};
