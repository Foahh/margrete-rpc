#include <windows.h>

#include <MargretePlugin.h>
#include "Plugin.h"

#define DLLEXPORT extern "C" __declspec(dllexport)

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}

DLLEXPORT void WINAPI MargretePluginGetInfo(MP_PLUGININFO* info) {
    if (!info) {
        return;
    }
    info->sdkVersion = MP_SDK_VERSION;
    if (info->nameBuffer) {
        wcsncpy_s(info->nameBuffer, static_cast<size_t>(info->nameBufferLength), L"Margrete RPC", _TRUNCATE);
    }
    if (info->descBuffer) {
        wcsncpy_s(info->descBuffer, static_cast<size_t>(info->descBufferLength),
                  L"Local TCP/protobuf bridge for Python chart scripting", _TRUNCATE);
    }
    if (info->developerBuffer) {
        wcsncpy_s(info->developerBuffer, static_cast<size_t>(info->developerBufferLength), L"Foahh", _TRUNCATE);
    }
}

DLLEXPORT MpBoolean WINAPI MargretePluginCommandCreate(IMargretePluginCommand** ppobj) {
    if (!ppobj) {
        return MP_FALSE;
    }
    auto* plugin = new Plugin();
    plugin->addRef();
    *ppobj = plugin;
    return MP_TRUE;
}
