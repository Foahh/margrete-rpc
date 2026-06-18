#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "Logger.h"

struct DiscoveryTransport
{
    std::string type;
    std::string endpoint;
    std::string path;
};

class DiscoveryRegistry
{
  public:
    static std::string CreateInstanceId();
    static std::filesystem::path Directory();
    static std::filesystem::path LogDirectory();
    static std::filesystem::path LogPath(const std::string &instanceId);
    static std::filesystem::path RecordPath(const std::string &instanceId);
    static void Publish(const std::string &instanceId, const std::vector<DiscoveryTransport> &transports,
                        const std::filesystem::path &logPath, const char *pluginVersion, Logger &logger);
    static void Remove(const std::string &instanceId, Logger &logger);
};
