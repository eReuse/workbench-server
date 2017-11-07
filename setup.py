from setuptools import find_packages, setup

tests_require = [
    'assertpy'
]

setup(
    name='eReuse-WorkbenchServer',
    version='0.2',
    packages=find_packages(exclude=('contrib', 'docs', 'scripts')),
    url='https://github.com/eReuse/acelerywb',
    license='AGPLv3 License',
    author='Garito and eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    description='Workbench manager for servers',
    # Updated in 2017-07-29
    install_requires=[],
    keywords='eReuse.org Workbench devices reuse recycle it asset management',
    test_suite='workbench_server.tests',
    tests_require=tests_require,
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