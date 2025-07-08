#!/usr/bin/env python3
"""Setup script for Python NMEA 0183 Simulator."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="nmea-simulator",
    version="1.0.0",
    author="NMEA Simulator Development Team",
    author_email="dev@nmea-simulator.com",
    description="A comprehensive Python NMEA 0183 data simulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nmea-simulator/nmea-simulator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "nmea-simulator=simulator.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
)

