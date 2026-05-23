#[[
FindVLD.cmake - 查找 Visual Leak Detector

Visual Leak Detector (VLD) 是一个免费的内存泄漏检测工具。

下载地址:
- https://github.com/KindDragon/vld/releases

导出变量:
  VLD_FOUND
  VLD_INCLUDE_DIR
  VLD_LIBRARY

导出目标:
  VLD::VLD
]]

if(NOT WIN32 OR NOT MSVC)
    set(VLD_FOUND FALSE)
    return()
endif()

set(VLD_SEARCH_PATHS
    "$ENV{VLD_ROOT}"
    "$ENV{PROGRAMFILES}/Visual Leak Detector"
    "$ENV{PROGRAMFILES\(X86\)}/Visual Leak Detector"
    "C:/Program Files/Visual Leak Detector"
    "C:/Program Files (x86)/Visual Leak Detector"
)

find_path(VLD_INCLUDE_DIR
    NAMES vld.h
    PATHS ${VLD_SEARCH_PATHS}
    PATH_SUFFIXES include
)

if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(VLD_LIB_SUFFIX "Win64")
else()
    set(VLD_LIB_SUFFIX "Win32")
endif()

find_library(VLD_LIBRARY
    NAMES vld
    PATHS ${VLD_SEARCH_PATHS}
    PATH_SUFFIXES "lib/${VLD_LIB_SUFFIX}"
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(VLD REQUIRED_VARS VLD_LIBRARY VLD_INCLUDE_DIR)

if(VLD_FOUND AND NOT TARGET VLD::VLD)
    add_library(VLD::VLD UNKNOWN IMPORTED)
    set_target_properties(VLD::VLD PROPERTIES
        IMPORTED_LOCATION "${VLD_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${VLD_INCLUDE_DIR}"
    )
endif()

mark_as_advanced(VLD_INCLUDE_DIR VLD_LIBRARY)
