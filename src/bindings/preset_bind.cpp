#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "libslic3r/Preset.hpp"
#include "libslic3r/PresetBundle.hpp"
#include "libslic3r/AppConfig.hpp"

namespace py = pybind11;
using namespace Slic3r;

void init_preset_bind(py::module &m) {
    auto preset_mod = m.def_submodule("preset", "Profile/preset system");

    // ── Preset ────────────────────────────────────────────────────────────
    py::class_<Preset>(preset_mod, "Preset")
        .def_readonly("name", &Preset::name)
        .def_readonly("alias", &Preset::alias)
        .def_readonly("type", &Preset::type)
        .def_readonly("file", &Preset::file)
        .def_readonly("is_system", &Preset::is_system)
        .def_readonly("is_compatible", &Preset::is_compatible)
        .def_property_readonly("config", [](Preset &self) -> DynamicPrintConfig& { return self.config; }, py::return_value_policy::reference)
        .def("__repr__", [](const Preset &self) {
            return "<Preset '" + self.name + "'>";
        });

    // ── Preset::Type enum ─────────────────────────────────────────────────
    py::enum_<Preset::Type>(preset_mod, "PresetType")
        .value("PRINT", Preset::Type::TYPE_PRINT)
        .value("FILAMENT", Preset::Type::TYPE_FILAMENT)
        .value("PRINTER", Preset::Type::TYPE_PRINTER)
        .value("PHYSICAL_PRINTER", Preset::Type::TYPE_PHYSICAL_PRINTER)
        .value("SLA_MATERIAL", Preset::Type::TYPE_SLA_MATERIAL)
        .value("SLA_PRINT", Preset::Type::TYPE_SLA_PRINT)
        .export_values();

    // ── FilamentInfo (from ProjectTask.hpp) ───────────────────────────────
    py::class_<FilamentInfo>(preset_mod, "FilamentInfo")
        .def_readonly("id", &FilamentInfo::id)
        .def_readonly("type", &FilamentInfo::type)
        .def_readonly("color", &FilamentInfo::color)
        .def_readonly("filament_id", &FilamentInfo::filament_id)
        .def_readonly("brand", &FilamentInfo::brand)
        .def_readonly("used_m", &FilamentInfo::used_m)
        .def_readonly("used_g", &FilamentInfo::used_g)
        .def_readonly("tray_id", &FilamentInfo::tray_id)
        .def_readonly("distance", &FilamentInfo::distance)
        .def_readonly("ctype", &FilamentInfo::ctype)
        .def_readonly("colors", &FilamentInfo::colors)
        .def_readonly("mapping_result", &FilamentInfo::mapping_result)
        .def_readonly("used_for_support", &FilamentInfo::used_for_support)
        .def_readonly("used_for_object", &FilamentInfo::used_for_object)
        .def_readonly("group_id", &FilamentInfo::group_id)
        .def_readonly("nozzle_diameter", &FilamentInfo::nozzle_diameter)
        .def_readonly("nozzle_volume_type", &FilamentInfo::nozzle_volume_type)
        .def_readonly("ams_id", &FilamentInfo::ams_id)
        .def_readonly("slot_id", &FilamentInfo::slot_id);

    // ── PresetBundle ─────────────────────────────────────────────────────
    py::class_<PresetBundle>(preset_mod, "PresetBundle")
        .def(py::init<>())
        .def("load_vendor_configs", [](PresetBundle &self, const std::string &path, const std::string &vendor_name) -> size_t {
            auto flags = PresetBundle::LoadConfigBundleAttribute::LoadSystem;
            auto result = self.load_vendor_configs_from_json(
                path, vendor_name, flags,
                ForwardCompatibilitySubstitutionRule::Enable
            );
            return result.second;
        }, "Load vendor profiles from a directory path (e.g. profiles/BBL)")
        .def("load_project_embedded_presets", [](PresetBundle &self, const std::vector<Preset*> &presets) {
            self.load_project_embedded_presets(
                presets, ForwardCompatibilitySubstitutionRule::Enable
            );
        }, "Load presets embedded in a .3mf project")
        .def("set_filament_preset", &PresetBundle::set_filament_preset)
        .def("update_multi_material_filament_presets", &PresetBundle::update_multi_material_filament_presets)
        .def("full_config", [](PresetBundle &self) {
            return self.full_config(true);
        }, "Get the full resolved configuration combining all active presets")
        .def("full_config_secure", [](PresetBundle &self) {
            return self.full_config_secure();
        }, "Get the full config with sensitive settings removed")
        .def("get_printer_extruder_count", &PresetBundle::get_printer_extruder_count)
        .def_property_readonly("prints", [](PresetBundle &self) -> PresetCollection& { return self.prints; }, py::return_value_policy::reference)
        .def_property_readonly("filaments", [](PresetBundle &self) -> PresetCollection& { return self.filaments; }, py::return_value_policy::reference)
        .def_property_readonly("printers", [](PresetBundle &self) -> PresetCollection& { return self.printers; }, py::return_value_policy::reference)
        .def_readonly("project_config", &PresetBundle::project_config)
        .def("__repr__", [](const PresetBundle &self) {
            return "<PresetBundle prints=" + std::to_string(self.prints.size())
                + " filaments=" + std::to_string(self.filaments.size())
                + " printers=" + std::to_string(self.printers.size()) + ">";
        });

    // ── PresetCollection ──────────────────────────────────────────────────
    py::class_<PresetCollection>(preset_mod, "PresetCollection")
        .def("size", &PresetCollection::size)
        .def("get", [](PresetCollection &self, size_t idx) -> Preset* {
            if (idx < self.size()) return &self.preset(idx);
            return nullptr;
        }, py::return_value_policy::reference)
        .def("find_preset", [](PresetCollection &self, const std::string &name) -> Preset* {
            return self.find_preset(name, false);
        }, py::return_value_policy::reference)
        .def("get_edited_preset", [](PresetCollection &self) -> Preset& { return self.get_edited_preset(); }, py::return_value_policy::reference)
        .def("__iter__", [](PresetCollection &self) {
            return py::make_iterator(self.begin(), self.end());
        }, py::keep_alive<0, 1>())
        .def("__len__", &PresetCollection::size);
}
