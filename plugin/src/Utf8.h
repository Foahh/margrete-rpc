#pragma once

#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>

#if defined(_WIN32)
#include <windows.h>
#endif

inline std::string PathUtf8(const std::filesystem::path &path)
{
    const std::u8string utf8 = path.u8string();
    return {utf8.begin(), utf8.end()};
}

inline std::filesystem::path EnvironmentPath(const char *name)
{
    if (name == nullptr || *name == '\0')
    {
        return {};
    }
#if defined(_WIN32)
    std::wstring wideName(static_cast<std::size_t>(std::strlen(name)), L'\0');
    for (std::size_t i = 0; i < wideName.size(); ++i)
    {
        wideName[i] = static_cast<wchar_t>(static_cast<unsigned char>(name[i]));
    }
    const DWORD needed = GetEnvironmentVariableW(wideName.c_str(), nullptr, 0);
    if (needed == 0)
    {
        return {};
    }
    std::wstring value(static_cast<std::size_t>(needed), L'\0');
    const DWORD n = GetEnvironmentVariableW(wideName.c_str(), value.data(), needed);
    if (n == 0)
    {
        return {};
    }
    value.resize(static_cast<std::size_t>(n));
    return std::filesystem::path(std::move(value));
#else
    if (const char *value = std::getenv(name); value && *value)
    {
        return std::filesystem::path(value);
    }
    return {};
#endif
}
