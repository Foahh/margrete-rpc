#pragma once

#include <MargretePlugin.h>

class MargreteSession
{
  public:
    explicit MargreteSession(IMargretePluginContext &context);

    MpInteger currentTick() const;
    IMargretePluginChart &chart() const;
    IMargretePluginUndoBuffer &undoBuffer() const;
    void update() const;

  private:
    IMargretePluginContext &context_;
    MargreteComPtr<IMargretePluginDocument> document_;
    MargreteComPtr<IMargretePluginChart> chart_;
    MargreteComPtr<IMargretePluginUndoBuffer> undoBuffer_;
};
