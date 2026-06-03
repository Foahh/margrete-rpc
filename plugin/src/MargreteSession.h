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
    IMargretePluginDocument *document_{nullptr};
    IMargretePluginChart *chart_{nullptr};
    IMargretePluginUndoBuffer *undoBuffer_{nullptr};
};
