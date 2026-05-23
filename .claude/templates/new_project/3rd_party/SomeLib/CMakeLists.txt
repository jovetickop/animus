# ============================================================
# SomeLib 三方库导入目标
# TODO: 将 SomeLib 替换为实际库名
# ============================================================

add_library(SomeLib SHARED IMPORTED GLOBAL)

set(_SOMELIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

set_target_properties(SomeLib PROPERTIES
    IMPORTED_IMPLIB_DEBUG "${_SOMELIB_DIR}/lib/SomeLibd.lib"
    IMPORTED_IMPLIB_RELEASE "${_SOMELIB_DIR}/lib/SomeLib.lib"
    IMPORTED_LOCATION_DEBUG "${_SOMELIB_DIR}/bin/SomeLibd.dll"
    IMPORTED_LOCATION_RELEASE "${_SOMELIB_DIR}/bin/SomeLib.dll"
    INTERFACE_INCLUDE_DIRECTORIES "${_SOMELIB_DIR}/include"
)
