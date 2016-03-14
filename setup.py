from setuptools import setup

setup(
    name="pyhugh",
    version="0.1",
    py_modules=["pyhugh"],
    description="Python library for the Hue API",
    license="ISC",
    author="mutantmonkey",
    author_email="pyhugh@mutantmonkey.in",
    keywords="hue pyhugh",
    url="https://github.com/mutantmonkey/pyhugh",
    install_requires=["requests>=2.4"]
)
