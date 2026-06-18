#include "DiscoveryRegistry.h"

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <random>
#include <sstream>
#include <vector>

#if defined(_WIN32)
#include <windows.h>
#endif

namespace
{
std::string JsonEscape(const std::string &value)
{
    std::string out;
    out.reserve(value.size() + 8);
    for (const char ch : value)
    {
        switch (ch)
        {
        case '\\':
            out += "\\\\";
            break;
        case '"':
            out += "\\\"";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            out += ch;
            break;
        }
    }
    return out;
}

unsigned long CurrentProcessId()
{
#if defined(_WIN32)
    return static_cast<unsigned long>(GetCurrentProcessId());
#else
    return 0;
#endif
}

std::uint64_t UnixTimeSeconds()
{
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count());
}
} // namespace

std::string DiscoveryRegistry::CreateInstanceId()
{
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<std::uint64_t> dist;

    std::ostringstream out;
    out << CurrentProcessId() << '-' << std::hex << UnixTimeSeconds() << '-' << dist(gen);
    return out.str();
}

std::filesystem::path DiscoveryRegistry::Directory()
{
    if (const char *localAppData = std::getenv("LOCALAPPDATA"); localAppData && *localAppData)
    {
        return std::filesystem::path(localAppData) / "MargreteRPC" / "instances";
    }
    return std::filesystem::temp_directory_path() / "MargreteRPC" / "instances";
}

std::filesystem::path DiscoveryRegistry::LogDirectory()
{
    if (const char *localAppData = std::getenv("LOCALAPPDATA"); localAppData && *localAppData)
    {
        return std::filesystem::path(localAppData) / "MargreteRPC" / "logs";
    }
    return std::filesystem::temp_directory_path() / "MargreteRPC" / "logs";
}

std::filesystem::path DiscoveryRegistry::LogPath(const std::string &instanceId)
{
    return LogDirectory() / ("margrete-rpc-" + instanceId + ".log");
}

std::filesystem::path DiscoveryRegistry::RecordPath(const std::string &instanceId)
{
    return Directory() / (instanceId + ".json");
}

void DiscoveryRegistry::Publish(const std::string &instanceId, const std::vector<DiscoveryTransport> &transports,
                                const std::filesystem::path &logPath, const char *pluginVersion, Logger &logger)
{
    try
    {
        const auto dir = Directory();
        std::filesystem::create_directories(dir);
        const auto recordPath = RecordPath(instanceId);
        const std::string endpoint = transports.empty() ? "" : transports.front().endpoint;

        std::ofstream out(recordPath, std::ios::trunc);
        out << "{\n";
        out << "  \"schema_version\": 2,\n";
        out << "  \"instance_id\": \"" << JsonEscape(instanceId) << "\",\n";
        out << "  \"pid\": " << CurrentProcessId() << ",\n";
        out << "  \"endpoint\": \"" << JsonEscape(endpoint) << "\",\n";
        out << "  \"transports\": [\n";
        for (std::size_t i = 0; i < transports.size(); ++i)
        {
            const auto &transport = transports[i];
            out << "    {\"type\": \"" << JsonEscape(transport.type) << "\"";
            if (!transport.endpoint.empty())
            {
                out << ", \"endpoint\": \"" << JsonEscape(transport.endpoint) << "\"";
            }
            if (!transport.path.empty())
            {
                out << ", \"path\": \"" << JsonEscape(transport.path) << "\"";
            }
            out << "}" << (i + 1 == transports.size() ? "" : ",") << "\n";
        }
        out << "  ],\n";
        out << "  \"started_at_unix\": " << UnixTimeSeconds() << ",\n";
        out << "  \"plugin_version\": \"" << JsonEscape(pluginVersion ? pluginVersion : "") << "\",\n";
        out << "  \"log\": \"" << JsonEscape(logPath.string()) << "\"\n";
        out << "}\n";
        if (!out)
        {
            logger.error("discovery publish failed path=" + recordPath.string());
            return;
        }
        logger.info("discovery published path=" + recordPath.string() + " endpoint=" + endpoint);
    }
    catch (const std::exception &ex)
    {
        logger.error(std::string("discovery publish failed: ") + ex.what());
    }
}

void DiscoveryRegistry::Remove(const std::string &instanceId, Logger &logger)
{
    try
    {
        const auto recordPath = RecordPath(instanceId);
        std::error_code ec;
        std::filesystem::remove(recordPath, ec);
        if (ec)
        {
            logger.error("discovery remove failed path=" + recordPath.string() + " error=" + ec.message());
            return;
        }
        logger.info("discovery removed path=" + recordPath.string());
    }
    catch (const std::exception &ex)
    {
        logger.error(std::string("discovery remove failed: ") + ex.what());
    }
}
