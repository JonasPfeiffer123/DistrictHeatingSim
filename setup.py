from setuptools import setup, find_packages

def read_requirements(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

setup(
    name="districtheatingsim",  # Name des Pakets
    version="0.1",  # Versionsnummer
    description="A simulation tool for district heating systems",  # Beschreibung
    author="Dipl.-Ing. (FH) Jonas Pfeiffer",  # Autor
    maintainer="Dipl.-Ing. (FH) Jonas Pfeiffer",  # Verantwortlicher
    packages=find_packages(where="src"),  # Suche Pakete im Ordner "src"
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    package_dir={"": "src"},  # Root ist "src"
    install_requires=read_requirements('requirements.txt'),
    include_package_data=True,  # Falls Daten wie .csv in Paketen enthalten sind
    package_data={
        'your_package': ['data/*.csv', 'data/*.json', 'data/*.dat', 'gui/LeafletTab/*.js', 'gui/LeafletTab/*.html'],  # Beispiel für Datenpakete
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",
    ],
    python_requires="~=3.11",  # Getestet mit Python 3.11
    url="https://github.com/JonasPfeiffer123/DistrictHeatingSim",  # URL zum Projekt
)
