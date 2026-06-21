#include "libslic3r/MeshBoolean.hpp"

// Stub implementations for MeshBoolean functions referenced by Model.cpp.
// The full MeshBoolean.cpp is excluded (depends on mcut and heavy CGAL),
// but Model.cpp calls these functions for cut/segment/merge features
// that are not needed in the MVP.

namespace Slic3r {
namespace MeshBoolean {

namespace cgal {

std::vector<TriangleMesh> segment(const TriangleMesh& /*src*/, double /*smoothing_alpha*/, int /*segment_number*/)
{
    return {};
}

TriangleMesh merge(std::vector<TriangleMesh> /*meshes*/)
{
    return {};
}

} // namespace cgal

namespace mcut {

void make_boolean(
    const TriangleMesh &/*src_mesh*/,
    const TriangleMesh &/*cut_mesh*/,
    std::vector<TriangleMesh> &/*dst_mesh*/,
    const std::string &/*boolean_opts*/,
    const BooleanCancelCB &/*cancel_cb*/,
    const BooleanProgressCB &/*progress_cb*/,
    const BooleanFailedCB &/*failed_cb*/)
{
}

} // namespace mcut

} // namespace MeshBoolean
} // namespace Slic3r
