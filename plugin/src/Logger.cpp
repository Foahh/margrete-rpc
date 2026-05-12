#include "Logger.h"

#include <chrono>
#include <ctime>
#include <iomanip>

Logger::Logger(std::filesystem::path path) {
    out_.open(path, std::ios::app);
}

void Logger::info(const std::string& message) {
    write("INFO", message);
}

void Logger::error(const std::string& message) {
    write("ERROR", message);
}

void Logger::write(const char* level, const std::string& message) {
    std::scoped_lock lock(mutex_);
    if (!out_) {
        return;
    }
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);
#if defined(_WIN32)
    std::tm tm_buf {};
    localtime_s(&tm_buf, &time);
    std::tm* tm = &tm_buf;
#else
    std::tm* tm = std::localtime(&time);
#endif
    out_ << std::put_time(tm, "%Y-%m-%d %H:%M:%S") << " [" << level << "] " << message << '\n';
    out_.flush();
}
