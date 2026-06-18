#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "DiscoveryRegistry.h"
#include "Logger.h"

#if defined(_WIN32)
#include <stdlib.h>
#endif

using Catch::Matchers::ContainsSubstring;

namespace
{
void SetLocalAppData(const std::string &value)
{
#if defined(_WIN32)
    _putenv_s("LOCALAPPDATA", value.c_str());
#else
    setenv("LOCALAPPDATA", value.c_str(), 1);
#endif
}

void RestoreLocalAppData(bool hadPrevious, const std::string &previous)
{
#if defined(_WIN32)
    _putenv_s("LOCALAPPDATA", hadPrevious ? previous.c_str() : "");
#else
    if (hadPrevious)
    {
        setenv("LOCALAPPDATA", previous.c_str(), 1);
    }
    else
    {
        unsetenv("LOCALAPPDATA");
    }
#endif
}

class LocalAppDataGuard
{
  public:
    LocalAppDataGuard()
    {
        const char *value = std::getenv("LOCALAPPDATA");
        hadPrevious_ = value != nullptr;
        previous_ = value ? value : "";
    }

    ~LocalAppDataGuard()
    {
        RestoreLocalAppData(hadPrevious_, previous_);
    }

  private:
    bool hadPrevious_{false};
    std::string previous_;
};
} // namespace

TEST_CASE("discovery publishes configured host")
{
    const LocalAppDataGuard localAppDataGuard;
    const std::filesystem::path base = std::filesystem::temp_directory_path() / "margrete-rpc-discovery-test";
    std::filesystem::remove_all(base);
    std::filesystem::create_directories(base);
    SetLocalAppData(base.string());

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
