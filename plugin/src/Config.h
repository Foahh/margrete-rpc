#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

struct ServerConfig
{
    std::string host{"127.0.0.1"};
    std::uint16_t port{48731};
    std::filesystem::path logPath{"margrete-rpc.log"};
    std::int32_t eventScanExtraTicks{768000};
    std::int32_t maxScanTil{16384};
};

ServerConfig LoadServerConfig(const std::filesystem::path &iniPath);
