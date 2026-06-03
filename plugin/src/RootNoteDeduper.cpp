#include "RootNoteDeduper.h"

#include <stdexcept>
#include <unordered_set>
#include <vector>

namespace
{
void Check(MpBoolean ok, const char *message)
{
    if (ok != MP_TRUE)
    {
        throw std::runtime_error(message);
    }
}
} // namespace

int RootNoteDeduper::Deduplicate(IMargretePluginChart &chart)
{
    std::vector<MargreteComPtr<IMargretePluginNote>> roots;
    const MpInteger count = chart.getNotesCount();
    roots.reserve(static_cast<std::size_t>(count));
    for (MpInteger index = 0; index < count; ++index)
    {
        IMargretePluginNote *note = nullptr;
        Check(chart.getNote(index, &note), "failed to read root note");
        if (!note)
        {
            throw std::runtime_error("root note is unavailable");
        }
        roots.emplace_back(note);
    }

    std::unordered_set<int> seen;
    int removed = 0;
    for (auto &note : roots)
    {
        const int id = note->getId();
        if (!seen.insert(id).second)
        {
            Check(chart.deleteNote(note.get()), "failed to delete duplicate root note");
            ++removed;
        }
    }
    return removed;
}
