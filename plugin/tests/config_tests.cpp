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
    REQUIRE(config.port == 0);
    REQUIRE(config.autoPort == true);
}

TEST_CASE("config reads server section")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-test.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "host = 127.0.0.1\n";
        out << "port = 49000\n";
    }

    const ServerConfig config = LoadServerConfig(path);

    REQUIRE(config.sourcePath == path);
    REQUIRE(config.loadedFromFile == true);
    REQUIRE(config.host == "127.0.0.1");
    REQUIRE(config.port == 49000);
    REQUIRE(config.autoPort == false);
}

TEST_CASE("config supports automatic port")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-auto.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "port = auto\n";
    }

    const ServerConfig config = LoadServerConfig(path);

    REQUIRE(config.port == 0);
    REQUIRE(config.autoPort == true);
}

TEST_CASE("config accepts explicit IPv4 host")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-host.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "host = 0.0.0.0\n";
    }

    const ServerConfig config = LoadServerConfig(path);

    REQUIRE(config.host == "0.0.0.0");
}

TEST_CASE("config rejects invalid host")
{
    const std::filesystem::path path = std::filesystem::temp_directory_path() / "margrete-rpc-bad-host.ini";
    {
        std::ofstream out(path);
        out << "[server]\n";
        out << "host = localhost\n";
    }

    REQUIRE_THROWS_WITH(LoadServerConfig(path), ContainsSubstring("server host must be an IPv4 address"));
}

TEST_CASE("loopback detection")
{
    REQUIRE(IsLoopbackAddress("127.0.0.1"));
    REQUIRE(IsLoopbackAddress("127.5.6.7"));
    REQUIRE_FALSE(IsLoopbackAddress("0.0.0.0"));
    REQUIRE_FALSE(IsLoopbackAddress("192.168.1.10"));
}
