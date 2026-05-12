#pragma once

#include <vector>

#include <MargretePlugin.h>

class FakeBase {
public:
    MpInteger addRef() { return ++refCount; }
    MpInteger release() { return --refCount; }
    MpBoolean queryInterface(const MpGuid&, void**) { return MP_FALSE; }

private:
    MpInteger refCount{1};
};

class FakeNote final : public IMargretePluginNote, public FakeBase {
public:
    MpInteger addRef() override { return FakeBase::addRef(); }
    MpInteger release() override { return FakeBase::release(); }
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override { return FakeBase::queryInterface(iid, ppobj); }
    MpInteger getId() const override { return id; }
    void getInfo(MP_NOTEINFO* noteInfo) const override { *noteInfo = info; }
    void setInfo(const MP_NOTEINFO* noteInfo) override { info = *noteInfo; }
    MpInteger getChildrenCount() const override { return static_cast<MpInteger>(children.size()); }
    MpBoolean getChild(MpInteger index, IMargretePluginNote** ppobj) const override {
        if (index < 0 || index >= static_cast<MpInteger>(children.size())) {
            return MP_FALSE;
        }
        *ppobj = children[static_cast<std::size_t>(index)];
        return MP_TRUE;
    }
    MpBoolean getParent(IMargretePluginNote**) const override { return MP_FALSE; }
    MpBoolean appendChild(IMargretePluginNote* note) override {
        children.push_back(note);
        return MP_TRUE;
    }
    MpBoolean deleteChild(IMargretePluginNote*) override { return MP_TRUE; }
    MpBoolean clone(IMargretePluginNote**) const override { return MP_FALSE; }
    void replaceWith(const IMargretePluginNote*, MpBoolean) override {}
    void copyInfoTo(IMargretePluginNote*) const override {}
    MpBoolean getBaseNote(IMargretePluginNote**) const override { return MP_FALSE; }
    void offsetChild(MpInteger) override {}
    void flipH(MpBoolean) override {}

    int id{1};
    MP_NOTEINFO info{};
    std::vector<IMargretePluginNote*> children;
};

class FakeChart final : public IMargretePluginChart, public FakeBase {
public:
    MpInteger addRef() override { return FakeBase::addRef(); }
    MpInteger release() override { return FakeBase::release(); }
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override { return FakeBase::queryInterface(iid, ppobj); }
    MpBoolean createNote(IMargretePluginNote** ppobj) const override {
        createdNotes.push_back(new FakeNote());
        *ppobj = createdNotes.back();
        return MP_TRUE;
    }
    MpInteger getNotesCount() const override { return 0; }
    MpBoolean getNote(MpInteger, IMargretePluginNote**) override { return MP_FALSE; }
    MpBoolean appendNote(IMargretePluginNote*) override {
        ++appendedNotes;
        return MP_TRUE;
    }
    MpBoolean deleteNote(IMargretePluginNote*) override { return MP_TRUE; }
    void offsetNotes(MpInteger) override {}
    MpBoolean createEvent(const MpGuid&, void**) const override { return MP_FALSE; }
    MpBoolean appendEvent(IMargretePluginEvent*) override {
        ++appendedEvents;
        return MP_TRUE;
    }
    MpBoolean deleteEvent(IMargretePluginEvent*) override { return MP_TRUE; }
    MpBoolean findEventTimelineSpeed(MpInteger, MpInteger, void**) override { return MP_FALSE; }
    MpBoolean findEventNoteSpeedModifier(MpInteger, void**) override { return MP_FALSE; }
    MpBoolean findEventBpm(MpInteger, void**) override { return MP_FALSE; }
    MpBoolean findEventBeatChange(MpInteger, void**) override { return MP_FALSE; }

    mutable std::vector<FakeNote*> createdNotes;
    int appendedNotes{0};
    int appendedEvents{0};
};

class FakeUndo final : public IMargretePluginUndoBuffer, public FakeBase {
public:
    MpInteger addRef() override { return FakeBase::addRef(); }
    MpInteger release() override { return FakeBase::release(); }
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override { return FakeBase::queryInterface(iid, ppobj); }
    MpBoolean beginRecording() override {
        ++beginCount;
        return MP_TRUE;
    }
    MpBoolean commitRecording() override {
        ++commitCount;
        return MP_TRUE;
    }
    MpBoolean discardRecording() override {
        ++discardCount;
        return MP_TRUE;
    }
    MpBoolean undo() override { return MP_TRUE; }
    MpBoolean redo() override { return MP_TRUE; }
    MpBoolean canUndo() const override { return MP_TRUE; }
    MpBoolean canRedo() const override { return MP_FALSE; }
    MpBoolean isRecording() const override { return beginCount > commitCount + discardCount; }

    int beginCount{0};
    int commitCount{0};
    int discardCount{0};
};

class FakeDocument final : public IMargretePluginDocument, public FakeBase {
public:
    explicit FakeDocument(FakeChart& chartIn, FakeUndo& undoIn) : chart(chartIn), undo(undoIn) {}
    MpInteger addRef() override { return FakeBase::addRef(); }
    MpInteger release() override { return FakeBase::release(); }
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override { return FakeBase::queryInterface(iid, ppobj); }
    MpBoolean getChart(IMargretePluginChart** ppobj) override {
        *ppobj = &chart;
        return MP_TRUE;
    }
    MpBoolean getUndoBuffer(IMargretePluginUndoBuffer** ppobj) override {
        *ppobj = &undo;
        return MP_TRUE;
    }

    FakeChart& chart;
    FakeUndo& undo;
};

class FakeContext final : public IMargretePluginContext, public FakeBase {
public:
    FakeContext() : document(chart, undo) {}
    MpInteger addRef() override { return FakeBase::addRef(); }
    MpInteger release() override { return FakeBase::release(); }
    MpBoolean queryInterface(const MpGuid& iid, void** ppobj) override { return FakeBase::queryInterface(iid, ppobj); }
    MpBoolean getDocument(IMargretePluginDocument** ppobj) override {
        *ppobj = &document;
        return MP_TRUE;
    }
    void* getMainWindowHandle() override { return nullptr; }
    MpInteger getCurrentTick() const override { return currentTick; }
    void update() const override { updated = true; }

    FakeChart chart;
    FakeUndo undo;
    FakeDocument document;
    int currentTick{960};
    mutable bool updated{false};
};
