#pragma once

#include <atomic>
#include <memory>

#include <MargretePlugin.h>

#include "ServerController.h"

class Plugin final : public IMargretePluginCommand {
public:
    Plugin();
    MpInteger addRef() override;
    MpInteger release() override;
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override;
    MpBoolean getCommandName(wchar_t* text, MpInteger textLength) const override;
    MpBoolean invoke(IMargretePluginContext* ctx) override;

private:
    ~Plugin();
    std::atomic<MpInteger> refCount_{0};
    std::unique_ptr<ServerController> controller_;
};
