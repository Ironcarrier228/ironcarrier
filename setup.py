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
            ('ironcarrier/vectors/layer4/*.py', None, None),
            ('ironcarrier/vectors/layer7/*.py', None, None),
            ('ironcarrier/vectors/amplification/*.py', None, None),
            ('ironcarrier/utils/recon/*.py', None, None),
            ('ironcarrier/utils/osint/*.py', None, None),
            ('ironcarrier/utils/proxy/*.py', None, None),
            ('ironcarrier/utils/payload/*.py', None, None),
            ('ironcarrier/utils/opsec/*.py', None, None),
            ('ironcarrier/net/*.py', None, None),
            ('ironcarrier/c2/*.py', None, None),
            ('ironcarrier/gui/web/*.py', None, None),
            ('ironcarrier/gui/tui/*.py', None, None),
            ('ironcarrier/plugins/*.py', None, None),
            ('ironcarrier/plugins/examples/*.py', None, None),
        ],
    },
    zip_safe=False,
)
