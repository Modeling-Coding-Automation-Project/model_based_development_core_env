import os
import sys
import importlib
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from source.my_func import add
from SIL_operator import SIL_Operator

current_dir = os.path.dirname(__file__)
generator = SIL_Operator("my_func.py", current_dir)
generator.build_SIL_code(build_type="Debug")

MyFuncSIL = importlib.import_module("MyFuncSIL")

MyFuncSIL.initialize()


def main():
    test_patterns = [
        (1.0, 2.0),
        (-4.5, 2.0),
        (1e6, 1e-3),
    ]

    for a, b in test_patterns:
        python_result = add(a, b)
        sil_result = MyFuncSIL.add(a, b)

        print(f"Inputs: a={a}, b={b}")
        print(f"Python result: {python_result}")
        print(f"C++ SIL result: {sil_result}")

        if python_result != sil_result:
            raise AssertionError(
                f"Mismatch detected for a={a}, b={b}: "
                f"python={python_result}, sil={sil_result}"
            )

    print("All equivalence checks passed.")


if __name__ == "__main__":
    main()
