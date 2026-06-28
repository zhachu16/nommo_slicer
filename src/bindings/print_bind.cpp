#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <algorithm>

#include "libslic3r/Print.hpp"
#include "libslic3r/PrintBase.hpp"
#include "libslic3r/Slicing.hpp"
#include "libslic3r/GCode/GCodeProcessor.hpp"
#include "libslic3r/GCode/ToolOrdering.hpp"
#include "libslic3r/GCode/WipeTower.hpp"
#include "libslic3r/Layer.hpp"
#include "libslic3r/Model.hpp"
#include "libslic3r/PresetBundle.hpp"

namespace py = pybind11;
using namespace Slic3r;



void init_print_bind(py::module &m) {
    auto print_mod = m.def_submodule("print", "Slicing pipeline");

    // ── PrintStep / ObjectStep enums ─────────────────────────────────────
    py::enum_<PrintStep>(print_mod, "PrintStep")
        .value("WIPE_TOWER", psWipeTower)
        .value("SKIRT_BRIM", psSkirtBrim)
        .value("GCODE_EXPORT", psGCodeExport)
        .value("CONFLICT_CHECK", psConflictCheck)
        .export_values();

    py::enum_<PrintObjectStep>(print_mod, "ObjectStep")
        .value("SLICE", posSlice)
        .value("PERIMETERS", posPerimeters)
        .value("PREPARE_INFILL", posPrepareInfill)
        .value("INFILL", posInfill)
        .value("IRONING", posIroning)
        .value("SUPPORT_MATERIAL", posSupportMaterial)
        .value("DETECT_OVERHANGS", posDetectOverhangsForLift)
        .export_values();

    // ── SlicingParameters ────────────────────────────────────────────────
    py::class_<SlicingParameters>(print_mod, "SlicingParameters")
        .def_readonly("valid", &SlicingParameters::valid)
        .def_readonly("layer_height", &SlicingParameters::layer_height)
        .def_readonly("first_print_layer_height", &SlicingParameters::first_print_layer_height)
        .def_readonly("first_object_layer_height", &SlicingParameters::first_object_layer_height)
        .def_readonly("min_layer_height", &SlicingParameters::min_layer_height)
        .def_readonly("max_layer_height", &SlicingParameters::max_layer_height);

    // ── PrintStatistics ──────────────────────────────────────────────────
    py::class_<PrintStatistics>(print_mod, "PrintStatistics")
        .def_readonly("estimated_normal_print_time", &PrintStatistics::estimated_normal_print_time)
        .def_readonly("estimated_silent_print_time", &PrintStatistics::estimated_silent_print_time)
        .def_readonly("total_used_filament", &PrintStatistics::total_used_filament)
        .def_readonly("total_extruded_volume", &PrintStatistics::total_extruded_volume)
        .def_readonly("total_cost", &PrintStatistics::total_cost)
        .def_readonly("total_weight", &PrintStatistics::total_weight)
        .def_readonly("total_toolchanges", &PrintStatistics::total_toolchanges);

    // ── Print ────────────────────────────────────────────────────────────
    py::class_<Print>(print_mod, "Print")
        .def(py::init<>())
        .def("apply", [](Print &self, const Model &model, PresetBundle &bundle) {
            DynamicPrintConfig full_config = bundle.full_config();
            self.apply(model, full_config);
        }, "Apply model and full config to the print job")
        .def("apply_config", [](Print &self, const Model &model, DynamicPrintConfig &config) {
            self.apply(model, config);
        }, "Apply model and an explicit print config to the print job")
        .def("set_bbl_printer", &Print::set_BBL_Printer, "Mark this print job as targeting a Bambu Lab printer")
        .def("is_bbl_printer", &Print::is_BBL_Printer, "Return whether this print job targets a Bambu Lab printer")
        .def("set_plate_index", [](Print &self, int idx) { self.set_plate_index(idx); }, "Set the active plate index for wipe tower and GCode positioning")
        .def("set_plate_origin", [](Print &self, double x, double y, double z) {
            self.set_plate_origin(Vec3d(x, y, z));
        }, "Set the plate origin (shifts coordinates from global 3MF space to plate-local space)")
        .def("get_plate_origin", [](Print &self) {
            Vec3d o = self.get_plate_origin();
            return py::make_tuple(o.x(), o.y(), o.z());
        }, "Get the plate origin")
        .def("process", [](Print &self) {
            self.process();
        }, "Run the full slicing pipeline")
        .def("export_gcode", [](Print &self, const std::string &path_template) {
            GCodeProcessorResult result;
            return self.export_gcode(path_template, &result);
        }, "Export G-code and update print statistics")
        .def("export_gcode_estimates", [](Print &self, const std::string &path_template) {
            GCodeProcessorResult result;
            std::string output_path = self.export_gcode(path_template, &result);
            const auto &mode_stats = result.print_statistics.modes[static_cast<size_t>(PrintEstimatedStatistics::ETimeMode::Normal)];

            py::dict estimates;
            estimates["output_path"] = output_path;
            estimates["total_time_seconds"] = mode_stats.time;
            estimates["prepare_time_seconds"] = mode_stats.prepare_time;
            estimates["model_time_seconds"] = std::max(0.0f, mode_stats.time - mode_stats.prepare_time);
            return estimates;
        }, "Export G-code and return processed time estimates")
        .def("is_step_done", [](Print &self, PrintStep step) { return self.is_step_done(step); },
            "Check if a print step has been completed")

        // Object-level step access
        .def("objects", [](Print &self) -> std::vector<PrintObject*> {
            std::vector<PrintObject*> objs;
            for (auto *o : self.objects()) objs.push_back(o);
            return objs;
        }, py::return_value_policy::reference)

        // Results
        .def("print_statistics", [](Print &self) -> const PrintStatistics& {
            return self.print_statistics();
        }, py::return_value_policy::reference)

        // Validation
        .def("validate", [](Print &self) -> std::string {
            auto w = self.validate(nullptr);
            return w.string;
        }, "Validate the print configuration. Returns an error string (empty if valid).")

        .def("__repr__", [](const Print &self) {
            return "<Print objects=" + std::to_string(self.objects().size()) + ">";
        });

    // ── PrintObject ──────────────────────────────────────────────────────
    py::class_<PrintObject, std::unique_ptr<PrintObject, py::nodelete>>(print_mod, "PrintObject")
        .def("model_object", [](PrintObject &self) -> ModelObject* { return self.model_object(); }, py::return_value_policy::reference)
        .def("layers", [](PrintObject &self) -> std::vector<Layer*> {
            std::vector<Layer*> layers;
            for (auto *l : self.layers()) layers.push_back(l);
            return layers;
        }, py::return_value_policy::reference)
        .def("slicing_parameters", [](PrintObject &self) -> const SlicingParameters& { return self.slicing_parameters(); }, py::return_value_policy::reference)
        .def("layer_count", &PrintObject::layer_count);

    // ── Layer ────────────────────────────────────────────────────────────
    py::class_<Layer, std::unique_ptr<Layer, py::nodelete>>(print_mod, "Layer")
        .def("id", &Layer::id)
        .def_readonly("print_z", &Layer::print_z)
        .def_readonly("height", &Layer::height)
        .def("bottom_z", &Layer::bottom_z)
        .def_readonly("slice_z", &Layer::slice_z);
}
