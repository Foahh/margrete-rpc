#include "Dialog.h"

#include "meta.h"

#include <exception>
#include <iterator>
#include <sstream>
#include <string>
#include <string_view>
#include <utility>

#if defined(_WIN32)
// clang-format off
#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
// clang-format on
#endif

namespace
{
#if defined(_WIN32)
constexpr wchar_t kDialogClassName[] = L"MargreteRpcServerStatusWindow";
constexpr UINT_PTR kRefreshTimerId = 1;
constexpr UINT kRefreshIntervalMs = 1000;

constexpr int kStartStopButtonId = 1001;
constexpr int kOpenConfigButtonId = 1002;
constexpr int kOpenLogButtonId = 1004;

constexpr int kControlHeight = 30;
constexpr int kSectionHeight = 28;
constexpr int kErrorHeight = 56;
constexpr int kPadding = 20;
constexpr int kTopPadding = 12;
constexpr int kRowGap = 8;
constexpr int kSectionGap = 14;

std::wstring WideFromUtf8(std::string_view text)
{
    if (text.empty())
    {
        return {};
    }
    const int len = MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), nullptr, 0);
    if (len <= 0)
    {
        return std::wstring(text.begin(), text.end());
    }
    std::wstring value(static_cast<std::size_t>(len), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), value.data(), len);
    return value;
}

std::wstring WideFromPath(const std::filesystem::path &path)
{
    return path.empty() ? L"(none)" : path.wstring();
}

std::wstring EndpointText(const ServerControllerStatus &status)
{
    if (!status.running)
    {
        return L"(stopped)";
    }

    const ServerConfig &effectiveConfig = status.hasActiveConfig ? status.activeConfig : status.loadedConfig;
    std::wostringstream out;
    out << WideFromUtf8(effectiveConfig.host) << L":";
    out << (status.actualPort == 0 ? L"(starting)" : std::to_wstring(status.actualPort));
    return out.str();
}

bool ActiveConfigDiffers(const ServerControllerStatus &status)
{
    return status.running && status.hasActiveConfig &&
           (status.loadedConfig.host != status.activeConfig.host ||
            status.loadedConfig.port != status.activeConfig.port ||
            status.loadedConfig.autoPort != status.activeConfig.autoPort);
}

std::wstring GetText(HWND hwnd)
{
    const int length = GetWindowTextLengthW(hwnd);
    if (length <= 0)
    {
        return {};
    }

    std::wstring text(static_cast<std::size_t>(length) + 1, L'\0');
    const int copied = GetWindowTextW(hwnd, text.data(), length + 1);
    text.resize(copied > 0 ? static_cast<std::size_t>(copied) : 0);
    return text;
}

void SetText(HWND hwnd, const wchar_t *text)
{
    const std::wstring_view nextText = text ? std::wstring_view(text) : std::wstring_view();
    if (GetText(hwnd) == nextText)
    {
        return;
    }

    const bool hasFocus = GetFocus() == hwnd;
    DWORD selectionStart = 0;
    DWORD selectionEnd = 0;
    if (hasFocus)
    {
        SendMessageW(hwnd, EM_GETSEL, reinterpret_cast<WPARAM>(&selectionStart),
                     reinterpret_cast<LPARAM>(&selectionEnd));
    }

    SetWindowTextW(hwnd, text ? text : L"");

    if (hasFocus)
    {
        const auto maxSelection = static_cast<DWORD>(nextText.size());
        if (selectionStart > maxSelection)
        {
            selectionStart = maxSelection;
        }
        if (selectionEnd > maxSelection)
        {
            selectionEnd = maxSelection;
        }
        SendMessageW(hwnd, EM_SETSEL, selectionStart, selectionEnd);
    }
}

void SetText(HWND hwnd, const std::wstring &text)
{
    SetText(hwnd, text.c_str());
}

HFONT CreateMessageFont(int pointSizeDelta = 0, LONG weight = FW_NORMAL)
{
    NONCLIENTMETRICSW metrics{};
    metrics.cbSize = sizeof(metrics);
    if (SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, metrics.cbSize, &metrics, 0) == 0)
    {
        return nullptr;
    }

    LOGFONTW font = metrics.lfMessageFont;
    font.lfWeight = weight;
    if (pointSizeDelta != 0)
    {
        HDC dc = GetDC(nullptr);
        const int dpiY = dc ? GetDeviceCaps(dc, LOGPIXELSY) : 96;
        if (dc)
        {
            ReleaseDC(nullptr, dc);
        }
        const int currentPoints = MulDiv(-font.lfHeight, 72, dpiY);
        font.lfHeight = -MulDiv(currentPoints + pointSizeDelta, dpiY, 72);
    }
    return CreateFontIndirectW(&font);
}

HWND AddControl(HWND parent, const wchar_t *className, const wchar_t *text, DWORD style, DWORD exStyle, int id, int x,
                int y, int width, int height, HFONT font)
{
    HWND hwnd = CreateWindowExW(exStyle, className, text, WS_CHILD | WS_VISIBLE | style, x, y, width, height, parent,
                                reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), GetModuleHandleW(nullptr), nullptr);
    if (font)
    {
        SendMessageW(hwnd, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    }
    return hwnd;
}

HWND AddLabel(HWND parent, const wchar_t *text, int x, int y, int width, int height, HFONT font)
{
    return AddControl(parent, L"STATIC", text, SS_LEFT | SS_NOPREFIX | SS_CENTERIMAGE, 0, 0, x, y, width, height, font);
}

HWND AddValue(HWND parent, int x, int y, int width, int height, HFONT font)
{
    return AddControl(parent, L"EDIT", L"", ES_READONLY | ES_AUTOHSCROLL, WS_EX_CLIENTEDGE, 0, x, y, width, height,
                      font);
}

HWND AddButton(HWND parent, const wchar_t *text, int id, int x, int y, int width, int height, HFONT font)
{
    return AddControl(parent, L"BUTTON", text, BS_PUSHBUTTON, 0, id, x, y, width, height, font);
}

struct ServerStatusWindow
{
    IMargretePluginContext *context{};
    ServerController *controller{};
    ReloadServerConfigFn reloadConfig;
    std::string configError;

    HWND hwnd{};
    HWND parent{};
    HWND endpointValue{};
    HWND loadedPathValue{};
    HWND instanceValue{};
    HWND logValue{};
    HWND errorLabel{};
    HWND errorValue{};
    HWND startStopButton{};
    HWND openConfigButton{};
    HWND openLogButton{};

    HFONT font{};
    HFONT boldFont{};
    HBRUSH backgroundBrush{};
    int normalClientHeight{};
    int messageClientHeight{};
    bool messageControlsVisible{true};
    std::wstring endpointText;
    std::wstring configPathText;
    std::wstring logPathText;

    explicit ServerStatusWindow(IMargretePluginContext *ctx, ServerController &ctrl, std::string error,
                                ReloadServerConfigFn reload)
        : context(ctx), controller(&ctrl), reloadConfig(std::move(reload)), configError(std::move(error))
    {
        parent = context ? static_cast<HWND>(context->getMainWindowHandle()) : nullptr;
        font = CreateMessageFont();
        boldFont = CreateMessageFont(0, FW_SEMIBOLD);
        backgroundBrush = CreateSolidBrush(RGB(248, 248, 248));
    }

    ~ServerStatusWindow()
    {
        if (backgroundBrush)
        {
            DeleteObject(backgroundBrush);
        }
        if (boldFont)
        {
            DeleteObject(boldFont);
        }
        if (font)
        {
            DeleteObject(font);
        }
    }

    void showModal()
    {
        EnsureWindowClass();

        hwnd =
            CreateWindowExW(WS_EX_DLGMODALFRAME, kDialogClassName, W_DIALOG_TITLE, WS_CAPTION | WS_SYSMENU,
                            CW_USEDEFAULT, CW_USEDEFAULT, 620, 390, parent, nullptr, GetModuleHandleW(nullptr), this);
        if (!hwnd)
        {
            return;
        }

        if (parent)
        {
            EnableWindow(parent, FALSE);
        }

        ShowWindow(hwnd, SW_SHOW);
        UpdateWindow(hwnd);

        MSG msg{};
        while (IsWindow(hwnd) && GetMessageW(&msg, nullptr, 0, 0) > 0)
        {
            if (!IsDialogMessageW(hwnd, &msg))
            {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }

        if (parent)
        {
            EnableWindow(parent, TRUE);
            SetActiveWindow(parent);
        }
    }

    void createControls()
    {
        RECT clientRect{};
        GetClientRect(hwnd, &clientRect);

        constexpr int labelX = kPadding;
        constexpr int labelWidth = 78;
        constexpr int valueX = 106;
        constexpr int buttonWidth = 95;

        const int rightEdge = clientRect.right - kPadding;
        const int actionX = rightEdge - buttonWidth;
        const int endpointWidth = actionX - kRowGap - valueX;
        const int fullValueWidth = rightEdge - valueX;

        int y = kTopPadding;

        AddLabel(hwnd, L"Server", labelX, y, 90, kSectionHeight, boldFont);
        y += kSectionHeight + kRowGap;

        AddLabel(hwnd, L"Endpoint", labelX, y, labelWidth, kControlHeight, font);
        endpointValue = AddValue(hwnd, valueX, y, endpointWidth, kControlHeight, font);
        startStopButton = AddButton(hwnd, L"", kStartStopButtonId, actionX, y, buttonWidth, kControlHeight, font);
        y += kControlHeight + kSectionGap;

        AddLabel(hwnd, L"Runtime", labelX, y, 180, kSectionHeight, boldFont);
        y += kSectionHeight + kRowGap;

        AddLabel(hwnd, L"Instance", labelX, y, labelWidth, kControlHeight, font);
        instanceValue = AddValue(hwnd, valueX, y, fullValueWidth, kControlHeight, font);
        y += kControlHeight + kRowGap;

        AddLabel(hwnd, L"Config", labelX, y, labelWidth, kControlHeight, font);
        loadedPathValue = AddValue(hwnd, valueX, y, actionX - kRowGap - valueX, kControlHeight, font);
        openConfigButton = AddButton(hwnd, L"Open", kOpenConfigButtonId, actionX, y, buttonWidth, kControlHeight, font);
        y += kControlHeight + kRowGap;

        AddLabel(hwnd, L"Log", labelX, y, labelWidth, kControlHeight, font);
        logValue = AddValue(hwnd, valueX, y, actionX - kRowGap - valueX, kControlHeight, font);
        openLogButton = AddButton(hwnd, L"Open", kOpenLogButtonId, actionX, y, buttonWidth, kControlHeight, font);
        y += kControlHeight;

        normalClientHeight = y + kPadding;
        y += kSectionGap;

        errorLabel = AddLabel(hwnd, L"Config reload failed", labelX, y, 180, kSectionHeight, boldFont);
        y += kSectionHeight + kRowGap;
        errorValue = AddControl(hwnd, L"EDIT", L"", ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL,
                                WS_EX_CLIENTEDGE, 0, labelX, y, rightEdge - labelX, kErrorHeight, font);
        messageClientHeight = y + kErrorHeight + kPadding;
    }

    void resizeToClientHeight(int clientHeight)
    {
        RECT clientRect{};
        GetClientRect(hwnd, &clientRect);
        if (clientRect.bottom == clientHeight)
        {
            return;
        }

        RECT windowRect{};
        GetWindowRect(hwnd, &windowRect);

        RECT targetRect{0, 0, clientRect.right, clientHeight};
        const auto style = static_cast<DWORD>(GetWindowLongPtrW(hwnd, GWL_STYLE));
        const auto exStyle = static_cast<DWORD>(GetWindowLongPtrW(hwnd, GWL_EXSTYLE));
        AdjustWindowRectEx(&targetRect, style, FALSE, exStyle);

        SetWindowPos(hwnd, nullptr, 0, 0, targetRect.right - targetRect.left, targetRect.bottom - targetRect.top,
                     SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    }

    void updateMessageVisibility(bool visible)
    {
        if (messageControlsVisible != visible)
        {
            ShowWindow(errorLabel, visible ? SW_SHOW : SW_HIDE);
            ShowWindow(errorValue, visible ? SW_SHOW : SW_HIDE);
            messageControlsVisible = visible;
        }
        resizeToClientHeight(visible ? messageClientHeight : normalClientHeight);
    }

    void refresh()
    {
        if (!controller)
        {
            return;
        }

        const ServerControllerStatus status = controller->status();
        endpointText = EndpointText(status);
        configPathText = status.loadedConfig.loadedFromFile ? WideFromPath(status.loadedConfig.sourcePath) : L"(none)";
        logPathText = WideFromPath(status.logPath);

        SetText(startStopButton, status.running ? L"Stop" : L"Start");
        SetText(endpointValue, endpointText);

        SetText(loadedPathValue, configPathText);

        const bool hasPendingConfig = ActiveConfigDiffers(status);
        SetText(instanceValue, WideFromUtf8(status.instanceId));
        SetText(logValue, logPathText);

        EnableWindow(openConfigButton,
                     status.loadedConfig.loadedFromFile && !status.loadedConfig.sourcePath.empty() ? TRUE : FALSE);
        EnableWindow(openLogButton, status.logPath.empty() ? FALSE : TRUE);

        const bool hasMessage = !configError.empty() || hasPendingConfig;
        updateMessageVisibility(hasMessage);
        if (!configError.empty())
        {
            SetText(errorLabel, L"Config reload failed");
            SetText(errorValue, WideFromUtf8(configError));
        }
        else if (hasPendingConfig)
        {
            SetText(errorLabel, L"Config changes pending");
            SetText(errorValue, L"Loaded config differs from the running server. Restart to apply.");
        }
        else
        {
            SetText(errorValue, L"");
        }

        InvalidateRect(errorLabel, nullptr, TRUE);
    }

    void toggleServer()
    {
        if (!controller)
        {
            return;
        }

        configError.clear();
        if (controller->running())
        {
            controller->stop();
            refresh();
            return;
        }

        if (reloadConfig)
        {
            configError = reloadConfig();
        }
        if (configError.empty())
        {
            try
            {
                controller->start(context);
            }
            catch (const std::exception &ex)
            {
                configError = ex.what();
            }
        }
        refresh();
    }

    void openPath(const std::wstring &path)
    {
        if (path.empty() || path == L"(none)")
        {
            return;
        }
        ShellExecuteW(hwnd, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    }

    void handleCommand(WPARAM wparam)
    {
        switch (LOWORD(wparam))
        {
        case kStartStopButtonId:
            toggleServer();
            break;
        case kOpenConfigButtonId:
            openPath(configPathText);
            break;
        case kOpenLogButtonId:
            openPath(logPathText);
            break;
        default:
            break;
        }
    }

    LRESULT handleMessage(UINT message, WPARAM wparam, LPARAM lparam)
    {
        switch (message)
        {
        case WM_CREATE:
            createControls();
            SetTimer(hwnd, kRefreshTimerId, kRefreshIntervalMs, nullptr);
            refresh();
            return 0;
        case WM_TIMER:
            if (wparam == kRefreshTimerId)
            {
                refresh();
                return 0;
            }
            break;
        case WM_COMMAND:
            handleCommand(wparam);
            return 0;
        case WM_CTLCOLORSTATIC:
            if (reinterpret_cast<HWND>(lparam) == errorLabel)
            {
                SetTextColor(reinterpret_cast<HDC>(wparam), RGB(165, 70, 35));
                SetBkColor(reinterpret_cast<HDC>(wparam), RGB(248, 248, 248));
                return reinterpret_cast<LRESULT>(backgroundBrush);
            }
            SetBkColor(reinterpret_cast<HDC>(wparam), RGB(248, 248, 248));
            return reinterpret_cast<LRESULT>(backgroundBrush);
        case WM_ERASEBKGND: {
            RECT rect{};
            GetClientRect(hwnd, &rect);
            FillRect(reinterpret_cast<HDC>(wparam), &rect, backgroundBrush);
            return 1;
        }
        case WM_CLOSE:
            DestroyWindow(hwnd);
            return 0;
        case WM_DESTROY:
            KillTimer(hwnd, kRefreshTimerId);
            hwnd = nullptr;
            return 0;
        default:
            break;
        }
        return DefWindowProcW(hwnd, message, wparam, lparam);
    }

    static void EnsureWindowClass()
    {
        static bool registered = false;
        if (registered)
        {
            return;
        }

        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.lpfnWndProc = WindowProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
        wc.lpszClassName = kDialogClassName;
        RegisterClassExW(&wc);
        registered = true;
    }

    static LRESULT CALLBACK WindowProc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam)
    {
        ServerStatusWindow *window = nullptr;
        if (message == WM_NCCREATE)
        {
            auto *create = reinterpret_cast<CREATESTRUCTW *>(lparam);
            window = static_cast<ServerStatusWindow *>(create->lpCreateParams);
            window->hwnd = hwnd;
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(window));
        }
        else
        {
            window = reinterpret_cast<ServerStatusWindow *>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
        }

        if (window)
        {
            return window->handleMessage(message, wparam, lparam);
        }
        return DefWindowProcW(hwnd, message, wparam, lparam);
    }
};
#endif
} // namespace

void ShowServerStatusDialog(IMargretePluginContext *context, ServerController &controller, std::string configError,
                            ReloadServerConfigFn reloadConfig)
{
#if defined(_WIN32)
    INITCOMMONCONTROLSEX commonControls{};
    commonControls.dwSize = sizeof(commonControls);
    commonControls.dwICC = ICC_STANDARD_CLASSES;
    InitCommonControlsEx(&commonControls);

    ServerStatusWindow window(context, controller, std::move(configError), std::move(reloadConfig));
    window.showModal();
#else
    (void)context;
    (void)controller;
    (void)configError;
    (void)reloadConfig;
#endif
}
