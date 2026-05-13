from setuptools import setup, find_packages

setup(
    name="bangumi-skill",
    version="1.0.0",
    description="Bangumi anime info query tool",
    packages=find_packages(),
    install_requires=["requests>=2.25.0", "beautifulsoup4>=4.9.0"],
    python_requires=">=3.8",
)
