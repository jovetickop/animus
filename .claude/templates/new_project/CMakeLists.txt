cmake_minimum_required(VERSION 3.21)
project(<PROJECT_NAME> LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/install" CACHE PATH "Default install path" FORCE)
endif()

option(BUILD_TESTS "Build smoke tests" ON)
option(USE_QT6 "Use Qt6 instead of Qt5" OFF)
option(ENABLE_VLD "Enable Visual Leak Detector on Windows/MSVC" OFF)
set(QT_EXTRA_MODULES "" CACHE STRING "Extra Qt modules separated by ';' (for example: OpenGL;OpenGLWidgets;Network;Sql)")

# ------------------------------------------------------------------
# Toolchain / compile options
# ------------------------------------------------------------------
if(MSVC)
    add_compile_options(/MP /W4 /wd4127 /wd4251 /utf-8)
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /MD")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} /MDd")
endif()

# ------------------------------------------------------------------
# Qt import (import first, then each target consumes modules)
# ------------------------------------------------------------------
set(QT_REQUIRED_COMPONENTS Core Gui Widgets)
if(QT_EXTRA_MODULES)
    list(APPEND QT_REQUIRED_COMPONENTS ${QT_EXTRA_MODULES})
endif()
if(BUILD_TESTS)
    list(APPEND QT_REQUIRED_COMPONENTS Test)
endif()
list(REMOVE_DUPLICATES QT_REQUIRED_COMPONENTS)

if(USE_QT6)
    find_package(Qt6 REQUIRED COMPONENTS ${QT_REQUIRED_COMPONENTS})
    set(QT_PACKAGE Qt6)
else()
    find_package(Qt5 REQUIRED COMPONENTS ${QT_REQUIRED_COMPONENTS})
    set(QT_PACKAGE Qt5)
endif()

function(set_template_use_qt_modules target)
    set(options)
    set(oneValueArgs)
    set(multiValueArgs COMPONENTS)
    cmake_parse_arguments(UQT "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    foreach(comp IN LISTS UQT_COMPONENTS)
        if(USE_QT6)
            if(NOT TARGET Qt6::${comp})
                message(FATAL_ERROR "Qt6::${comp} is not available. Check QT_EXTRA_MODULES or Qt installation.")
            endif()
            target_link_libraries(${target} PRIVATE Qt6::${comp})
        else()
            if(NOT TARGET Qt5::${comp})
                message(FATAL_ERROR "Qt5::${comp} is not available. Check QT_EXTRA_MODULES or Qt installation.")
            endif()
            target_link_libraries(${target} PRIVATE Qt5::${comp})
        endif()
    endforeach()
endfunction()

function(set_template_output_directories target)
    set_target_properties(${target} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/bin/Debug"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/bin/Release"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/bin"
        ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/lib"
    )
endfunction()

function(copy_qt_runtime_to_target target)
    if(NOT WIN32 OR NOT MSVC)
        return()
    endif()

    if(USE_QT6)
        set(_qt_prefix Qt6)
        set(_platform_plugin_debug qwindowsd.dll)
        set(_platform_plugin_release qwindows.dll)
    else()
        set(_qt_prefix Qt5)
        set(_platform_plugin_debug qwindowsd.dll)
        set(_platform_plugin_release qwindows.dll)
    endif()

    get_target_property(_qmake_executable ${_qt_prefix}::qmake IMPORTED_LOCATION)
    if(NOT _qmake_executable)
        message(WARNING "Cannot find ${_qt_prefix}::qmake. Skip Qt runtime copy for ${target}.")
        return()
    endif()

    get_filename_component(_qt_bin_dir "${_qmake_executable}" DIRECTORY)
    get_filename_component(_qt_install_prefix "${_qt_bin_dir}" DIRECTORY)
    set(_qt_plugins_dir "${_qt_install_prefix}/plugins")

    set(_qt_runtime_targets
        ${_qt_prefix}::Core
        ${_qt_prefix}::Gui
        ${_qt_prefix}::Widgets
    )
    if(TARGET ${_qt_prefix}::OpenGL)
        list(APPEND _qt_runtime_targets ${_qt_prefix}::OpenGL)
    endif()
    if(TARGET ${_qt_prefix}::OpenGLWidgets)
        list(APPEND _qt_runtime_targets ${_qt_prefix}::OpenGLWidgets)
    endif()
    if(TARGET ${_qt_prefix}::Test)
        list(APPEND _qt_runtime_targets ${_qt_prefix}::Test)
    endif()

    foreach(_qt_target IN LISTS _qt_runtime_targets)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "$<TARGET_FILE:${_qt_target}>"
                "$<TARGET_FILE_DIR:${target}>"
        )
    endforeach()

    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory
            "$<TARGET_FILE_DIR:${target}>/platforms"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_qt_plugins_dir}/platforms/$<IF:$<CONFIG:Debug>,${_platform_plugin_debug},${_platform_plugin_release}>"
            "$<TARGET_FILE_DIR:${target}>/platforms/"
        COMMENT "Copy Qt runtime DLLs and platforms plugin for ${target}"
    )
endfunction()

if(ENABLE_VLD AND WIN32 AND MSVC)
    find_package(VLD QUIET)
endif()

# Optional extension points
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/3rd_party/CMakeLists.txt")
    add_subdirectory(3rd_party)
endif()

set(APP_SOURCES
    src/main.cpp
    src/mainwindow.cpp
    src/mainwindow.h
    ui/mainwindow.ui
    resources/resources.qrc
)

add_executable(<PROJECT_NAME> ${APP_SOURCES})
target_include_directories(<PROJECT_NAME>
    PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
)
set_template_use_qt_modules(<PROJECT_NAME> COMPONENTS Core Gui Widgets)
if(TARGET VLD::VLD)
    target_link_libraries(<PROJECT_NAME> PRIVATE VLD::VLD)
endif()
set_template_output_directories(<PROJECT_NAME>)
copy_qt_runtime_to_target(<PROJECT_NAME>)

if(BUILD_TESTS)
    enable_testing()

    add_executable(<PROJECT_NAME>_smoke_test
        tests/test_smoke.cpp
        src/mainwindow.cpp
        src/mainwindow.h
        ui/mainwindow.ui
    )
    target_include_directories(<PROJECT_NAME>_smoke_test
        PRIVATE
            "${CMAKE_CURRENT_SOURCE_DIR}/src"
            "${CMAKE_CURRENT_SOURCE_DIR}/include"
    )
    set_template_use_qt_modules(<PROJECT_NAME>_smoke_test COMPONENTS Core Gui Widgets Test)
    if(TARGET VLD::VLD)
        target_link_libraries(<PROJECT_NAME>_smoke_test PRIVATE VLD::VLD)
    endif()
    set_template_output_directories(<PROJECT_NAME>_smoke_test)
    copy_qt_runtime_to_target(<PROJECT_NAME>_smoke_test)

    add_test(
        NAME T001_MainWindowSmoke
        COMMAND <PROJECT_NAME>_smoke_test
    )
endif()
