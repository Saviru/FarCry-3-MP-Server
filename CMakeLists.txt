cmake_minimum_required(VERSION 3.10)
project(FC3Multiplayer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Define WIN32_LEAN_AND_MEAN to avoid Windows.h including winsock.h
add_definitions(-DWIN32_LEAN_AND_MEAN)

# Path to Detours - UPDATE THIS PATH to point to your Detours installation
set(DETOURS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/Detours")
message(STATUS "Looking for Detours in: ${DETOURS_DIR}")

# Check if X64 library exists, otherwise fall back to X86
if(EXISTS "${DETOURS_DIR}/lib.X64/detours.lib")
    set(DETOURS_LIB_PATH "${DETOURS_DIR}/lib.X64/detours.lib")
    message(STATUS "Using 64-bit Detours library")
elseif(EXISTS "${DETOURS_DIR}/lib.X86/detours.lib")
    set(DETOURS_LIB_PATH "${DETOURS_DIR}/lib.X86/detours.lib")
    message(STATUS "Using 32-bit Detours library")
else()
    # If neither exists, we need to copy the prebuilt one
    message(STATUS "Detours library not found, will use static linking")
    set(DETOURS_LIB_PATH "")
endif()

# Include directories
include_directories("${DETOURS_DIR}/include")

# Add source files
add_library(fc3_multiplayer SHARED fc3_multiplayer.cpp)

# Link libraries - conditionally include Detours
target_link_libraries(fc3_multiplayer ws2_32.lib)

if(NOT "${DETOURS_LIB_PATH}" STREQUAL "")
    target_link_libraries(fc3_multiplayer "${DETOURS_LIB_PATH}")
else()
    # Handle the case where Detours library is not found
    message(WARNING "Detours library not found - functionality will be limited")
endif()