import os
from setuptools import setup, find_packages


# Optional: read requirements.txt dynamically
def read_requirements(filename="requirements.txt"):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="Mt4PredictServer",
    version="1.0.0",
    author="Noel M nguemechieu",
    author_email="nguemechieu@live.com",
    description="AI-powered trading software for MetaTrader 4/5",
    long_description=open("README.md", "r", encoding="utf-8").read()
    if os.path.exists("README.md")
    else "",
    long_description_content_type="text/markdown",
    keywords=["metatrader", "ai", "trading", "prediction", "forex"],
    url="https://github.com/nguemechieu/Mt4PredictServer",
    include_package_data=True,
    zip_safe=False,
    packages=find_packages(exclude=["tests*", "examples*"]),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    entry_points={
        "console_scripts": [
            "Mt4PredictServer =app.main:main",
        ],
    },
    install_requires=read_requirements(),
)
