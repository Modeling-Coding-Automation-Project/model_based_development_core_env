"""
File: SIL_operator.py

Description: This file contains the SIL_Operator class, which is responsible for generating and building
the SIL (Static Intermediate Language) code for a given Python file. It uses CMake and pybind11 to create
a C++ extension module that can be imported in Python.

Example code to use the SIL_Operator class:
```
import os
from helper.SIL.SIL_operator import SIL_Operator

current_dir = os.path.dirname(__file__)
generator = SIL_Operator("my_func.py", current_dir)
generator.build_SIL_code()

import MyFuncSIL
MyFuncSIL.initialize()
```
"""
import os
import subprocess
import ast
import json
import fnmatch


def snake_to_camel(snake_str: str) -> str:
    """
    Convert a snake_case string to CamelCase.
    """
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


class CmakeGenerator:
    EXCLUDE_PATHS_FILE_NAME = "SIL_operator_exclude_paths.json"

    def __init__(
        self,
        original_python_file_name: str,
        python_file_dir: str,
        cpp_file_name: str,
        pybind11_module_name: str,
        SIL_folder: str,
        root_path: str,
        compile_definitions: list = None
    ):
        self.original_python_file_name = original_python_file_name
        self.pybind11_module_name = pybind11_module_name
        self.SIL_folder = SIL_folder
        self.folder_name = os.path.basename(os.path.normpath(self.SIL_folder))

        self.root_path = root_path
        self.python_file_dir = python_file_dir
        self.exclude_path_patterns = self.load_exclude_path_patterns()

        self.cpp_file_name = cpp_file_name

        # Optional list of compile-time definitions (e.g. ["__TEST__", "__DEBUG__"])
        self.compile_definitions = compile_definitions or []

    @staticmethod
    def load_exclude_path_patterns() -> list:
        """
        Load exclude path patterns from SIL_operator_exclude_paths.json.

        The config file is expected to be located in the same directory as this file.
        Supported formats:
            - {"exclude_paths": ["pattern1", "pattern2", ...]}
            - ["pattern1", "pattern2", ...]
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(
            current_dir, CmakeGenerator.EXCLUDE_PATHS_FILE_NAME)

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Exclude path config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            patterns = data.get("exclude_paths", [])
        elif isinstance(data, list):
            patterns = data
        else:
            raise ValueError(
                f"Invalid format in exclude path config: {config_path}")

        if not isinstance(patterns, list):
            raise ValueError(
                f"'exclude_paths' must be a list in: {config_path}")

        return [str(p).replace('\\', '/').strip('/') for p in patterns if str(p).strip()]

    @staticmethod
    def check_path_is_excluded(path: str, exclude_path_patterns: list) -> str:
        """
        Check if the given path matches one of exclude_path_patterns.
        If matched, return an empty string.
        Otherwise, return the original path.
        """
        normalized = path.replace('\\', '/').strip('/')

        if normalized == "":
            return path

        for pattern in exclude_path_patterns:
            normalized_pattern = pattern.replace('\\', '/').strip('/')

            # Wildcard pattern match.
            if fnmatch.fnmatch(normalized, normalized_pattern):
                return ""

            # Directory-prefix match when pattern has no wildcard.
            if not any(ch in normalized_pattern for ch in "*?[]"):
                if normalized == normalized_pattern or normalized.startswith(normalized_pattern + "/"):
                    return ""

        return path

    @staticmethod
    def discover_source_include_dirs(
        root_path: str,
        exclude_path_patterns: list,
        source_header_extensions: set = None
    ) -> list:
        """
        Discover directories under root_path that contain source files.

        Returns a list of paths relative to root_path (using forward slashes).
        The function mirrors the behavior previously embedded in
        CmakeGenerator.generate_cmake_lists_txt: it detects files with
        extensions in source_header_extensions, converts backslashes to forward slashes,
        uses '' for the root directory, and preserves discovery order while
        avoiding duplicates.
        """
        if source_header_extensions is None:
            source_header_extensions = {'.c', '.h', '.cpp', '.hpp'}

        include_dirs = []

        seen = set()

        # Normalize root_path
        root = os.path.abspath(root_path)

        # include_dirs
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() in source_header_extensions:

                    rel = os.path.relpath(dirpath, root)
                    rel = rel.replace('\\', '/')
                    if rel == '.':
                        rel = ''

                    rel = CmakeGenerator.check_path_is_excluded(
                        rel, exclude_path_patterns)

                    if (rel not in seen) and (rel != ""):
                        seen.add(rel)
                        include_dirs.append(rel)
                    break

        return include_dirs

    @staticmethod
    def discover_source_files(
        root_path: str,
        SIL_cpp_file_name: str,
        exclude_path_patterns: list,
        source_extensions: set = None
    ) -> list:

        if source_extensions is None:
            source_extensions = {'.c', '.cpp'}

        source_file_list = []

        # Normalize root_path
        root = os.path.abspath(root_path)

        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() in source_extensions:

                    original_rel = os.path.relpath(dirpath, root)
                    original_rel = original_rel.replace('\\', '/')

                    is_root = (original_rel == '.')
                    rel = '' if is_root else original_rel

                    rel = CmakeGenerator.check_path_is_excluded(
                        rel, exclude_path_patterns)

                    is_target = CmakeGenerator.check_SIL_cpp_file_name(
                        fn, SIL_cpp_file_name)

                    if not (rel == "" and not is_root) and is_target:
                        source_file_list.append(os.path.join(dirpath, fn))

        return source_file_list

    @staticmethod
    def check_SIL_cpp_file_name(
        file_name: str,
        SIL_cpp_file_name: str
    ) -> bool:
        """
        Return False when `file_name` ends with "_SIL.cpp" and is different
        from `SIL_cpp_file_name`. Otherwise return True.
        """
        if file_name.endswith("_SIL.cpp") and file_name != SIL_cpp_file_name:
            return False

        return True

    def generate_cmake_lists_txt(self):
        """
        Generate a CMakeLists.txt file for building the pybind11 module.
        """
        include_dirs = CmakeGenerator.discover_source_include_dirs(
            root_path=self.root_path,
            exclude_path_patterns=self.exclude_path_patterns)
        source_file_list = CmakeGenerator.discover_source_files(
            root_path=self.root_path,
            SIL_cpp_file_name=self.cpp_file_name,
            exclude_path_patterns=self.exclude_path_patterns)

        code_text = ""
        code_text += "cmake_minimum_required(VERSION 3.14)\n"
        code_text += "cmake_policy(SET CMP0148 NEW)\n\n"

        code_text += f"project({self.pybind11_module_name})\n\n"

        code_text += "set(CMAKE_CXX_STANDARD 11)\n"
        code_text += "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n"
        code_text += "# Debug-friendly defaults: prefer Debug builds during development so symbols are available\n"
        code_text += "if(NOT CMAKE_BUILD_TYPE)\n"
        code_text += "  set(CMAKE_BUILD_TYPE Debug CACHE STRING \"Build type\" FORCE)\n"
        code_text += "endif()\n\n"
        code_text += "set(CMAKE_CXX_FLAGS_DEBUG \"-g -O0 "

        for definition in self.compile_definitions:
            code_text += f"-D{definition} "
        code_text += "\")\n"

        code_text += "set(CMAKE_CXX_FLAGS_RELEASE \"-O2 "

        for definition in self.compile_definitions:
            code_text += f"-D{definition} "
        code_text += "\")\n"

        code_text += "set(CMAKE_CXX_FLAGS_RELEASE \"${CMAKE_CXX_FLAGS_RELEASE} -flto=auto\")\n\n"

        code_text += "find_package(pybind11 REQUIRED)\n\n"

        code_text += f"pybind11_add_module({self.pybind11_module_name} \n"
        code_text += f"    {self.python_file_dir}/{self.cpp_file_name}\n"

        for source_file in source_file_list:
            if source_file != f"{self.python_file_dir}/{self.cpp_file_name}":
                code_text += f"    {source_file}\n"

        code_text += ")\n\n"

        code_text += "# Treat warnings as errors only in Release builds to avoid blocking development\n"
        code_text += f"if(CMAKE_BUILD_TYPE STREQUAL \"Release\")\n"
        code_text += f"  target_compile_options({self.pybind11_module_name} PRIVATE -Werror)\n"
        code_text += "endif()\n\n"

        code_text += f"target_include_directories({self.pybind11_module_name} PRIVATE\n"

        for d in include_dirs:
            if d != "":
                # absolute_dir
                path = os.path.abspath(os.path.join(self.root_path, d))

                code_text += "    " + path + "\n"

        code_text += ")\n\n"

        with open(os.path.join(self.SIL_folder, "CMakeLists.txt"), "w", encoding="utf-8") as f:
            f.write(code_text)


class PythonAnalyzer:
    """
    Analyze a Python source file and extract class definitions and their methods.

    Usage:
        classes = PythonAnalyzer.parse_file('/path/to/file.py')
        # classes -> dict where keys are class names and values are lists of method info dicts

    Each method info dict contains:
        - name: method name
        - lineno: line number where the method is defined
        - decorators: list of decorator names (as strings)
    """
    @staticmethod
    def _get_decorator_name(decorator_node):
        # Try to recover a readable decorator name from AST node
        if isinstance(decorator_node, ast.Name):
            return decorator_node.id
        elif isinstance(decorator_node, ast.Attribute):
            parts = []
            node = decorator_node
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(decorator_node, ast.Call):
            # decorator with arguments, get the function part
            return PythonAnalyzer._get_decorator_name(decorator_node.func)
        else:
            return ast.dump(decorator_node)

    @staticmethod
    def parse_source(source: str) -> dict:
        """
        Parse source text and return a mapping of class names to a list of methods.
        """
        tree = ast.parse(source)

        classes = {}

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        decorators = [PythonAnalyzer._get_decorator_name(
                            d) for d in item.decorator_list]
                        methods.append({
                            'name': item.name,
                            'lineno': getattr(item, 'lineno', None),
                            'decorators': decorators,
                        })
                classes[class_name] = methods

        return classes

    @staticmethod
    def parse_file(path: str) -> dict:
        """
        Read a Python file from given path and parse it for classes and methods.
        Raises FileNotFoundError if the file doesn't exist, and SyntaxError for invalid Python.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found")

        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()

        return PythonAnalyzer.parse_source(src)


class PybindCppGenerator:
    @staticmethod
    def generate_cpp_code(
        python_file_path_with_extension: str,
        module_name: str,
        cpp_file_path_to_generate: str
    ):
        """
        Generate a C++ file that defines a pybind11 module with an initialize function.
        """

        # analyze the python file to find classes and methods
        classes = PythonAnalyzer.parse_file(python_file_path_with_extension)

        if not classes:
            raise ValueError(
                f"No classes found in {python_file_path_with_extension}. Cannot generate SIL code.")
        if len(classes) > 1:
            raise ValueError(
                f"Multiple classes found in {python_file_path_with_extension}. Only one class is supported.")

        code_text = ""
        code_text += "#include <pybind11/numpy.h>\n"
        code_text += "#include <pybind11/pybind11.h>\n\n"

        code_text += "namespace py = pybind11;\n\n"

        code_text += "void initialize(void) {}\n\n"

        method_names = set()
        for class_name, methods in classes.items():
            code_text += f"// Class: {class_name}\n"
            for method in methods:
                method_name = method['name']

                if method_name.startswith("__") and method_name.endswith("__"):
                    # Skip dunder methods
                    continue

                code_text += f"// Method: {method_name}\n"
                code_text += f"void {method_name}(void) {{}}\n\n"

                method_names.add(method_name)

        code_text += f"PYBIND11_MODULE({module_name}, m) {{\n"

        code_text += "    m.def(\"initialize\", &initialize, \"Initialize the module\");\n"

        for method_name in method_names:
            code_text += f"    m.def(\"{method_name}\", &{method_name}, \"{method_name} method\");\n"

        code_text += "}\n"

        with open(cpp_file_path_to_generate, "w", encoding="utf-8") as f:
            f.write(code_text)


class SIL_Operator:
    def __init__(
        self,
        target_python_file_name: str,
        SIL_folder: str
    ):
        self.root_path = os.getcwd()

        if target_python_file_name.endswith(".py"):
            target_python_file_name = target_python_file_name[:-3]
        else:
            raise ValueError(
                "The target_python_file_name should end with .py")

        self.target_python_file_name = target_python_file_name
        self.module_file_name = snake_to_camel(
            self.target_python_file_name) + "SIL"

        self.SIL_folder = SIL_folder

        self.folder_name = os.path.basename(os.path.normpath(self.SIL_folder))

        self.this_file_path = os.path.abspath(__file__)
        dir_path = os.path.dirname(self.this_file_path)

        self.cpp_file_path_to_generate = ""

    @staticmethod
    def find_file_path(
            file_name: str,
            root_path: str) -> str:
        """
        Recursively search for a file in the given root_path and return its full path.
        Raises FileNotFoundError if the file is not found.
        """

        for dirpath, dirnames, filenames in os.walk(root_path):
            if file_name in filenames:
                return os.path.join(dirpath, file_name)

        raise FileNotFoundError(f"{file_name} not found in {root_path}")

    def find_c_make_lists_txt(self) -> str:
        """
        Recursively search for a CMakeLists.txt file in the current directory
          and return its full path.
        Raises FileNotFoundError if the file is not found.
        """

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            if "CMakeLists.txt" in filenames:
                return os.path.join(dirpath, "CMakeLists.txt")

        raise FileNotFoundError(
            f"CMakeLists.txt not found. Delete {self.cpp_file_path_to_generate} and try again.")

    def build_pybind11_code(self, build_type: str = "Debug"):
        """
        Build the pybind11 C++ code using CMake.

        Args:
            build_type: Build configuration, either "Debug" or "Release". Defaults to "Debug".
        """

        if build_type not in ("Debug", "Release"):
            raise ValueError(
                f"build_type must be 'Debug' or 'Release', got '{build_type}'")

        build_folder = os.path.join(self.SIL_folder, "build")

        subprocess.run(f"rm -rf {build_folder}", shell=True)
        subprocess.run(f"mkdir -p {build_folder}", shell=True)
        subprocess.run(
            f"cmake -S {self.SIL_folder} -B {build_folder} -DCMAKE_BUILD_TYPE={build_type}",
            shell=True
        )
        subprocess.run(
            f"cmake --build {build_folder} --config {build_type}", shell=True)

        subprocess.run(
            f"mv {build_folder}/{self.module_file_name}.*so {self.SIL_folder}", shell=True)

    def build_SIL_code(self, compile_definitions=None, build_type: str = "Debug"):
        """
        Generate and build the SIL code for the given Python file.

        Args:
            compile_definitions: Optional list of compile-time definitions (e.g. ["__TEST__"]).
            build_type: Build configuration, either "Debug" or "Release". Defaults to "Debug".
        """
        python_file_name = self.target_python_file_name + ".py"

        python_file_path_with_extension = SIL_Operator.find_file_path(
            python_file_name, self.root_path)
        python_file_path = python_file_path_with_extension.split('.py')[0]

        self.cpp_file_path_to_generate = python_file_path + "_SIL.cpp"

        if not os.path.exists(self.cpp_file_path_to_generate):
            PybindCppGenerator.generate_cpp_code(
                python_file_path_with_extension,
                self.module_file_name,
                self.cpp_file_path_to_generate
            )

        cmake_generator = CmakeGenerator(
            self.target_python_file_name,
            os.path.dirname(python_file_path),
            self.cpp_file_path_to_generate.split('/')[-1],
            self.module_file_name,
            self.SIL_folder,
            self.root_path,
            compile_definitions=compile_definitions)
        cmake_generator.generate_cmake_lists_txt()

        self.build_pybind11_code(build_type=build_type)
