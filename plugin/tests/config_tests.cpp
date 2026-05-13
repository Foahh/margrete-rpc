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
    REQUIRE(config.eventScanExtraTicks == 768000);
    REQUIRE(config.eventScanMaxTil == 31);
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

TEST_CASE("config reads chart editing scan limits")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-chart-editing.ini";
    {
        std::ofstream out(path);
        out << "[chart_editing]\n";
        out << "event_scan_extra_ticks = 2400\n";
        out << "event_scan_max_til = 9600\n";
    }

    const ServerConfig config = LoadServerConfig(path);

    REQUIRE(config.eventScanExtraTicks == 2400);
    REQUIRE(config.eventScanMaxTil == 9600);
}

TEST_CASE("config rejects non-positive chart editing scan limits")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-chart-editing-bad.ini";
    {
        std::ofstream out(path);
        out << "[chart_editing]\n";
        out << "event_scan_extra_ticks = 0\n";
        out << "event_scan_max_til = -1\n";
    }

    REQUIRE_THROWS_WITH(LoadServerConfig(path), ContainsSubstring("chart editing scan limits must be positive"));
}
