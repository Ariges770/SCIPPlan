import scipplan

from setuptools import setup, find_packages

def readme():
    with open("README.md") as f:
        return f.read()

setup(
    name='scipplan', 
    version=scipplan.__version__, 
    description="Metric Hybrid Factored Planning in Nonlinear Domains with Constraint Generation in Python.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license="MIT License",
    author=scipplan.__author__,
    author_email=scipplan.__email__,
    packages=find_packages(),  # Automatically find all packages
    include_package_data=True,
    package_data={
        # "": ["translation/*.txt"], 
        "scipplan": ["translation/*.txt"]
        },
    install_requires=[
        # "PySCIPOpt>=4.3.0"
        # "pyscipopt>=4.0.0"
        "PySCIPOpt==5.2.1",
        "sympy==1.13.3"
    ],
    entry_points={
        'console_scripts': [
            'scipplan = scipplan.scipplan:main',  # Entry point
        ],
    },
    keywords=["scip", "automated planner"],
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
    ]
)



