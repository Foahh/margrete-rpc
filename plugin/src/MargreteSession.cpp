#include "MargreteSession.h"

#include <stdexcept>

MargreteSession::MargreteSession(IMargretePluginContext& context) : context_(context) {
    if (context_.getDocument(&document_) != MP_TRUE || !document_) {
        throw std::runtime_error("document is unavailable");
    }
    if (document_->getChart(&chart_) != MP_TRUE || !chart_) {
        throw std::runtime_error("chart is unavailable");
    }
    if (document_->getUndoBuffer(&undo_) != MP_TRUE || !undo_) {
        throw std::runtime_error("undo buffer is unavailable");
    }
}

MpInteger MargreteSession::currentTick() const {
    return context_.getCurrentTick();
}

IMargretePluginChart& MargreteSession::chart() const {
    return *chart_;
}

IMargretePluginUndoBuffer& MargreteSession::undo() const {
    return *undo_;
}

void MargreteSession::update() const {
    context_.update();
}
