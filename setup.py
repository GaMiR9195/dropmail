import setuptools

with open("dropmail/__version__.py", "r") as fh:
    exec(fh.read())

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='dropmail',
    version=__version__,
    author='gam1r (discord)',
    author_email='miroslavtarasov0@gmail.com',
    description='Python wrapper for https://dropmail.me API',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/yourusername/dropmail-python',
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.6',
    install_requires=[
        'requests>=2.25.0',
        'aiohttp>=3.7.0',
    ],
    keywords='dropmail temporary email disposable api client tempmail mail temp simple wrapper gmail email',
)