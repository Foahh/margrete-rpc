#pragma once

#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>

class Logger {
public:
    explicit Logger(std::filesystem::path path);
    void info(const std::string& message);
    void error(const std::string& message);

private:
    void write(const char* level, const std::string& message);

    std::mutex mutex_;
    std::ofstream out_;
};
