from setuptools import setup, find_packages

setup(
    name='TunaSwap',
    version='0.5.0',
    packages=find_packages(),
    url='https://github.com/Aureliano90/TunaSwap',
    license='GNU Affero General Public License v3.0',
    author='Aureliano',
    author_email='shuhui.1990+@gmail.com',
    description='',
    python_requires=">=3.10",
    install_requires=['requests~=2.27.1',
                      'terra_sdk~=2.0.5',
                      'attrs~=21.4.0'],
)
