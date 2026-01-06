from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pi169",   # package name based on folder src/pi169
    version="0.1.0",
    author="169PI",
    author_email="support@169pi.com",
    description="Production-ready Python SDK for Alpie-Core, a 4-bit quantized 32B reasoning model achieving state-of-the-art efficiency and performance",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/169Pi/Pi169-SDK",

    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    license="Apache-2.0",

    install_requires=[
        "certifi>=2025.11.12",
        "httpx>=0.28.1",
        "httpcore>=1.0.9",
        "h11>=0.16.0",
        "idna>=3.11",
        "sniffio>=1.3.1",
        "packaging>=25.0",
        "python-dotenv",
    ],

    extras_require={
        "dev": [
            "pytest>=9.0.1",
            "pytest-mock>=3.15.1",
        ]
    },

    python_requires=">=3.10",

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],

    # CLI entry point
    entry_points={
        "console_scripts": [
            "pi169=pi169.cli:main",
        ]
    },
)
