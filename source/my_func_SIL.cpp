#include <pybind11/pybind11.h>

#include "my_func.hpp"

namespace py = pybind11;

namespace my_func_SIL {

void initialize(void) {}

// Method: add
double add(double a, double b) { return my_func::add(a, b); }

} // namespace my_func_SIL

PYBIND11_MODULE(MyFuncSIL, m) {
  m.def("initialize", &my_func_SIL::initialize, "Initialize the module");
  m.def("add", &my_func_SIL::add, "add method");

  py::class_<my_func::Calculator>(m, "Calculator")
      .def(py::init<>())
      .def("integrate", &my_func::Calculator::integrate)
      .def("reset", &my_func::Calculator::reset);
}
