#include "Plugin.h"

#include <cwchar>

#include "Config.h"
#include "meta.h"

Plugin::Plugin() : controller_(std::make_unique<ServerController>(LoadServerConfig("margrete-rpc.ini")))
{
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
