import pathlib

import setuptools

__package_name = "rs_store"
__root_directory_path = pathlib.Path(__file__).parent
__package_directory_path = __root_directory_path / __package_name

if __name__ == '__main__':
    setuptools.setup(
        name=__package_name,
        version="0.0.1",
        author="Raymond Tunstill",
        author_email="ray.tunstill@live.co.uk",
        description="Data capture example for D400 Cameras by Raymond Tunstill.",
        long_description=open('README.md').read(),
        long_description_content_type="text/markdown",
        packages=list(filter(lambda x: __package_name in x, setuptools.find_packages(exclude=["tests"]))),
        classifiers=["Programming Language :: Python :: 3"],
        setup_requires=['wheel', "Cython"],
        install_requires=[
            'Cython',
            'numpy',
            'raytils',
            'opencv-python',
            'tqdm',
            'pyyaml',
            'pyrealsense2',
        ],
        python_requires='>=3.7',
    )