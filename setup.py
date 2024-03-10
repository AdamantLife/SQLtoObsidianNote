import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sqltoobsidiannote",
    version="0.0.1",
    author="AdamantLife",
    author_email="",
    description="Creates Obsidian Note markdown files from SQL schema",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AdamantLife/SQLtoObsidianNote",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        "sqlglot[rs]==22.2.0"
        ],
    entry_points={
        'console_scripts': [
            'sqltonote=SQLtoObsidianNote.__main__:cli',
        ],
    }
)
