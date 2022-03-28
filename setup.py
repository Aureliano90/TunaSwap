from setuptools import setup, find_packages

setup(
    name='TunaSwap',
    version='0.1.0',
    packages=find_packages(),
    url='https://github.com/Aureliano90/TunaSwap',
    license='GNU Affero General Public License v3.0',
    author='Aureliano',
    author_email='81753529+Aureliano90@users.noreply.github.com',
    description='',
    python_requires=">=3.8",
    install_requires=['requests~=2.27.1',
                      'terra_sdk~=2.0.5'],
)
