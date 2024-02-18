import scipplan

from setuptools import setup, find_packages

def readme():
    with open("README.md") as f:
        return f.read()

setup(
    name='scipplan',  # Replace with your package name
    version=scipplan.__version__,  # Set your desired version
    description="Metric Hybrid Factored Planning in Nonlinear Domains with Constraint Generation in Python.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    author=scipplan.__author__,
    author_email=scipplan.__email__,
    packages=find_packages(),  # Automatically find all packages
    include_package_data=True,
    package_data={
        "": ["translation/*.txt"], 
        # "scipplan": ["translation/*.txt"]
        },
    install_requires=[
        "PySCIPOpt>=4.3.0"
    ],
    entry_points={
        'console_scripts': [
            'scipplan = scipplan.scipplan:main',  # Specify the entry point
        ],
    },
)



# setup(
#     name="scipplan",
#     version=scipplan.__version__,
#     author="Ari Gestetner, Dr. Buser Say",
#     author_email="ages0001@student.monash.edu",
#     description="Metric Hybrid Factored Planning in Nonlinear Domains with Constraint Generation in Python.",
#     long_description=read_file("README.md"),
#     long_description_content_type="text/markdown",
#     license="MIT License",
#     keywords=["scip", "automated planner"],
#     url="https://github.com/",
#     packages=find_packages(),
#     scripts=["scripts/scipplan"],
#     install_requires=[
#         "PySCIPOpt"
#     ],
#     include_package_data=True,
#     zip_safe=False,
#     classifiers=[
#         "Development Status :: 3 - Alpha",
#         "Environment :: Console",
#         "Intended Audience :: Science/Research",
#         "License :: OSI Approved :: MIT License",
#         "Natural Language :: English",
#         "Operating System :: OS Independent",
#         "Programming Language :: Python :: 3",
#         "Topic :: Scientific/Engineering :: Artificial Intelligence"
#     ],
# )