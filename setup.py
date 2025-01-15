from setuptools import setup, find_packages

setup(
    name='keprompt',
    version='0.1.0',
    description='Knowledge Engineering of LLM Prompts ',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/JerryWestrick/keprompt.git',
    author='Jerry Westrick',
    author_email='jerry@westrick.com',
    license='None',  # or whatever license you choose
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'keprompt=keprompt.keprompt:main'  # This line makes 'keprompt' an executable command
        ],
    },
    install_requires=[
        # Any dependencies your package has
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)