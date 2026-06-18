#include "Config.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <ranges>
#include <stdexcept>
#include <string_view>

namespace
{
std::string Trim(std::string value)
{
    const auto notSpace = [](unsigned char ch) { return !std::isspace(ch); };
    value.erase(value.begin(), std::ranges::find_if(value, notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
    return value;
}

bool IsValidIpv4Address(std::string_view value)
{
    if (value.empty())
    {
        return false;
    }

    int octetCount = 0;
    std::size_t start = 0;
    while (start <= value.size())
    {
        const std::size_t dot = value.find('.', start);
        const std::size_t end = dot == std::string_view::npos ? value.size() : dot;
        const std::string_view octet = value.substr(start, end - start);
        if (octet.empty() || octet.size() > 3)
        {
            return false;
        }

        int number = 0;
        for (const char ch : octet)
        {
            if (!std::isdigit(static_cast<unsigned char>(ch)))
            {
                return false;
            }
            number = number * 10 + (ch - '0');
        }
        if (number > 255)
        {
            return false;
        }

        ++octetCount;
        if (dot == std::string_view::npos)
        {
            break;
        }
        start = dot + 1;
    }
    return octetCount == 4;
}

ServerTransportMode ParseTransportMode(std::string_view value)
{
    if (value == "tcp")
    {
        return ServerTransportMode::Tcp;
    }
    if (value == "pipe" || value == "npipe")
    {
        return ServerTransportMode::Pipe;
    }
    if (value == "both")
    {
        return ServerTransportMode::Both;
    }
    throw std::runtime_error("server transport must be tcp, pipe, or both");
}

bool IsValidPipeName(std::string_view value)
{
    if (value.empty())
    {
        return false;
    }
    return value.find_first_of("\\/:*?\"<>|") == std::string_view::npos;
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
        else if (section == "server" && key == "transport")
        {
            config.transport = ParseTransportMode(value);
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
        else if (section == "server" && key == "pipe_name")
        {
            config.pipeName = value;
        }
    }

    if (!IsValidIpv4Address(config.host))
    {
        throw std::runtime_error("server host must be an IPv4 address");
    }
    if (config.pipeName != "auto" && !IsValidPipeName(config.pipeName))
    {
        throw std::runtime_error("server pipe_name must be auto or a simple pipe name");
    }
    return config;
}

bool IsLoopbackAddress(std::string_view host)
{
    return host.starts_with("127.");
}

std::string_view TransportModeName(ServerTransportMode mode)
{
    switch (mode)
    {
    case ServerTransportMode::Tcp:
        return "tcp";
    case ServerTransportMode::Pipe:
        return "pipe";
    case ServerTransportMode::Both:
        return "both";
    }
    return "both";
}
