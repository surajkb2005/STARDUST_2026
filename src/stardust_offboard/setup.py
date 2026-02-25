from setuptools import setup, find_packages

package_name = 'stardust_offboard'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(),
    package_dir={'': '.'},
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Team Stardust',
    maintainer_email='team@stardust.com',
    description='IRoC-U Qualification Offboard Control',
    license='Apache License 2.0',
    entry_points={
        'console_scripts': [
            'offboard_node = stardust_offboard.offboard_node:main',
        ],
    },
)
