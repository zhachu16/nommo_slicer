#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "libslic3r/Config.hpp"
#include "libslic3r/PrintConfig.hpp"

namespace py = pybind11;
using namespace Slic3r;

void init_config_bind(py::module &m) {
    auto config_mod = m.def_submodule("config", "Dynamic configuration system");

    // ── ConfigOption types ───────────────────────────────────────────────
    py::class_<ConfigOption>(config_mod, "ConfigOption");

    py::class_<ConfigOptionFloat, ConfigOption>(config_mod, "ConfigOptionFloat")
        .def_property_readonly("value", [](ConfigOptionFloat &self) { return self.getFloat(); });

    py::class_<ConfigOptionInt, ConfigOption>(config_mod, "ConfigOptionInt")
        .def_property_readonly("value", [](ConfigOptionInt &self) { return self.getInt(); });

    py::class_<ConfigOptionString, ConfigOption>(config_mod, "ConfigOptionString")
        .def_property_readonly("value", [](ConfigOptionString &self) -> const std::string& { return self.value; });

    py::class_<ConfigOptionBool, ConfigOption>(config_mod, "ConfigOptionBool")
        .def_property_readonly("value", [](ConfigOptionBool &self) { return self.getBool(); });

    py::class_<ConfigOptionFloatOrPercent, ConfigOption>(config_mod, "ConfigOptionFloatOrPercent")
        .def_property_readonly("value", [](ConfigOptionFloatOrPercent &self) { return self.get_abs_value(1.0); })
        .def_readonly("percent", &ConfigOptionFloatOrPercent::percent);

    // ── DynamicPrintConfig ──────────────────────────────────────────────
    py::class_<DynamicPrintConfig>(config_mod, "DynamicPrintConfig")
        .def(py::init<>())
        .def("option", [](DynamicPrintConfig &self, const std::string &key) -> ConfigOption* {
            return self.option(key);
        }, py::return_value_policy::reference)
        .def("has", [](DynamicPrintConfig &self, const std::string &key) { return self.has(key); })
        .def("keys", [](DynamicPrintConfig &self) { return self.keys(); })
        .def("get_float", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt_float(key);
        })
        .def("get_int", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt_int(key);
        })
        .def("get_string", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt_string(key);
        })
        .def("get_bool", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt_bool(key);
        })
        .def("get_ints", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt<ConfigOptionInts>(key)->values;
        })
        .def("get_floats", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt<ConfigOptionFloats>(key)->values;
        })
        .def("get_strings", [](DynamicPrintConfig &self, const std::string &key) {
            return self.opt<ConfigOptionStrings>(key)->values;
        })
        .def("set_float", [](DynamicPrintConfig &self, const std::string &key, double val) {
            self.set(key, val, true);
        })
        .def("set_int", [](DynamicPrintConfig &self, const std::string &key, int val) {
            self.set(key, val, true);
        })
        .def("set_string", [](DynamicPrintConfig &self, const std::string &key, const std::string &val) {
            self.set(key, val, true);
        })
        .def("set_bool", [](DynamicPrintConfig &self, const std::string &key, bool val) {
            self.set(key, val, true);
        })
        .def("apply", [](DynamicPrintConfig &self, const DynamicPrintConfig &other) {
            self.apply(other);
        })
        .def("__repr__", [](const DynamicPrintConfig &self) {
            std::string out = "DynamicPrintConfig(";
            for (const auto &k : self.keys()) {
                out += k + ", ";
            }
            out += ")";
            return out;
        });
}
