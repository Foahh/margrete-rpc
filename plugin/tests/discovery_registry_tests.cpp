#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "DiscoveryRegistry.h"
#include "Logger.h"
#include "Utf8.h"

#if defined(_WIN32)
#include <windows.h>
#endif

using Catch::Matchers::ContainsSubstring;

namespace
{
void SetLocalAppData(const std::filesystem::path &value)
{
#if defined(_WIN32)
    SetEnvironmentVariableW(L"LOCALAPPDATA", value.empty() ? nullptr : value.c_str());
#else
    if (value.empty())
    {
        unsetenv("LOCALAPPDATA");
    }
    else
    {
        setenv("LOCALAPPDATA", value.string().c_str(), 1);
    }
#endif
}

class LocalAppDataGuard
{
  public:
    LocalAppDataGuard() : previous_(EnvironmentPath("LOCALAPPDATA")) {}

    ~LocalAppDataGuard()
    {
        SetLocalAppData(previous_);
    }

  private:
    std::filesystem::path previous_;
};
} // namespace

TEST_CASE("discovery publishes configured host")
{
    const LocalAppDataGuard localAppDataGuard;
    const std::filesystem::path base = std::filesystem::temp_directory_path() / "margrete-rpc-discovery-test";
    std::filesystem::remove_all(base);
    std::filesystem::create_directories(base);
    SetLocalAppData(base);

    {
        const std::string instanceId = "test-instance";
        const std::filesystem::path logPath = base / "test.log";
        Logger logger(logPath);

        DiscoveryRegistry::Publish(instanceId,
                                   std::vector<DiscoveryTransport>{
                                       DiscoveryTransport{"tcp", "192.168.1.23:49000", ""},
                                       DiscoveryTransport{"npipe", "", "\\\\.\\pipe\\margrete-rpc-test"},
                                   },
                                   logPath, "test-version", logger);

        const std::filesystem::path recordPath = base / "MargreteRPC" / "instances" / (instanceId + ".json");
        std::ifstream in(recordPath);
        REQUIRE(in);
        const std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        REQUIRE_THAT(content, ContainsSubstring("\"endpoint\": \"192.168.1.23:49000\""));
        REQUIRE_THAT(content, ContainsSubstring("\"schema_version\": 2"));
        REQUIRE_THAT(content, ContainsSubstring("\"type\": \"tcp\""));
        REQUIRE_THAT(content, ContainsSubstring("\"type\": \"npipe\""));
        REQUIRE_THAT(content, ContainsSubstring("\"path\": \"\\\\\\\\.\\\\pipe\\\\margrete-rpc-test\""));
    }

    std::filesystem::remove_all(base);
}

TEST_CASE("discovery publishes utf-8 log path")
{
    const LocalAppDataGuard localAppDataGuard;
    const std::filesystem::path base = std::filesystem::temp_directory_path() / "margrete-rpc-discovery-utf8-test";
    std::filesystem::remove_all(base);
    std::filesystem::create_directories(base);
    SetLocalAppData(base);

    {
        const std::string instanceId = "utf8-instance";
        const std::filesystem::path logPath = base / std::filesystem::path(u8"\u30c6\u30b9\u30c8.log");
        Logger logger(logPath);

        DiscoveryRegistry::Publish(instanceId, std::vector<DiscoveryTransport>{DiscoveryTransport{"tcp", "127.0.0.1:49000", ""}},
                                   logPath, "test-version", logger);

        const std::filesystem::path recordPath = base / "MargreteRPC" / "instances" / (instanceId + ".json");
        std::ifstream in(recordPath, std::ios::binary);
        REQUIRE(in);
        const std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        const std::string utf8LogName(reinterpret_cast<const char *>(u8"\u30c6\u30b9\u30c8.log"));
        REQUIRE_THAT(content, ContainsSubstring(utf8LogName));
    }

    std::filesystem::remove_all(base);
}

TEST_CASE("discovery directory keeps unicode local app data")
{
    const LocalAppDataGuard localAppDataGuard;
    const std::filesystem::path base =
        std::filesystem::temp_directory_path() / std::filesystem::path(u8"\u30c6\u30b9\u30c8-rpc");
    std::filesystem::remove_all(base);
    std::filesystem::create_directories(base);
    SetLocalAppData(base);

    REQUIRE(DiscoveryRegistry::Directory() == base / "MargreteRPC" / "instances");
    REQUIRE(DiscoveryRegistry::LogDirectory() == base / "MargreteRPC" / "logs");

    std::filesystem::remove_all(base);
}
