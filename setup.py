import setuptools

setuptools.setup(
    name="np2_ultra",
    version="0.2.0",
    url="https://github.com/saharmanavi/np2_ultra",

    author="Sahar Manavi",
    author_email="saharm@alleninstitute.org",

    description="process and analyze neuropixels ultra data collected from NP2",
    long_description=open('README.md').read(),

    packages=setuptools.find_packages(),

    install_requires=[
                        'matlab',
                        'pandas',
                        'numpy',
                        'allensdk',
                        'matplotlib',
                        'seaborn',
                        'glob2',
                                ],

    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
                                                ],
)
