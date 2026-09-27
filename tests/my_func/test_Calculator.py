import os
import sys
import importlib
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from tests.tools.simulation_plotter import SimulationPlotter
from source.my_func import Calculator
from SIL_operator import SIL_Operator

current_dir = os.path.dirname(__file__)
generator = SIL_Operator("my_func.py", current_dir)
generator.build_SIL_code(build_type="Debug")

MyFuncSIL = importlib.import_module("MyFuncSIL")

MyFuncSIL.initialize()


def main():
    calculator = Calculator()
    sil_calculator = MyFuncSIL.Calculator()

    plotter = SimulationPlotter()

    max_step = 20

    input_signal = 0.0
    result = [0.0] * max_step

    for i in range(max_step):

        if i > 5:
            input_signal = 1.0

        if i == 10:
            calculator.reset()
            sil_calculator.reset()

        python_result = calculator.integrate(input_signal)
        sil_result = sil_calculator.integrate(input_signal)
        result[i] = python_result

        if python_result != sil_result:
            raise AssertionError(
                f"Mismatch detected at step={i}, input={input_signal}: "
                f"python={python_result}, sil={sil_result}"
            )

        plotter.append_name(result[i], "result")
        plotter.append_name(input_signal, "input")

    print("All equivalence checks passed.")

    plotter.assign("result", position=(0, 0), label="result")
    plotter.assign("input", position=(1, 0), label="input")

    plotter.plot("Calculator Test")


if __name__ == "__main__":
    main()
