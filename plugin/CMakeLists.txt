cmake_minimum_required(VERSION 3.30)

file(STRINGS "config/VERSION" PROJECT_VERSION)
project(margrete_rpc VERSION ${PROJECT_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_definitions(-DUNICODE -D_UNICODE -D_WIN32_WINNT=0x0601)

function(setup_metadata)
    set(REPO_URL "https://github.com/Foahh/margrete-rpc")

    set(TITLE "Margrete RPC" PARENT_SCOPE)
    set(DESC "TCP/protobuf bridge for chart scripting\\n${REPO_URL}" PARENT_SCOPE)
    set(DEVELOPER "Foahh" PARENT_SCOPE)
    set(DLL_NAME "margrete_rpc" PARENT_SCOPE)
endfunction()

function(generate_configurations)
    configure_file(config/margrete-rpc.ini.in ${CMAKE_CURRENT_BINARY_DIR}/margrete-rpc.ini @ONLY)
    configure_file(config/meta.h.in ${CMAKE_CURRENT_BINARY_DIR}/include/meta.h @ONLY)
    configure_file(config/version.rc.in ${CMAKE_CURRENT_BINARY_DIR}/include/version.rc @ONLY)

    message(STATUS "CONFIGURATION_PATH: ${CMAKE_CURRENT_BINARY_DIR}")
endfunction()

setup_metadata()
generate_configurations()

find_package(Protobuf CONFIG REQUIRED)
find_package(Catch2 CONFIG REQUIRED)

set(PROTO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../proto")
set(PROTO_FILE "${PROTO_ROOT}/margrete/rpc/v1/messages.proto")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(GEN_SRC "${GENERATED_DIR}/margrete/rpc/v1/messages.pb.cc")
set(GEN_HDR "${GENERATED_DIR}/margrete/rpc/v1/messages.pb.h")

add_custom_command(
    OUTPUT ${GEN_SRC} ${GEN_HDR}
    COMMAND protobuf::protoc
    ARGS --cpp_out=${GENERATED_DIR} -I${PROTO_ROOT} ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
    VERBATIM
    COMMENT "Generating C++ protobuf sources for margrete.rpc.v1")

set(MARGRETE_SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../MargretePluginSDK")
set(MARGRETE_SDK_INCLUDE "${MARGRETE_SDK_ROOT}/include")
if(NOT EXISTS "${MARGRETE_SDK_INCLUDE}/MargretePlugin.h")
    message(FATAL_ERROR "MargretePluginSDK not found at ${MARGRETE_SDK_ROOT}. Run: git submodule update --init --recursive")
endif()

add_library(MargretePluginSDK INTERFACE)
target_include_directories(MargretePluginSDK INTERFACE "${MARGRETE_SDK_INCLUDE}")

add_library(margrete_rpc SHARED
    src/DLLMain.cpp
    src/Plugin.cpp
    src/Config.cpp
    src/Logger.cpp
    src/FrameProtocol.cpp
    src/MargreteSession.cpp
    src/TransactionApplier.cpp
    src/ChartMapper.cpp
    src/RequestRouter.cpp
    ${GEN_SRC}
    ${CMAKE_CURRENT_BINARY_DIR}/include/version.rc
)

set_target_properties(margrete_rpc PROPERTIES OUTPUT_NAME "${DLL_NAME}")

target_include_directories(margrete_rpc PRIVATE
    src
    "${GENERATED_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}/include"
)
target_link_libraries(margrete_rpc PRIVATE MargretePluginSDK protobuf::libprotobuf ws2_32)

if(MSVC)
    target_compile_options(margrete_rpc PRIVATE /EHsc /utf-8)
endif()

add_executable(plugin_tests
    tests/smoke_tests.cpp
    tests/frame_protocol_tests.cpp
    tests/config_tests.cpp
    tests/transaction_applier_tests.cpp
    tests/request_router_tests.cpp
    src/Config.cpp
    src/Logger.cpp
    src/FrameProtocol.cpp
    src/MargreteSession.cpp
    src/TransactionApplier.cpp
    src/ChartMapper.cpp
    src/RequestRouter.cpp
    ${GEN_SRC}
)

target_include_directories(plugin_tests PRIVATE
    src
    "${CMAKE_CURRENT_LIST_DIR}/tests"
    "${GENERATED_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}/include"
)
target_link_libraries(plugin_tests PRIVATE MargretePluginSDK protobuf::libprotobuf Catch2::Catch2WithMain ws2_32)
