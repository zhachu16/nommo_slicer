// FuzzySkin.hpp uses Points, Polygon, coordf_t, PrintRegionConfig, PerimeterRegions
// but is missing the necessary includes. Satisfy them here before including the header.
#include <cstddef>
#include "libslic3r/Point.hpp"
#include "libslic3r/Polygon.hpp"
#include "libslic3r/PrintConfig.hpp"
#include "libslic3r/PerimeterGenerator.hpp"
#include "libslic3r/Arachne/utils/ExtrusionLine.hpp"
#include "libslic3r/FuzzySkin.hpp"

// Stub implementations for FuzzySkin.
// Full FuzzySkin.cpp is excluded (it needs libnoise). Referenced by PerimeterGenerator.cpp for the
// fuzzy skin perimeter feature. The stubs must be the identity: PerimeterGenerator replaces every
// perimeter with the return value, so anything else changes or drops walls. With fuzzy skin
// enabled in a project, walls are therefore printed smooth (the Python layer warns about this).

namespace Slic3r {

Polygon apply_fuzzy_skin(
    const Polygon &polygon,
    const PrintRegionConfig & /*base_config*/,
    const PerimeterRegions & /*perimeter_regions*/,
    size_t /*layer_idx*/,
    size_t /*perimeter_idx*/,
    bool /*is_contour*/,
    coordf_t /*slice_z*/)
{
    return polygon;
}

Arachne::ExtrusionLine apply_fuzzy_skin(
    const Arachne::ExtrusionLine &extrusion,
    const PrintRegionConfig & /*base_config*/,
    const PerimeterRegions & /*perimeter_regions*/,
    size_t /*layer_idx*/,
    size_t /*perimeter_idx*/,
    bool /*is_contour*/,
    coordf_t /*slice_z*/)
{
    // Returning an empty line here used to drop every Arachne wall from the G-code.
    return extrusion;
}

} // namespace Slic3r
