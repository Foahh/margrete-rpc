#pragma once

#include <atomic>
#include <MargretePlugin.h>

class Plugin final : public IMargretePluginCommand {
public:
    MpInteger addRef() override;
    MpInteger release() override;
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override;
    MpBoolean getCommandName(wchar_t* text, MpInteger textLength) const override;
    MpBoolean invoke(IMargretePluginContext* ctx) override;

private:
    ~Plugin() = default;
    std::atomic<MpInteger> refCount_{0};
    std::atomic_bool running_{false};
};
