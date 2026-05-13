#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include <filesystem>
#include <fstream>

#include "Config.h"

using Catch::Matchers::ContainsSubstring;

TEST_CASE("config uses defaults when file is missing")
{
    const ServerConfig config = LoadServerConfig("missing-file.ini");
    REQUIRE(config.sourcePath.filename().string() == "missing-file.ini");
    REQUIRE(config.loadedFromFile == false);
    REQUIRE(config.host == "127.0.0.1");
    REQUIRE(config.port == 48731);
    REQUIRE(config.logPath.filename().string() == "margrete-rpc.log");
}

TEST_CASE("config reads server section")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-test.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "host = 127.0.0.1\n";
        out << "port = 49000\n";
        out << "log = custom.log\n";
    }

    const ServerConfig config = LoadServerConfig(path);

    REQUIRE(config.sourcePath == path);
    REQUIRE(config.loadedFromFile == true);
    REQUIRE(config.host == "127.0.0.1");
    REQUIRE(config.port == 49000);
    REQUIRE(config.logPath.filename().string() == "custom.log");
}

TEST_CASE("config rejects non-localhost host")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-bad.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "host = 0.0.0.0\n";
    }

    REQUIRE_THROWS_WITH(LoadServerConfig(path), ContainsSubstring("server host must be 127.0.0.1"));
}
