#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <algorithm>

#include "libslic3r/GCode/GCodeProcessor.hpp"
#include "libslic3r/GCodeReader.hpp"
#include "libslic3r/Extruder.hpp"
#include "libslic3r/ProjectTask.hpp"

namespace py = pybind11;
using namespace Slic3r;

void init_gcode_bind(py::module &m) {
    auto gcode_mod = m.def_submodule("gcode", "GCode analysis and estimation");

    // ── Results and statistics types ─────────────────────────────────────

    py::class_<GCodeProcessorResult::SliceWarning>(gcode_mod, "SliceWarning")
        .def_readonly("level", &GCodeProcessorResult::SliceWarning::level)
        .def_readonly("msg", &GCodeProcessorResult::SliceWarning::msg)
        .def_readonly("error_code", &GCodeProcessorResult::SliceWarning::error_code)
        .def_readonly("params", &GCodeProcessorResult::SliceWarning::params);

    py::class_<PrintEstimatedStatistics::Mode>(gcode_mod, "EstimatedTimeMode")
        .def_readonly("time", &PrintEstimatedStatistics::Mode::time)
        .def_readonly("prepare_time", &PrintEstimatedStatistics::Mode::prepare_time)
        .def_readonly("layers_times", &PrintEstimatedStatistics::Mode::layers_times)
        .def_readonly("moves_times", &PrintEstimatedStatistics::Mode::moves_times)
        .def_readonly("roles_times", &PrintEstimatedStatistics::Mode::roles_times);

    py::enum_<PrintEstimatedStatistics::ETimeMode>(gcode_mod, "ETimeMode")
        .value("NORMAL", PrintEstimatedStatistics::ETimeMode::Normal)
        .value("STEALTH", PrintEstimatedStatistics::ETimeMode::Stealth)
        .export_values();

    py::class_<PrintEstimatedStatistics>(gcode_mod, "PrintEstimatedStatistics")
        .def_readonly("total_volumes_per_extruder", &PrintEstimatedStatistics::total_volumes_per_extruder)
        .def_readonly("model_volumes_per_extruder", &PrintEstimatedStatistics::model_volumes_per_extruder)
        .def_readonly("support_volumes_per_extruder", &PrintEstimatedStatistics::support_volumes_per_extruder)
        .def_readonly("wipe_tower_volumes_per_extruder", &PrintEstimatedStatistics::wipe_tower_volumes_per_extruder)
        .def_readonly("flush_per_filament", &PrintEstimatedStatistics::flush_per_filament)
        .def("time_by_mode", [](PrintEstimatedStatistics &self, PrintEstimatedStatistics::ETimeMode mode) -> float {
            return self.modes[static_cast<size_t>(mode)].time;
        })
        .def("prepare_time_by_mode", [](PrintEstimatedStatistics &self, PrintEstimatedStatistics::ETimeMode mode) -> float {
            return self.modes[static_cast<size_t>(mode)].prepare_time;
        })
        .def("model_time_by_mode", [](PrintEstimatedStatistics &self, PrintEstimatedStatistics::ETimeMode mode) -> float {
            const auto &mode_stats = self.modes[static_cast<size_t>(mode)];
            return std::max(0.0f, mode_stats.time - mode_stats.prepare_time);
        })
        .def("modes", [](PrintEstimatedStatistics &self) -> std::vector<float> {
            std::vector<float> times;
            for (const auto &mode : self.modes)
                times.push_back(mode.time);
            return times;
        });

    py::class_<GCodeProcessorResult>(gcode_mod, "GCodeProcessorResult")
        .def_readonly("print_statistics", &GCodeProcessorResult::print_statistics)
        .def_readonly("warnings", &GCodeProcessorResult::warnings)
        .def("total_print_time", [](GCodeProcessorResult &self) -> float {
            return self.print_statistics.modes[0].time;
        }, "Estimated total print time in seconds (Normal mode)")
        .def("model_print_time", [](GCodeProcessorResult &self) -> float {
            const auto &mode_stats = self.print_statistics.modes[0];
            return std::max(0.0f, mode_stats.time - mode_stats.prepare_time);
        }, "Estimated model print time in seconds, excluding Bambu prepare time (Normal mode)");

    // ── GCodeProcessor ──────────────────────────────────────────────────
    py::class_<GCodeProcessor>(gcode_mod, "GCodeProcessor")
        .def(py::init<>())
        .def("process", [](GCodeProcessor &self, const std::string &gcode_str) {
            self.initialize("");
            self.process_buffer(gcode_str);
            self.finalize(true);
        }, "Process G-code string, extracting time and filament estimates.")
        .def("process_file", [](GCodeProcessor &self, const std::string &gcode_path) {
            self.process_file(gcode_path);
        }, "Process a G-code file, extracting time and filament estimates.")
        .def("get_result", [](GCodeProcessor &self) -> const GCodeProcessorResult& {
            return self.get_result();
        }, py::return_value_policy::reference);

    // ── Free function: extract time/filament from existing GCode text ────
    gcode_mod.def("estimate_from_gcode", [](const std::string &gcode_text) -> PrintEstimatedStatistics {
        GCodeProcessor processor;
        processor.initialize("");
        processor.process_buffer(gcode_text);
        processor.finalize(true);
        return processor.get_result().print_statistics;
    }, "Parse existing GCode text and extract print time and filament estimates");

}
