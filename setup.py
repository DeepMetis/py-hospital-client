from setuptools import setup, find_packages

setup(
    name="hospital-client",
    version="0.1.3",
    packages=find_packages(),
    install_requires=["aiohttp==3.10.5", "pydantic==2.9.0", "pycryptodome==3.20.0"],
    author="Karim Dahmeni",
    author_email="karim.dahmeni@deepmetis.com",
    description="A client for interacting with the service hospital",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/DeepMetis/py-hospital-client",
    license="MIT",
)
