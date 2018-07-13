from setuptools import setup


if __name__ == "__main__":
    setup(
        name='tox-edm',
        author="Ioannis Tziakos",
        description='tox plugin to use edm environments',
        license="BSD license",
        version='0.1',
        py_modules=['tox_edm'],
        entry_points={'tox': ['edm = tox_edm']},
        install_requires=['tox>=2.0'],
    )
