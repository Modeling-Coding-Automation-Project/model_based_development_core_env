#ifndef MY_FUNC_HPP_
#define MY_FUNC_HPP_

namespace my_func {

inline double add(double a, double b) { return a + b; }

class Calculator {
public:
  Calculator() : store(0.0) {}

  double integrate(double in) {
    store += in;
    return store;
  }

  void reset() { store = 0.0; }

  double store;
};

} // namespace my_func

#endif // MY_FUNC_HPP_
