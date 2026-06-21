cmake_minimum_required(VERSION 3.15)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
project(nommo_slicer VERSION 0.1.1 LANGUAGES CXX)

# CMP0167: keep FindBoost module
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 OLD)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS
    Debug Release RelWithDebInfo MinSizeRel
  )
endif()

# ── Project paths ────────────────────────────────────────────────────────────
set(BAMBU_SRC "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(LIBSLIC3R_SRC "${BAMBU_SRC}/libslic3r")

# ── BambuStudio version macros (BBL_RELEASE_TO_PUBLIC, BBL_INTERNAL_TESTING) ─
include("${CMAKE_CURRENT_SOURCE_DIR}/version.inc")

# ── Dependencies (system) ───────────────────────────────────────────────────
find_package(Boost 1.83 REQUIRED COMPONENTS filesystem thread log locale regex chrono atomic date_time iostreams log_setup)
find_package(TBB REQUIRED)
find_package(Eigen3 3.3 QUIET)
find_package(EXPAT QUIET)
find_package(PNG REQUIRED)
find_package(ZLIB REQUIRED)
find_package(Freetype REQUIRED)
find_package(NLopt REQUIRED)
find_package(OpenCV REQUIRED)

# ── pybind11 ────────────────────────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG v2.13.6
)
FetchContent_MakeAvailable(pybind11)

# ── Global includes ──────────────────────────────────────────────────────────
include_directories(BEFORE SYSTEM "${BAMBU_SRC}/eigen")
include_directories("${LIBSLIC3R_SRC}")
include_directories("${BAMBU_SRC}")
include_directories("${BAMBU_SRC}/libigl")
include_directories("${CMAKE_CURRENT_BINARY_DIR}")

# ── Build utilities (encoding_check function) ──────────────────────────────
add_subdirectory("${BAMBU_SRC}/build-utils" build-utils)

# ── Third-party bundled libs (from BambuStudio src/) ───────────────────────
add_subdirectory("${BAMBU_SRC}/admesh" admesh)
# Ensure admesh uses the same Boost ABI tag as the rest of the codebase
target_compile_definitions(admesh PRIVATE BOOST_LOG_DYN_LINK BOOST_LOG_NO_LIB)

# qhull needs LIBDIR for target_include_directories — set it before
set(LIBDIR "${BAMBU_SRC}")
add_subdirectory("${BAMBU_SRC}/boost" boost)
add_subdirectory("${BAMBU_SRC}/clipper" clipper)
add_subdirectory("${BAMBU_SRC}/clipper2" clipper2)
add_subdirectory("${BAMBU_SRC}/miniz" miniz)
add_subdirectory("${BAMBU_SRC}/minilzo" minilzo)
add_subdirectory("${BAMBU_SRC}/glu-libtess" glu-libtess)
add_subdirectory("${BAMBU_SRC}/qhull" qhull)
add_subdirectory("${BAMBU_SRC}/semver" semver)
add_subdirectory("${BAMBU_SRC}/libigl" libigl)
add_subdirectory("${BAMBU_SRC}/libnest2d" libnest2d)

# ── Boost convenience targets ────────────────────────────────────────────────
add_library(boost_headeronly INTERFACE)
if(APPLE)
  target_compile_definitions(boost_headeronly INTERFACE BOOST_ASIO_DISABLE_KQUEUE)
endif()
target_link_libraries(boost_headeronly INTERFACE Boost::boost)

add_library(boost_libs INTERFACE)
target_link_libraries(boost_libs INTERFACE boost_headeronly
  Boost::filesystem Boost::thread Boost::log
  Boost::locale Boost::regex Boost::chrono Boost::atomic
  Boost::date_time Boost::iostreams
  Boost::log_setup)

# ── Collect libslic3r sources (stripped) ────────────────────────────────────
# We start with the full CMake source list from the existing project, minus
# SLA, Interlocking, Shape, TextureToColor, Format/STEP, Format/OBJ, Format/SVG,
# Format/Assimp, Format/SL1, Format/AMF, and CGAL-dependent files.

# Collect all source files from libslic3r recursively, then filter.
file(GLOB_RECURSE ALL_LIBSLIC3R_SOURCES
  CONFIGURE_DEPENDS
  "${LIBSLIC3R_SRC}/*.cpp"
  "${LIBSLIC3R_SRC}/*.hpp"
  "${LIBSLIC3R_SRC}/*.h"
)

# Files/directories to EXCLUDE (stripped subsystems)
set(EXCLUDED_PATTERNS
  "/SLA/"
  "/Interlocking/"
  "/Shape/"
  "/TextureToColor/"
  "/Format/AMF"
  "/Format/OBJ"
  "/Format/STEP"
  "/Format/SVG"
  "/Format/svg"
  "/Format/SL1"
  "/Format/Assimp"
  "/Format/ModelIO"
  "/libslic3r_cgal"
  "CutSurface"
  "FuzzySkin"
  "MeshBoolean"
  "PressureEqualizer"
  "GCode/PostProcessor"
  "GCodeSender"
  "SLAPrint"
  "SLAPrintSteps"
  "Emboss"
  "TextShape"
  "NSVGUtils"
  "nanosvg"
  "LogSink"
  "TryCatchSignalSEH"
)

function(skip_excluded input_list excluded output_list)
  set(result)
  foreach(f ${${input_list}})
    set(skip FALSE)
    foreach(pattern ${${excluded}})
      if(f MATCHES "${pattern}")
        set(skip TRUE)
        break()
      endif()
    endforeach()
    if(NOT skip)
      list(APPEND result "${f}")
    endif()
  endforeach()
  set(${output_list} "${result}" PARENT_SCOPE)
endfunction()

skip_excluded(ALL_LIBSLIC3R_SOURCES EXCLUDED_PATTERNS LIBSLIC3R_SOURCES)

# MeshBoolean stub: Model.cpp references MeshBoolean functions but we don't
# want the full MeshBoolean.cpp dependency chain (mcut, heavy CGAL).
# The stub defines no-op versions of the called functions.
list(APPEND LIBSLIC3R_SOURCES
  "${CMAKE_CURRENT_SOURCE_DIR}/src/stubs/MeshBooleanStub.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/stubs/NSVGUtilsStub.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/stubs/FuzzySkinStub.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/stubs/FormatStubs.cpp"
)

# Also add Mac-specific files
if(APPLE)
  list(APPEND LIBSLIC3R_SOURCES
    "${LIBSLIC3R_SRC}/MacUtils.mm"
  )
endif()

# ── libslic3r target ─────────────────────────────────────────────────────────
add_library(libslic3r STATIC ${LIBSLIC3R_SOURCES})
target_compile_definitions(libslic3r PUBLIC -DUSE_TBB -DTBB_USE_CAPTURED_EXCEPTION=0)
target_include_directories(libslic3r PRIVATE "${LIBSLIC3R_SRC}"
  SYSTEM BEFORE "${BAMBU_SRC}/eigen")
target_include_directories(libslic3r PUBLIC "${CMAKE_CURRENT_BINARY_DIR}")

target_link_libraries(libslic3r
  admesh clipper Clipper2 miniz minilzo glu-libtess qhull semver libigl libnest2d
  boost_libs
  ${PNG_LIBRARIES} ${ZLIB_LIBRARIES} ${EXPAT_LIBRARIES}
  TBB::tbb TBB::tbbmalloc
  ${OpenCV_LIBS}
  ${CMAKE_DL_LIBS}
)

if(NOT WIN32)
  target_link_libraries(libslic3r Freetype::Freetype)
endif()

if(APPLE)
  find_library(FOUNDATION Foundation REQUIRED)
  target_link_libraries(libslic3r ${FOUNDATION})
endif()

# ── CGAL handling ───────────────────────────────────────────────────────────
# Most CGAL-dependent files were excluded, but some geometry files
# (VoronoiUtilsCgal) may still reference CGAL. If CGAL is available, link it.
find_package(CGAL QUIET)
if(CGAL_FOUND)
  message(STATUS "CGAL found: ${CGAL_VERSION}")
  target_include_directories(libslic3r PUBLIC ${CGAL_INCLUDE_DIRS})
  target_link_libraries(libslic3r CGAL::CGAL)
  target_compile_definitions(libslic3r PRIVATE -DNOMNO_CGAL_AVAILABLE)
else()
  message(STATUS "CGAL not found — excluding CGAL-dependent code paths")
  target_compile_definitions(libslic3r PRIVATE -DNOMNO_CGAL_AVAILABLE=0)
endif()

# ── libslic3r_version.h generation ──────────────────────────────────────────
set(SLIC3R_VERSION "0.1.0")
set(SLIC3R_BUILD_TIME "0")
set(SLIC3R_COMMIT_SHA "nommo")
configure_file(
  "${LIBSLIC3R_SRC}/libslic3r_version.h.in"
  "${CMAKE_CURRENT_BINARY_DIR}/libslic3r_version.h"
  @ONLY
)

# ── pybind11 module ─────────────────────────────────────────────────────────
pybind11_add_module(_nommo_native
  src/bindings/module.cpp
  src/bindings/model_bind.cpp
  src/bindings/config_bind.cpp
  src/bindings/preset_bind.cpp
  src/bindings/print_bind.cpp
  src/bindings/gcode_bind.cpp
)

target_include_directories(_nommo_native PRIVATE
  "${LIBSLIC3R_SRC}" "${BAMBU_SRC}"
  SYSTEM BEFORE "${BAMBU_SRC}/eigen"
)

target_link_libraries(_nommo_native PRIVATE libslic3r boost_libs pybind11::module)

set_target_properties(_nommo_native PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/nommo_slicer"
)
