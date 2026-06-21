#include "libslic3r/NSVGUtils.hpp"

// read_from_disk is used by Format/bbs_3mf.cpp for loading SVG files from disk.
// NSVGUtils.cpp is excluded from build (depends on nanosvg).
// Return nullptr to indicate SVG file not available.

std::unique_ptr<std::string> Slic3r::read_from_disk(const std::string & /*path*/)
{
    return nullptr;
}
