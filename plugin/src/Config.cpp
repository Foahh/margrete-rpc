#include "Config.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <ranges>
#include <stdexcept>

namespace
{
std::string Trim(std::string value)
{
    const auto notSpace = [](unsigned char ch) { return !std::isspace(ch); };
    value.erase(value.begin(), std::ranges::find_if(value, notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
    return value;
}
} // namespace

ServerConfig LoadServerConfig(const std::filesystem::path &iniPath)
{
    ServerConfig config;
    config.sourcePath = iniPath;
    std::ifstream in(iniPath);
    if (!in)
    {
        return config;
    }
    config.loadedFromFile = true;

    std::string section;
    std::string line;
    while (std::getline(in, line))
    {
        line = Trim(line);
        if (line.empty() || line.starts_with(';') || line.starts_with('#'))
        {
            continue;
        }
        if (line.starts_with('[') && line.ends_with(']'))
        {
            section = line.substr(1, line.size() - 2);
            continue;
        }
        const std::size_t pos = line.find('=');
        if (pos == std::string::npos)
        {
            continue;
        }
        const std::string key = Trim(line.substr(0, pos));
        const std::string value = Trim(line.substr(pos + 1));
        if (section == "server" && key == "host")
        {
            config.host = value;
        }
        else if (section == "server" && key == "port")
        {
            if (value == "auto")
            {
                config.port = 0;
                config.autoPort = true;
                continue;
            }
            const int port = std::stoi(value);
            if (port < 0 || port > 65535)
            {
                throw std::runtime_error("server port must be auto or between 0 and 65535");
            }
            config.port = static_cast<std::uint16_t>(port);
            config.autoPort = port == 0;
        }
    }

    if (config.host != "127.0.0.1")
    {
        throw std::runtime_error("server host must be 127.0.0.1");
    }
    return config;
}
