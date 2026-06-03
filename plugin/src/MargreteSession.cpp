#include "MargreteSession.h"

#include <stdexcept>

MargreteSession::MargreteSession(IMargretePluginContext &context) : context_(context)
{
    IMargretePluginDocument *document = nullptr;
    if (context_.getDocument(&document) != MP_TRUE || !document)
    {
        throw std::runtime_error("document is unavailable");
    }
    document_.reset(document);

    IMargretePluginChart *chart = nullptr;
    if (document_->getChart(&chart) != MP_TRUE || !chart)
    {
        throw std::runtime_error("chart is unavailable");
    }
    chart_.reset(chart);

    IMargretePluginUndoBuffer *undoBuffer = nullptr;
    if (document_->getUndoBuffer(&undoBuffer) != MP_TRUE || !undoBuffer)
    {
        throw std::runtime_error("undoBuffer buffer is unavailable");
    }
    undoBuffer_.reset(undoBuffer);
}

MpInteger MargreteSession::currentTick() const
{
    return context_.getCurrentTick();
}

IMargretePluginChart &MargreteSession::chart() const
{
    return *chart_;
}

IMargretePluginUndoBuffer &MargreteSession::undoBuffer() const
{
    return *undoBuffer_;
}

void MargreteSession::update() const
{
    context_.update();
}
