#include <windows.h>

#include "Plugin.h"
#include "meta.h"
#include <MargretePlugin.h>

#define DLLEXPORT extern "C" __declspec(dllexport)

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}

DLLEXPORT void WINAPI MargretePluginGetInfo(MP_PLUGININFO *info)
{
    if (!info)
    {
        return;
    }
    info->sdkVersion = MP_SDK_VERSION;
    if (info->nameBuffer)
    {
        wcsncpy_s(info->nameBuffer, static_cast<size_t>(info->nameBufferLength), W_TITLE, _TRUNCATE);
    }
    if (info->descBuffer)
    {
        wcsncpy_s(info->descBuffer, static_cast<size_t>(info->descBufferLength), W_DESC, _TRUNCATE);
    }
    if (info->developerBuffer)
    {
        wcsncpy_s(info->developerBuffer, static_cast<size_t>(info->developerBufferLength), W_DEVELOPER, _TRUNCATE);
    }
}

DLLEXPORT MpBoolean WINAPI MargretePluginCommandCreate(IMargretePluginCommand **ppobj)
{
    if (!ppobj)
    {
        return MP_FALSE;
    }
    auto *plugin = new Plugin();
    plugin->addRef();
    *ppobj = plugin;
    return MP_TRUE;
}
