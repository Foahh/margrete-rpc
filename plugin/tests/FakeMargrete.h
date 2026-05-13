#pragma once

#include <algorithm>
#include <vector>

#include <MargretePlugin.h>

class FakeBase
{
  public:
    MpInteger addRef()
    {
        return ++refCount;
    }
    MpInteger release()
    {
        return --refCount;
    }
    MpBoolean queryInterface(const MpGuid &, void **)
    {
        return MP_FALSE;
    }
    MpInteger refCountValue() const
    {
        return refCount;
    }

  private:
    MpInteger refCount{1};
};

class FakeNote final : public IMargretePluginNote, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &iid, void **ppobj) override
    {
        return FakeBase::queryInterface(iid, ppobj);
    }
    MpInteger getId() const override
    {
        return id;
    }
    void getInfo(MP_NOTEINFO *noteInfo) const override
    {
        *noteInfo = info;
    }
    void setInfo(const MP_NOTEINFO *noteInfo) override
    {
        info = *noteInfo;
    }
    MpInteger getChildrenCount() const override
    {
        return static_cast<MpInteger>(children.size());
    }
    MpBoolean getChild(MpInteger index, IMargretePluginNote **ppobj) const override
    {
        if (index < 0 || index >= static_cast<MpInteger>(children.size()))
        {
            return MP_FALSE;
        }
        *ppobj = children[static_cast<std::size_t>(index)];
        return MP_TRUE;
    }
    MpBoolean getParent(IMargretePluginNote **) const override
    {
        return MP_FALSE;
    }
    MpBoolean appendChild(IMargretePluginNote *note) override
    {
        children.push_back(note);
        return MP_TRUE;
    }
    MpBoolean deleteChild(IMargretePluginNote *) override
    {
        return MP_TRUE;
    }
    MpBoolean clone(IMargretePluginNote **) const override
    {
        return MP_FALSE;
    }
    void replaceWith(const IMargretePluginNote *, MpBoolean) override
    {
    }
    void copyInfoTo(IMargretePluginNote *) const override
    {
    }
    MpBoolean getBaseNote(IMargretePluginNote **) const override
    {
        return MP_FALSE;
    }
    void offsetChild(MpInteger) override
    {
    }
    void flipH(MpBoolean) override
    {
    }

    int id{1};
    MP_NOTEINFO info{};
    std::vector<IMargretePluginNote *> children;
};

class FakeBpmEvent final : public IMargretePluginEventBpm, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &, void **) override
    {
        return MP_FALSE;
    }
    MpInteger getId() const override
    {
        return 1;
    }
    void getInfo(MP_EVENT_BPMINFO *out) const override
    {
        *out = info;
    }
    void setInfo(const MP_EVENT_BPMINFO *in) override
    {
        info = *in;
    }
    void replaceWith(const IMargretePluginEventBpm *) override
    {
    }
    void copyInfoTo(IMargretePluginEventBpm *) const override
    {
    }
    MP_EVENT_BPMINFO info{};
};

class FakeBeatEvent final : public IMargretePluginEventBeatChange, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &, void **) override
    {
        return MP_FALSE;
    }
    MpInteger getId() const override
    {
        return 1;
    }
    void getInfo(MP_EVENT_BCINFO *out) const override
    {
        *out = info;
    }
    void setInfo(const MP_EVENT_BCINFO *in) override
    {
        info = *in;
    }
    void replaceWith(const IMargretePluginEventBeatChange *) override
    {
    }
    void copyInfoTo(IMargretePluginEventBeatChange *) const override
    {
    }
    MP_EVENT_BCINFO info{};
};

class FakeTimelineSpeedEvent final : public IMargretePluginEventTimelineSpeed, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &, void **) override
    {
        return MP_FALSE;
    }
    MpInteger getId() const override
    {
        return 1;
    }
    void getInfo(MP_EVENT_TLSINFO *out) const override
    {
        *out = info;
    }
    void setInfo(const MP_EVENT_TLSINFO *in) override
    {
        info = *in;
    }
    void replaceWith(const IMargretePluginEventTimelineSpeed *) override
    {
    }
    void copyInfoTo(IMargretePluginEventTimelineSpeed *) const override
    {
    }
    MP_EVENT_TLSINFO info{};
};

class FakeNoteSpeedEvent final : public IMargretePluginEventNoteSpeedModifier, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &, void **) override
    {
        return MP_FALSE;
    }
    MpInteger getId() const override
    {
        return 1;
    }
    void getInfo(MP_EVENT_NSMINFO *out) const override
    {
        *out = info;
    }
    void setInfo(const MP_EVENT_NSMINFO *in) override
    {
        info = *in;
    }
    void replaceWith(const IMargretePluginEventNoteSpeedModifier *) override
    {
    }
    void copyInfoTo(IMargretePluginEventNoteSpeedModifier *) const override
    {
    }
    MP_EVENT_NSMINFO info{};
};

class FakeChart final : public IMargretePluginChart, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &iid, void **ppobj) override
    {
        return FakeBase::queryInterface(iid, ppobj);
    }
    MpBoolean createNote(IMargretePluginNote **ppobj) const override
    {
        createdNotes.push_back(new FakeNote());
        *ppobj = createdNotes.back();
        return MP_TRUE;
    }
    FakeNote *addExistingNote(int id)
    {
        notes.push_back(new FakeNote());
        notes.back()->id = id;
        return notes.back();
    }

    FakeNote *addDetachedNote(int id)
    {
        detachedNotes.push_back(new FakeNote());
        detachedNotes.back()->id = id;
        return detachedNotes.back();
    }

    MpInteger getNotesCount() const override
    {
        return static_cast<MpInteger>(notes.size());
    }
    MpBoolean getNote(MpInteger index, IMargretePluginNote **ppobj) override
    {
        if (index < 0 || index >= static_cast<MpInteger>(notes.size()))
        {
            return MP_FALSE;
        }
        *ppobj = notes[static_cast<std::size_t>(index)];
        return MP_TRUE;
    }
    MpBoolean appendNote(IMargretePluginNote *note) override
    {
        ++appendedNotes;
        auto *fake = static_cast<FakeNote *>(note);
        notes.push_back(fake);
        return MP_TRUE;
    }
    MpBoolean deleteNote(IMargretePluginNote *note) override
    {
        ++deletedNotes;
        auto *fake = static_cast<FakeNote *>(note);
        notes.erase(std::remove(notes.begin(), notes.end(), fake), notes.end());
        return MP_TRUE;
    }
    void offsetNotes(MpInteger) override
    {
    }
    MpBoolean createEvent(const MpGuid &iid, void **ppobj) const override
    {
        if (!ppobj)
        {
            return MP_FALSE;
        }
        if (iid == IID_IMargretePluginEventBpm)
        {
            createdBpmEvents.push_back(new FakeBpmEvent());
            *ppobj = createdBpmEvents.back();
            return MP_TRUE;
        }
        if (iid == IID_IMargretePluginEventBeatChange)
        {
            createdBeatEvents.push_back(new FakeBeatEvent());
            *ppobj = createdBeatEvents.back();
            return MP_TRUE;
        }
        if (iid == IID_IMargretePluginEventTimelineSpeed)
        {
            createdTimelineSpeedEvents.push_back(new FakeTimelineSpeedEvent());
            *ppobj = createdTimelineSpeedEvents.back();
            return MP_TRUE;
        }
        if (iid == IID_IMargretePluginEventNoteSpeedModifier)
        {
            createdNoteSpeedEvents.push_back(new FakeNoteSpeedEvent());
            *ppobj = createdNoteSpeedEvents.back();
            return MP_TRUE;
        }
        return MP_FALSE;
    }
    MpBoolean appendEvent(IMargretePluginEvent *) override
    {
        ++appendedEvents;
        return MP_TRUE;
    }
    MpBoolean deleteEvent(IMargretePluginEvent *event) override
    {
        ++deletedEvents;
        deletedEventPointers.push_back(event);
        existingBpmEvents.erase(std::remove(existingBpmEvents.begin(), existingBpmEvents.end(), event),
                                existingBpmEvents.end());
        existingBeatEvents.erase(std::remove(existingBeatEvents.begin(), existingBeatEvents.end(), event),
                                 existingBeatEvents.end());
        existingTimelineSpeedEvents.erase(
            std::remove(existingTimelineSpeedEvents.begin(), existingTimelineSpeedEvents.end(), event),
            existingTimelineSpeedEvents.end());
        existingNoteSpeedEvents.erase(
            std::remove(existingNoteSpeedEvents.begin(), existingNoteSpeedEvents.end(), event),
            existingNoteSpeedEvents.end());
        return MP_TRUE;
    }
    FakeBpmEvent *addExistingBpmEvent(int tick, double bpm)
    {
        existingBpmEvents.push_back(new FakeBpmEvent());
        existingBpmEvents.back()->info.tick = tick;
        existingBpmEvents.back()->info.bpm = bpm;
        return existingBpmEvents.back();
    }

    FakeBeatEvent *addExistingBeatEvent(int bar, int beatsPerBar, int beatUnit)
    {
        existingBeatEvents.push_back(new FakeBeatEvent());
        existingBeatEvents.back()->info.bar = bar;
        existingBeatEvents.back()->info.beatsPerBar = beatsPerBar;
        existingBeatEvents.back()->info.beatUnit = beatUnit;
        return existingBeatEvents.back();
    }

    FakeTimelineSpeedEvent *addExistingTimelineSpeedEvent(int tick, int timelineId, double speed)
    {
        existingTimelineSpeedEvents.push_back(new FakeTimelineSpeedEvent());
        existingTimelineSpeedEvents.back()->info.tick = tick;
        existingTimelineSpeedEvents.back()->info.timelineId = timelineId;
        existingTimelineSpeedEvents.back()->info.speed = speed;
        return existingTimelineSpeedEvents.back();
    }

    FakeNoteSpeedEvent *addExistingNoteSpeedEvent(int tick, double speed)
    {
        existingNoteSpeedEvents.push_back(new FakeNoteSpeedEvent());
        existingNoteSpeedEvents.back()->info.tick = tick;
        existingNoteSpeedEvents.back()->info.speed = speed;
        return existingNoteSpeedEvents.back();
    }

    MpBoolean findEventBpm(MpInteger tick, void **ppobj) override
    {
        for (auto *event : existingBpmEvents)
        {
            if (event->info.tick == tick)
            {
                *ppobj = event;
                return MP_TRUE;
            }
        }
        return MP_FALSE;
    }
    MpBoolean findEventBeatChange(MpInteger bar, void **ppobj) override
    {
        for (auto *event : existingBeatEvents)
        {
            if (event->info.bar == bar)
            {
                *ppobj = event;
                return MP_TRUE;
            }
        }
        return MP_FALSE;
    }
    MpBoolean findEventTimelineSpeed(MpInteger tick, MpInteger timelineId, void **ppobj) override
    {
        for (auto *event : existingTimelineSpeedEvents)
        {
            if (event->info.tick == tick && event->info.timelineId == timelineId)
            {
                *ppobj = event;
                return MP_TRUE;
            }
        }
        return MP_FALSE;
    }
    MpBoolean findEventNoteSpeedModifier(MpInteger tick, void **ppobj) override
    {
        for (auto *event : existingNoteSpeedEvents)
        {
            if (event->info.tick == tick)
            {
                *ppobj = event;
                return MP_TRUE;
            }
        }
        return MP_FALSE;
    }

    std::vector<FakeNote *> notes;
    std::vector<FakeNote *> detachedNotes;
    std::vector<FakeBpmEvent *> existingBpmEvents;
    std::vector<FakeBeatEvent *> existingBeatEvents;
    std::vector<FakeTimelineSpeedEvent *> existingTimelineSpeedEvents;
    std::vector<FakeNoteSpeedEvent *> existingNoteSpeedEvents;
    mutable std::vector<FakeNote *> createdNotes;
    mutable std::vector<FakeBpmEvent *> createdBpmEvents;
    mutable std::vector<FakeBeatEvent *> createdBeatEvents;
    mutable std::vector<FakeTimelineSpeedEvent *> createdTimelineSpeedEvents;
    mutable std::vector<FakeNoteSpeedEvent *> createdNoteSpeedEvents;
    int appendedNotes{0};
    int appendedEvents{0};
    int deletedNotes{0};
    int deletedEvents{0};
    std::vector<IMargretePluginEvent *> deletedEventPointers;
};

class FakeUndo final : public IMargretePluginUndoBuffer, public FakeBase
{
  public:
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &iid, void **ppobj) override
    {
        return FakeBase::queryInterface(iid, ppobj);
    }
    MpBoolean beginRecording() override
    {
        ++beginCount;
        return MP_TRUE;
    }
    MpBoolean commitRecording() override
    {
        ++commitCount;
        return MP_TRUE;
    }
    MpBoolean discardRecording() override
    {
        ++discardCount;
        return MP_TRUE;
    }
    MpBoolean undo() override
    {
        return MP_TRUE;
    }
    MpBoolean redo() override
    {
        return MP_TRUE;
    }
    MpBoolean canUndo() const override
    {
        return MP_TRUE;
    }
    MpBoolean canRedo() const override
    {
        return MP_FALSE;
    }
    MpBoolean isRecording() const override
    {
        return beginCount > commitCount + discardCount;
    }

    int beginCount{0};
    int commitCount{0};
    int discardCount{0};
};

class FakeDocument final : public IMargretePluginDocument, public FakeBase
{
  public:
    explicit FakeDocument(FakeChart &chartIn, FakeUndo &undoIn) : chart(chartIn), undo(undoIn)
    {
    }
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &iid, void **ppobj) override
    {
        return FakeBase::queryInterface(iid, ppobj);
    }
    MpBoolean getChart(IMargretePluginChart **ppobj) override
    {
        *ppobj = &chart;
        return MP_TRUE;
    }
    MpBoolean getUndoBuffer(IMargretePluginUndoBuffer **ppobj) override
    {
        *ppobj = &undo;
        return MP_TRUE;
    }

    FakeChart &chart;
    FakeUndo &undo;
};

class FakeContext final : public IMargretePluginContext, public FakeBase
{
  public:
    FakeContext() : document(chart, undo)
    {
    }
    MpInteger addRef() override
    {
        return FakeBase::addRef();
    }
    MpInteger release() override
    {
        return FakeBase::release();
    }
    MpBoolean queryInterface(const MpGuid &iid, void **ppobj) override
    {
        return FakeBase::queryInterface(iid, ppobj);
    }
    MpBoolean getDocument(IMargretePluginDocument **ppobj) override
    {
        *ppobj = &document;
        return MP_TRUE;
    }
    void *getMainWindowHandle() override
    {
        return nullptr;
    }
    MpInteger getCurrentTick() const override
    {
        return currentTick;
    }
    void update() const override
    {
        updated = true;
    }

    FakeChart chart;
    FakeUndo undo;
    FakeDocument document;
    int currentTick{960};
    mutable bool updated{false};
};
