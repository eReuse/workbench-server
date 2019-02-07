from setuptools import find_packages, setup

setup(
    name='eReuse-WorkbenchServer',
    version='0.5.0a3',
    packages=find_packages(exclude=('contrib', 'docs', 'scripts')),
    url='https://github.com/ereuse/workbench-server',
    license='AGPLv3 License',
    author='Garito and eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='Workbench manager.',
    install_requires=[
        'cachetools',
        'cefpython3==66.0',
        'ereuse-utils [usb_flash_drive,naming,test,session]>=0.4b20',
        'flask>=1.0.2',
        'flask-cors',
        'pycups',
        'pyusb',
        'requests',
        'deepmerge',
        'more-itertools'
    ],
    keywords='eReuse.org Workbench devices reuse recycle it asset management',
    test_suite='workbench_server.tests',
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest',
        'requests_mock'
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Flask',
        'Intended Audience :: Manufacturing',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Operating System :: Linux',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Office/Business',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'
    ]
)
