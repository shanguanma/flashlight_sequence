#!/usr/bin/env python3
"""
Copyright (c) Facebook, Inc. and its affiliates.
This source code is licensed under the MIT-style license found in the
LICENSE file in the root directory of this source tree.
"""

import datetime
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

from packaging import version
from setuptools import Extension, find_namespace_packages, setup
from setuptools.command.build_ext import build_ext

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Path relative to project root that contains Python artifacts for packaging
PACKAGE_DIR = "bindings/python"
ARTIFACTS_DIR = os.path.join(PACKAGE_DIR, "flashlight/lib/sequence")
BUILD_VERSION_PATH = Path(os.path.join(THIS_DIR, "BUILD_VERSION.txt"))


# Environment variables:
# - `USE_CUDA=1` enables building with CUDA support
# By default builds with USE_CUDA=0


def check_env_flag(name, default=""):
    return os.getenv(name, default).upper() in ["ON", "1", "YES", "TRUE", "Y"]


def check_negative_env_flag(name, default="") -> bool:
    return os.getenv(name, default).upper() in ["OFF", "0", "NO", "FALSE", "N"]


def get_local_version_suffix() -> str:
    date_suffix = datetime.datetime.now().strftime("%Y%m%d")
    git_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent
    ).decode("ascii")[:-1]
    return f"+{git_hash}.d{date_suffix}"


def write_version_file(version: str):
    version_path = os.path.join(THIS_DIR, ARTIFACTS_DIR, "version.py")
    with open(version_path, "w") as f:
        f.write("# noqa: C801\n")
        f.write(f'__version__ = "{version}"\n')
        tag = os.getenv("GIT_TAG")
        if tag is not None:
            f.write(f'git_tag = "{tag}"\n')


class CMakeExtension(Extension):
    def __init__(self, name):
        Extension.__init__(self, name, sources=[])


class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        cmake_version = re.search(r"version\s*([\d.]+)", out.decode().lower()).group(1)
        if version.parse(cmake_version) < version.parse("3.18"):
            raise RuntimeError(
                "CMake >= 3.18 is required to build flashlight-sequence Python bindings"
            )

        # our CMakeLists builds all the extensions at once
        for ext in self.extensions:
            self.build_extensions(ext)

    def build_extensions(self, ext):
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        ext_dir = str(Path(self.get_ext_fullpath(ext.name)).absolute().parent)
        source_dir = str(Path(__file__).absolute().parent)
        use_cuda = "ON" if check_env_flag("USE_CUDA") else "OFF"
        use_openmp = "OFF" if check_negative_env_flag("USE_OPENMP") else "ON"
        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + ext_dir,
            "-DPython3_EXECUTABLE=" + sys.executable,
            "-DBUILD_SHARED_LIBS=ON",
            "-DFL_SEQUENCE_BUILD_TESTS=OFF",
            "-DFL_SEQUENCE_BUILD_PYTHON=ON",
            "-DFL_SEQUENCE_BUILD_PYTHON_PACKAGE=ON",
            "-DFL_SEQUENCE_BUILD_STANDALONE=OFF",
            "-DFL_SEQUENCE_USE_OPENMP=" + use_openmp,
            "-DFL_SEQUENCE_USE_CUDA=" + use_cuda,
        ]
        cfg = "Debug" if self.debug else "Release"
        build_args = ["--config", cfg]

        if platform.system() == "Windows":
            cmake_args += [
                "-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), ext_dir),
                "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), ext_dir),
                "-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), ext_dir),
            ]
            if sys.maxsize > 2**32:
                cmake_args += ["-A", "x64"]
            build_args += ["--", "/m"]
        else:
            cmake_args += ["-DCMAKE_BUILD_TYPE=" + cfg]
            build_args += ["--", "-j4"]

        env = os.environ.copy()
        env["CXXFLAGS"] = '{} -fPIC -DVERSION_INFO=\\"{}\\"'.format(
            env.get("CXXFLAGS", ""), self.distribution.get_version()
        )

        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(
            ["cmake", source_dir] + cmake_args, cwd=self.build_temp, env=env
        )
        subprocess.check_call(
            ["cmake", "--build", "."] + build_args, cwd=self.build_temp
        )


def main():
    if os.getenv("BUILD_VERSION"):
        version = os.getenv("BUILD_VERSION")
    elif BUILD_VERSION_PATH.is_file():
        version = BUILD_VERSION_PATH.read_text().strip()
    else:
        version_txt = os.path.join(THIS_DIR, PACKAGE_DIR, "version.txt")
        with open(version_txt) as f:
            version = f.readline().strip()
        version += get_local_version_suffix()

    write_version_file(version)

    # Read Python bindings README
    long_description = (Path(PACKAGE_DIR) / "README.md").read_text()

    setup(
        name="flashlight-sequence",
        version=version,
        url="https://github.com/flashlight/sequence",
        author="Jacob Kahn",
        author_email="jacobkahn1@gmail.com",
        description="Flashlight Sequence bindings for Python",
        long_description=long_description,
        long_description_content_type="text/markdown",
        packages=find_namespace_packages(
            where=PACKAGE_DIR,
            include=["flashlight.lib.sequence", "flashlight.lib.sequence.criterion"],
            exclude=["test"],
        ),
        package_dir={"": PACKAGE_DIR},
        ext_modules=[CMakeExtension("flashlight.lib.sequence.criterion")],
        cmdclass={"build_ext": CMakeBuild},
        zip_safe=False,
        license="BSD licensed, as found in the LICENSE file",
        python_requires=">=3.6",
        classifiers=[
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "Operating System :: OS Independent",
        ],
    )


if __name__ == "__main__":
    main()
