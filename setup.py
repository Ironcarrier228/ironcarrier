from setuptools import setup, find_packages
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()
setup(
    name='ironcarrier',
    version='2.4.0',
    description='Multi-Vector Stress Testing Framework',
    long_description=long_description,
    author='IronCarrier Team',
    packages=find_packages(exclude=['tests*', '*.tests*']),
    python_requires='>=3.8',
    install_requires=[
        'cryptography>=41.0.0',
        'flask>=3.0.0',
        'rich>=13.0.0',
        'pyyaml>=6.0',
    ],
    extras_require={
        'gui': ['flask>=3.0.0', 'flask-cors>=4.0.0', 'gevent>=23.9.0', 'gevent-websocket>=0.10.1'],
        'tui': ['rich>=13.0.0'],
        'dns': ['dnspython>=2.4.0'],
        'dev': ['pytest>=7.0.0', 'pytest-asyncio>=0.21.0', 'flake8>=6.0.0', 'black>=23.0.0', 'mypy>=1.5.0'],
    },
    entry_points={
        'console_scripts': [
            'ironcarrier=ironcarrier.__main__:main',
        ],
    },
    include_package_data=True,
    package_data={
        'ironcarrier': [
            'vectors/layer4/*.py',
            'vectors/layer7/*.py',
            'vectors/amplification/*.py',
            'utils/recon/*.py',
            'utils/osint/*.py',
            'utils/proxy/*.py',
            'utils/payload/*.py',
            'utils/opsec/*.py',
            'net/*.py',
            'c2/*.py',
            'gui/web/*.py',
            'gui/tui/*.py',
            'plugins/*.py',
            'plugins/examples/*.py',
        ],
    },
    zip_safe=False,
)
