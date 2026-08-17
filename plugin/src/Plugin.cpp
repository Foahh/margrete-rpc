#include "Plugin.h"

#include <cwchar>
#include <exception>
#include <filesystem>
#include <string>
#include <system_error>
#include <utility>

#if defined(_WIN32)
#include <windows.h>
#endif

#include "Config.h"
#include "Dialog.h"
#include "Utf8.h"
#include "meta.h"

namespace
{
bool PathExists(const std::filesystem::path &path)
{
    std::error_code ec;
    return !path.empty() && std::filesystem::exists(path, ec) && !ec;
}

std::filesystem::path DllDirectory()
{
#if defined(_WIN32)
    HMODULE self = nullptr;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(&DllDirectory), &self) == 0 ||
        !self)
    {
        return {};
    }
    std::wstring buf(MAX_PATH, L'\0');
    for (;;)
    {
        const DWORD n = GetModuleFileNameW(self, buf.data(), static_cast<DWORD>(buf.size()));
        if (n == 0)
        {
            return {};
        }
        if (n < buf.size())
        {
            buf.resize(n);
            return std::filesystem::path(buf).parent_path();
        }
        buf.assign(buf.size() * 2, L'\0');
    }
#else
    return {};
#endif
}

std::filesystem::path ResolveConfigPath()
{
    if (const auto envPath = EnvironmentPath("MARGRETE_RPC_CONFIG"); PathExists(envPath))
    {
        return envPath;
    }

    const std::filesystem::path dllDir = DllDirectory();
    if (!dllDir.empty())
    {
        const std::filesystem::path nearDll = dllDir / "margrete-rpc.ini";
        if (PathExists(nearDll))
        {
            return nearDll;
        }
    }

    if (PathExists("./plugins/margrete-rpc.ini"))
    {
        return "./plugins/margrete-rpc.ini";
    }

    return "margrete-rpc.ini";
}

ServerConfig LoadCurrentConfig()
{
    return LoadServerConfig(ResolveConfigPath());
}

std::string TryReloadConfig(ServerController &controller)
{
    try
    {
        controller.setConfig(LoadCurrentConfig());
        return {};
    }
    catch (const std::exception &ex)
    {
        return ex.what();
    }
}

void ShowServerDialog(IMargretePluginContext *ctx, ServerController &controller, std::string configError)
{
    ShowServerStatusDialog(ctx, controller, std::move(configError),
                           [&controller]() { return TryReloadConfig(controller); });
}
} // namespace

Plugin::Plugin()
{
    ServerConfig config;
    config.sourcePath = ResolveConfigPath();
    controller_ = std::make_unique<ServerController>(config);
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

    auto configError = TryReloadConfig(*controller_);
    if (!controller_->running() && configError.empty())
    {
        controller_->start(ctx);
    }
    ShowServerDialog(ctx, *controller_, configError);
    return MP_TRUE;
}
