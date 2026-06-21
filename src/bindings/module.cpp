#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

namespace py = pybind11;

// Forward declarations for binding init functions
void init_model_bind(py::module &m);
void init_config_bind(py::module &m);
void init_preset_bind(py::module &m);
void init_print_bind(py::module &m);
void init_gcode_bind(py::module &m);

// Custom exception type for nommo errors
class NommoNativeError : public std::exception {
public:
    NommoNativeError(std::string code, std::string message)
        : m_code(std::move(code)), m_message(std::move(message)) {}
    const char *what() const noexcept override { return m_message.c_str(); }
    const std::string &code() const { return m_code; }
private:
    std::string m_code;
    std::string m_message;
};

PYBIND11_MODULE(_nommo_native, m) {
    m.doc() = "NOMMO Slicing Library - Native C++ bindings";

    // Register exception
    static py::exception<NommoNativeError> exc(m, "NommoNativeError");
    py::register_local_exception_translator([](std::exception_ptr p) {
        try {
            if (p) std::rethrow_exception(p);
        } catch (const NommoNativeError &e) {
            PyErr_SetString(exc.ptr(), e.what());
        }
    });

    // Init submodules
    init_model_bind(m);
    init_config_bind(m);
    init_preset_bind(m);
    init_print_bind(m);
    init_gcode_bind(m);
}
