#pragma once

#include <functional>
#include <string>

#include <MargretePlugin.h>

#include "ServerController.h"

using ReloadServerConfigFn = std::function<std::string()>;

void ShowServerStatusDialog(IMargretePluginContext *context, ServerController &controller, std::string configError,
                            ReloadServerConfigFn reloadConfig);
