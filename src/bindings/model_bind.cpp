#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <boost/filesystem.hpp>

#include "libslic3r/Model.hpp"
#include "libslic3r/Preset.hpp"
#include "libslic3r/Format/bbs_3mf.hpp"
#include "libslic3r/Format/3mf.hpp"
#include "libslic3r/TriangleMesh.hpp"
#include "libslic3r/Point.hpp"
#include "libslic3r/PrintConfig.hpp"
#include "libslic3r/Semver.hpp"

namespace py = pybind11;
using namespace Slic3r;

void init_model_bind(py::module &m) {
    // ── Semver ─────────────────────────────────────────────────────────────
    py::class_<Semver>(m, "Semver")
        .def(py::init<>())
        .def(py::init<const std::string&>())
        .def("maj", &Semver::maj)
        .def("min", &Semver::min)
        .def("patch", &Semver::patch)
        .def("prerelease", &Semver::prerelease)
        .def("metadata", &Semver::metadata)
        .def("to_string", &Semver::to_string)
        .def("valid", &Semver::valid)
        .def("__str__", &Semver::to_string)
        .def("__repr__", [](const Semver &v) { return "Semver(" + v.to_string() + ")"; })
        .def("__eq__", &Semver::operator==);
    // ── TriangleMesh ──────────────────────────────────────────────────────
    py::class_<TriangleMesh>(m, "TriangleMesh")
        .def("volume", &TriangleMesh::volume)
        .def("empty", &TriangleMesh::empty);

    // ── ModelInstance ─────────────────────────────────────────────────────
    py::class_<ModelInstance>(m, "ModelInstance")
        .def("get_offset", [](ModelInstance &self) -> const Vec3d& { return self.get_offset(); }, py::return_value_policy::reference)
        .def("get_rotation", [](ModelInstance &self) -> const Vec3d& { return self.get_rotation(); }, py::return_value_policy::reference)
        .def("get_scaling_factor", [](ModelInstance &self) -> const Vec3d& { return self.get_scaling_factor(); }, py::return_value_policy::reference)
        .def("get_mirror", [](ModelInstance &self) -> const Vec3d& { return self.get_mirror(); }, py::return_value_policy::reference)
        .def("id", &ModelInstance::id);

    // ── ModelVolume ───────────────────────────────────────────────────────
    py::class_<ModelVolume>(m, "ModelVolume")
        .def("mesh", &ModelVolume::mesh, py::return_value_policy::reference)
        .def_readonly("name", &ModelVolume::name)
        .def("is_model_part", &ModelVolume::is_model_part)
        .def("is_modifier", &ModelVolume::is_modifier)
        .def("is_support_blocker", &ModelVolume::is_support_blocker)
        .def("is_support_enforcer", &ModelVolume::is_support_enforcer)
        .def_property_readonly("config", [](ModelVolume &self) -> ModelConfigObject& { return self.config; }, py::return_value_policy::reference)
        .def("id", &ModelVolume::id);

    // ── ModelObject ──────────────────────────────────────────────────────
    py::class_<ModelObject, std::unique_ptr<ModelObject, py::nodelete>>(m, "ModelObject")
        .def_readonly("name", &ModelObject::name)
        .def_readonly("instances", &ModelObject::instances)
        .def_readonly("volumes", &ModelObject::volumes)
        .def("raw_mesh", &ModelObject::raw_mesh)
        .def("get_model", [](ModelObject &self) -> Model* { return self.get_model(); }, py::return_value_policy::reference)
        .def("id", &ModelObject::id);

    // ── PlateData ────────────────────────────────────────────────────────
    py::class_<PlateData>(m, "PlateData")
        .def_readonly("plate_index", &PlateData::plate_index)
        .def_readonly("gcode_prediction", &PlateData::gcode_prediction)
        .def_readonly("gcode_weight", &PlateData::gcode_weight)
        .def_readonly("first_layer_time", &PlateData::first_layer_time)
        .def_readonly("plate_name", &PlateData::plate_name)
        .def_readonly("printer_model_id", &PlateData::printer_model_id)
        .def_readonly("nozzle_diameters", &PlateData::nozzle_diameters)
        .def_readonly("slice_filaments_info", &PlateData::slice_filaments_info)
        .def_readonly("warnings", &PlateData::warnings)
        .def_readonly("locked", &PlateData::locked)
        .def("get_gcode_prediction_str", &PlateData::get_gcode_prediction_str)
        .def("get_gcode_weight_str", &PlateData::get_gcode_weight_str);

    // ── Model ────────────────────────────────────────────────────────────
    py::class_<Model>(m, "Model")
        .def(py::init<>())
        .def("objects", [](Model &self) -> ModelObjectPtrs& { return self.objects; }, py::return_value_policy::reference)
        .def("add_object", [](Model &self) -> ModelObject* { return self.add_object(); }, py::return_value_policy::reference)
        .def("delete_object", [](Model &self, size_t idx) { self.delete_object(idx); })
        .def("clear_objects", &Model::clear_objects)
        .def("get_object", [](Model &self, size_t idx) -> ModelObject* {
            return (idx < self.objects.size()) ? self.objects[idx] : nullptr;
        }, py::return_value_policy::reference)
        .def("object_count", [](Model &self) -> size_t { return self.objects.size(); })
        .def_static("load_bbs_3mf", [](const std::string &path) {
            auto model = std::make_unique<Model>();
            auto config = std::make_unique<DynamicPrintConfig>();
            auto backup_path = boost::filesystem::temp_directory_path() /
                boost::filesystem::unique_path("nommo_3mf_%%%%%%%%%%%%%%%%");
            model->set_backup_path(backup_path.string());
            ConfigSubstitutionContext subst{ForwardCompatibilitySubstitutionRule::Enable};
            PlateDataPtrs plates;
            std::vector<Preset*> project_presets;
            bool is_bbl = false;
            Semver version;

            LoadStrategy strategy = LoadStrategy::LoadModel | LoadStrategy::LoadConfig;
            bool ok = load_bbs_3mf(
                path.c_str(), config.get(), &subst, model.get(),
                &plates, &project_presets, &is_bbl, &version,
                nullptr, strategy
            );

            if (!ok) {
                throw std::runtime_error("Failed to load .3mf file: " + path);
            }

            return std::tuple(
                std::move(model),
                std::move(config),
                std::move(plates),
                project_presets,
                is_bbl,
                version
            );
        }, "Load a Bambu Studio .3mf file. Returns (Model, DynamicPrintConfig, plates, presets, is_bbl, version)")
        .def_static("load_standard_3mf", [](const std::string &path) {
            Model model;
            DynamicPrintConfig config;
            ConfigSubstitutionContext subst{ForwardCompatibilitySubstitutionRule::Enable};
            bool ok = load_3mf(path.c_str(), config, subst, &model, true);
            if (!ok) {
                throw std::runtime_error("Failed to load standard .3mf file: " + path);
            }
            return std::make_tuple(std::move(model), std::move(config));
        }, "Load a standard PrusaSlicer .3mf file. Returns (Model, DynamicPrintConfig)");
}
