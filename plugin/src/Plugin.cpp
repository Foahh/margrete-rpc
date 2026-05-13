#include "Plugin.h"

#include <cwchar>
#include <filesystem>
#include <string>

#if defined(_WIN32)
#include <windows.h>
#endif

#include "Config.h"
#include "meta.h"

namespace
{
std::filesystem::path DllDirectory()
{
#if defined(_WIN32)
    wchar_t buf[MAX_PATH]{};
    HMODULE self = nullptr;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(&DllDirectory), &self) == 0 ||
        !self)
    {
        return {};
    }
    const DWORD n = GetModuleFileNameW(self, buf, static_cast<DWORD>(std::size(buf)));
    if (n == 0 || n >= std::size(buf))
    {
        return {};
    }
    return std::filesystem::path(buf).parent_path();
#else
    return {};
#endif
}

std::filesystem::path ResolveConfigPath()
{
    if (const char *env = std::getenv("MARGRETE_RPC_CONFIG"); env && *env)
    {
        std::filesystem::path p(env);
        if (std::filesystem::exists(p))
        {
            return p;
        }
    }

    const std::filesystem::path dllDir = DllDirectory();
    if (!dllDir.empty())
    {
        const std::filesystem::path nearDll = dllDir / "margrete-rpc.ini";
        if (std::filesystem::exists(nearDll))
        {
            return nearDll;
        }
    }

    if (std::filesystem::exists("./plugins/margrete-rpc.ini"))
    {
        return "./plugins/margrete-rpc.ini";
    }

    return "margrete-rpc.ini";
}
} // namespace

Plugin::Plugin()
{
    const std::filesystem::path configPath = ResolveConfigPath();
    controller_ = std::make_unique<ServerController>(LoadServerConfig(configPath));
}

Plugin::~Plugin()
{
    if (controller_)
    {
        controller_->stop();
    }
}

MpInteger Plugin::addRef()
{
    return ++refCount_;
}

MpInteger Plugin::release()
{
    const MpInteger value = --refCount_;
    if (value == 0)
    {
        delete this;
    }
    return value;
}

MpBoolean Plugin::queryInterface(const MpGuid &iid, void **ppobj)
{
    if (!ppobj)
    {
        return MP_FALSE;
    }
    if (iid == IID_IMargretePluginBase || iid == IID_IMargretePluginCommand)
    {
        *ppobj = this;
        addRef();
        return MP_TRUE;
    }
    *ppobj = nullptr;
    return MP_FALSE;
}

MpBoolean Plugin::getCommandName(wchar_t *text, MpInteger textLength) const
{
    if (!text || textLength <= 0)
    {
        return MP_FALSE;
    }
    wcsncpy_s(text, static_cast<size_t>(textLength), W_TITLE, _TRUNCATE);
    return MP_TRUE;
}

MpBoolean Plugin::invoke(IMargretePluginContext *ctx)
{
    if (!ctx || !controller_)
    {
        return MP_FALSE;
    }
    controller_->toggle(ctx);
    return MP_TRUE;
}
