#include "Plugin.h"

#include <cwchar>

MpInteger Plugin::addRef() {
    return ++refCount_;
}

MpInteger Plugin::release() {
    const MpInteger value = --refCount_;
    if (value == 0) {
        delete this;
    }
    return value;
}

MpBoolean Plugin::queryInterface(const MpGuid& iid, void** ppobj) {
    if (!ppobj) {
        return MP_FALSE;
    }
    if (iid == IID_IMargretePluginBase || iid == IID_IMargretePluginCommand) {
        *ppobj = this;
        addRef();
        return MP_TRUE;
    }
    *ppobj = nullptr;
    return MP_FALSE;
}

MpBoolean Plugin::getCommandName(wchar_t* text, MpInteger textLength) const {
    if (!text || textLength <= 0) {
        return MP_FALSE;
    }
    wcsncpy_s(text, static_cast<size_t>(textLength), L"Margrete RPC", _TRUNCATE);
    return MP_TRUE;
}

MpBoolean Plugin::invoke(IMargretePluginContext*) {
    running_.store(!running_.load());
    return MP_TRUE;
}
