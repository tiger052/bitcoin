import setuptools

install_requires = [
   'pyjwt>=2.0.0',
   'pandas',
   'requests',
   'websockets'
]

with open("README.md", "r", encoding='UTF-8') as fh:
    long_description = fh.read()

author_email = 'brayden.jo@outlook.com, ' \
               'jonghun.yoo@outlook.com, ' \
               'pyquant@outlook.com'

setuptools.setup(
    name='pyupbit',
    version='0.2.33',
    author='Jonghun Yoo, Brayden Jo',
    author_email=author_email,
    description='python wrapper for Upbit API',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/sharebook-kr/pyupbit',
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
