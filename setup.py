from setuptools import setup, find_packages

setup(
    name="abstract_pypit",
    version='0.0.1',
    description="One-command PyPI publisher + GitHub pusher.",
    author="putkoff",
    author_email="partners@abstractendeavors.com",
    license="MIT",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["requests"],
    entry_points={
        "console_scripts": [
            "abstract-pypit = pypit.main:runPypit",
            "pypit-github   = pypit.github_only:runGithubOnly",
        ],
    },
    url="https://github.com/AbstractEndeavors/abstract_pypit",
)
