from setuptools import setup, find_packages

setup(
    name='asyncTwitterClient',
    version='0.8.0',
    author='obnoxious',
    author_email='obnoxious@dongcorp.org',
    description='A async port of twitter-api-client with extra features',
    long_description='A async port of twitter-api-client with extra features | Please see https://github.com/obnoxiousish/async_twitter_api_client for more information',
    long_description_content_type='text/markdown',
    url='https://github.com/obnoxiousish/async_twitter_api_client',
    packages=find_packages(),
    install_requires=[
        'httpx',
        'anyio',
        'trio',
        'httpx[socks]',
        'httpx-socks',
        'twitter-api-client',
        'colorama',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Framework :: AsyncIO',
    ],
    python_requires='>=3.7',
)
