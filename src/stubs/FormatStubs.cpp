#include <string>
#include <memory>
#include <utility>
#include "libslic3r/TriangleMesh.hpp"
#include "libslic3r/Model.hpp"
#include "libslic3r/PrintConfig.hpp"
#include "libslic3r/Format/AMF.hpp"
#include "libslic3r/Format/OBJ.hpp"
#include "libslic3r/Format/AssimpImport.hpp"
#include "libslic3r/Format/ModelIO.hpp"
#include "libslic3r/SLA/IndexedMesh.hpp"
#include "libslic3r/Interlocking/InterlockingGenerator.hpp"

// Stubs for excluded modules: Format/AMF, Format/OBJ, Format/Assimp, SLA/IndexedMesh, Interlocking

// Format/AMF.cpp
bool Slic3r::load_amf(
    const char * /*path*/,
    DynamicPrintConfig * /*config*/,
    ConfigSubstitutionContext * /*config_substitutions*/,
    Model * /*model*/,
    bool * /*use_inches*/)
{
    return false;
}

// Format/OBJ.cpp — overload 1: TriangleMesh variant
bool Slic3r::load_obj(
    const char * /*path*/,
    TriangleMesh * /*mesh*/,
    ObjInfo & /*vertex_colors*/,
    std::string & /*message*/,
    bool /*gamma_correct*/,
    ObjParser::MtlData * /*out_mtl*/)
{
    return false;
}

// Format/OBJ.cpp — overload 2: Model variant
bool Slic3r::load_obj(
    const char * /*path*/,
    Model * /*model*/,
    ObjInfo & /*vertex_colors*/,
    std::string & /*message*/,
    const char * /*object_name*/,
    bool /*gamma_correct*/,
    ObjParser::MtlData * /*out_mtl*/)
{
    return false;
}

// Format/Assimp.cpp
bool Slic3r::load_assimp_textured_model(
    const std::string & /*path*/,
    TexturedMesh & /*out*/,
    std::string * /*error_message*/)
{
    return false;
}

// obj_to_textured_mesh — declared in OBJ.hpp, defined in Format/OBJ.cpp (excluded)
bool Slic3r::obj_to_textured_mesh(
    const ObjInfo & /*obj_info*/,
    const indexed_triangle_set & /*its*/,
    const ObjParser::MtlData & /*mtl_data*/,
    const std::string & /*obj_directory*/,
    TexturedMesh & /*out*/)
{
    return false;
}

// Format/ModelIO.cpp
std::string Slic3r::make_temp_stl_with_modelio(const std::string & /*input_file*/)
{
    return {};
}

void Slic3r::delete_temp_file(const std::string & /*temp_file*/)
{
}

// SLA/IndexedMesh — dummy AABBImpl for unique_ptr destructor
namespace Slic3r::sla { class IndexedMesh::AABBImpl {}; }

Slic3r::sla::IndexedMesh::~IndexedMesh() = default;
Slic3r::sla::IndexedMesh::IndexedMesh(const indexed_triangle_set & /*tmesh*/, bool /*calculate_epsilon*/) : m_tm(nullptr) {}
Slic3r::sla::IndexedMesh::IndexedMesh(const TriangleMesh & /*mesh*/, bool /*calculate_epsilon*/) : m_tm(nullptr) {}


Slic3r::sla::IndexedMesh::hit_result Slic3r::sla::IndexedMesh::query_ray_hit(
    const Vec3d & /*s*/, const Vec3d & /*dir*/) const
{
    return hit_result{*this};
}

// InterlockingGenerator
void Slic3r::InterlockingGenerator::generate_embedding_wall(PrintObject * /*print_object*/) {}
void Slic3r::InterlockingGenerator::generate_interlocking_structure(PrintObject * /*print_object*/) {}


