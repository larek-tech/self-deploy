import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek.models import Service
import re
from typing import Tuple, Set

class PythonAnalyze(BaseAnalyzer):
    def __init__(self) -> None:
        super().__init__() 

    def analyze(self, root: Path) -> tp.Optional[Service]: 
        if not root.is_dir():
            return None

        detected_docker=self.get_dockerfile(root)
        detected_docker_compose = self.get_docker_compose(root)
        packet_managers = self.get_packet_managers(root)
        dec_libs=self.get_libs(root)
        py_version = self.detect_python_version_by_syntax(root)
        environment = self.get_environment(root) 

        return Service(
            path=root,
            name=root.name,
            language= models.Language(name="python", version = py_version),
            dependencies=models.Dependencies(packet_manager=packet_managers, libs=dec_libs),
            config=self.get_config(root),
            docker=models.Docker(dockerfiles=detected_docker, compose=detected_docker_compose if detected_docker_compose else None, environment=environment),
            entrypoints=self.get_entrypoint(root),
            tests=self.detected_tests(root),
            linters=self.get_linters(root),
        )


    def get_environment(self, root: Path) -> tp.Optional[str]:
        env_files = {
            '.env.prod': 'production', '.env.production': 'production',
            '.env.staging': 'staging', '.env.stage': 'staging', 
            '.env.test': 'testing', '.env.testing': 'testing',
            '.env.dev': 'development', '.env.development': 'development',
            '.env.local': 'development', '.env': 'development'
        }
        for env_file, env_type in env_files.items():
            if (root / env_file).exists():
                return env_type
        for compose_file in root.glob('docker-compose*.yml'):
            name = compose_file.stem.lower()
            if 'prod' in name: return 'production'
            elif 'stage' in name: return 'staging'  
            elif 'test' in name: return 'testing'
            elif 'dev' in name: return 'development'
        
        config_files = list(root.glob('**/settings*.py')) + list(root.glob('**/config*.py'))
        for config_file in config_files[:2]:
            try:
                content = config_file.read_text()
                if 'DEBUG = True' in content: return 'development'
                if 'DEBUG = False' in content: return 'production'
            except: continue
        
        return None

    def get_dockerfile(self, root: Path) -> tp.Optional[str]:
        try:
            for docker_file in root.glob("**/Dockerfile*"):
                if docker_file.is_file():
                    return str(docker_file)
        except Exception as e:
            print(f"Error searching Dockerfile in {root}: {e}")
        return None

    def get_docker_compose(self, root: Path) -> tp.Optional[str]:
        try:
            for compose_file in root.glob("**/docker-compose*.yml"):
                if compose_file.is_file():
                    return str(compose_file)
        except Exception as e:
            print(f"Error searching docker-compose in {root}: {e}")
        return None


    def get_packet_managers(self, root: Path) -> tp.Optional[str]:
        package_managers = [
            ('poetry', self._is_poetry_project),
            ('pipenv', self._is_pipenv_project),
            ('pdm', self._is_pdm_project),
            ('rye', self._is_rye_project),
            ('hatch', self._is_hatch_project),
            ('uv', self._is_uv_project),
            ('setuptools', self._is_setuptools_project),
            ('pip', self._is_requirements_project),
        ]
    
        for name, validator in package_managers:
            if validator(root):
                return name  
        return None

    def _is_poetry_project(self, root: Path) -> bool:
        if (root / 'poetry.lock').exists():
            return True 
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            try:
                return '[tool.poetry]' in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_pipenv_project(self, root: Path) -> bool:
        return (root / 'Pipfile').exists()

    def _is_pdm_project(self, root: Path) -> bool:
        if (root / 'pdm.lock').exists() or (root / 'pdm.toml').exists():
            return True
        
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            try:
                return '[tool.pdm]' in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_rye_project(self, root: Path) -> bool:
        return (root / 'requirements.lock').exists() or (root / 'rye.toml').exists()

    def _is_hatch_project(self, root: Path) -> bool:
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            try:
                return '[tool.hatch]' in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_uv_project(self, root: Path) -> bool:
        return (root / 'uv.lock').exists()

    def _is_setuptools_project(self, root: Path) -> bool:
        return (root / 'setup.py').exists() or (root / 'setup.cfg').exists()

    def _is_requirements_project(self, root: Path) -> bool:
        requirements_files = list(root.glob('requirements*.txt'))
        return bool(requirements_files and not self._has_modern_package_manager(root))

    def _has_modern_package_manager(self, root: Path) -> bool:
        modern_indicators = [
            'pyproject.toml', 'poetry.lock', 'Pipfile', 
            'pdm.lock', 'requirements.lock', 'uv.lock'
        ]
        return any((root / indicator).exists() for indicator in modern_indicators)

    def get_libs(self, root) -> list[str]:
        libraries = []
        try:
            req_files = list(root.glob("**/requirements*.txt")) 
            for file in req_files:
                try:
                    with open(file, "r", encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if (line and not line.startswith("#") 
                                and not line.startswith("-r") 
                                and not line.startswith("--") 
                                and not line.startswith("-f")):
                            
                                pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                                if pkg_name:
                                    libraries.append(pkg_name)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
                    continue
        except Exception as e:
            print(f"Error in get_libs: {e}")
        return list(set(libraries)) 
  
    def get_config(self, root) -> list[str]:
        config_files: tp.Set[str] = set() 
        patterns = ['**/*.cfg', '**/*.ini', '**/*.yml', '**/*.yaml', '**/.env*', '**/config/*']
        for key in patterns:
            for file in root.glob(key):
                if file.is_file():
                    config_files.add(file.name)
        return list(config_files)

    def get_entrypoint(self, root) -> str:
        entrypoints = [
            "main.py", "app.py", "run.py", "manage.py",  
            "wsgi.py", "asgi.py", "application.py", root.name + ".py"
        ]       
        for candidate in entrypoints:
            try:
                candidate_file = root / candidate
                if candidate_file.exists():
                    with open(candidate_file, "r", encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "if __name__ == '__main__':" in content:
                            return str(candidate_file)
                        elif any(keyword in content for keyword in ["main()", "app.run", "manage.run", "execute"]):
                            return str(candidate_file)
            except Exception as e:
                print(f"Error checking entrypoint {candidate}: {e}")
                continue
    
        return "" 


    def detected_tests(self, root) -> str:
        test_commands = []
        config_files = {
            'pytest.ini': 'pytest',
            'pyproject.toml': 'pytest',  
            'setup.cfg': 'pytest',       
            'tox.ini': 'pytest',        
            'manage.py': 'python manage.py test',  
            'noxfile.py': 'nox', 
        }        
        for config_file, command in config_files.items():
            if (root / config_file).exists():
                if config_file == 'manage.py':
                    test_commands.append(command)
                else:
                    if self._has_test_config(root / config_file):
                        test_commands.append(command)
        
        setup_py = root / 'setup.py'
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                if 'test_suite' in content or 'pytest' in content:
                    test_commands.append('python setup.py test')
            except:
                pass  

 
        test_dirs = ['tests', 'test', 'spec']
        for test_dir in test_dirs:
            if (root / test_dir).exists():
                test_commands.append('pytest')
                break

        makefile = root / 'Makefile'
        if makefile.exists():
            try:
                content = makefile.read_text()
                if 'test:' in content or 'pytest' in content:
                    test_commands.append('make test')
            except:
                pass 


        tox_ini = root / 'tox.ini'
        if tox_ini.exists():
            try:
                content = tox_ini.read_text()
                if '[testenv]' in content:
                    test_commands.append('tox')
            except:
                pass 
                

        python_files = list(root.glob('**/test_*.py')) + list(root.glob('**/*_test.py'))
        if python_files:
            try:
                if 'unittest' in python_files[0].read_text():
                    test_commands.append('python -m unittest discover')
            except:
                pass  

        return test_commands[0] if test_commands else None

        


    def get_linters(self, root: Path) -> tp.Optional[str]:

        detected_linters = []
        detected_linters.extend(self._find_by_config_files(root))    
        detected_linters.extend(self._find_by_dependencies(root))
        detected_linters.extend(self._find_by_build_tools(root))
        unique_linters = list(dict.fromkeys([l for l in detected_linters if l]))
        return " && ".join(unique_linters[:3]) if unique_linters else None

    def _find_by_config_files(self, root: Path) -> list[str]:
        linters = []
    
        config_patterns = {
        '.flake8': 'flake8',
        'setup.cfg': self._check_flake8_in_setup_cfg(root),
        '.pylintrc': 'pylint',
        'pylintrc': 'pylint',
        'setup.cfg': self._check_pylint_in_setup_cfg(root),
        'pyproject.toml': self._check_black_in_pyproject(root),
        'mypy.ini': 'mypy .',
        '.mypy.ini': 'mypy .',
        'pyproject.toml': self._check_mypy_in_pyproject(root),
        '.bandit': 'bandit -r .',
        'bandit.yaml': 'bandit -r .',
        '.pydocstyle': 'pydocstyle',
        'pydocstyle.ini': 'pydocstyle'}

        for config_file, linter_command in config_patterns.items():
            config_path = root / config_file
            if config_path.exists():
                if isinstance(linter_command, str):
                    linters.append(linter_command)
                elif linter_command:  
                    linters.append(linter_command)
        
        return linters

    def _find_by_dependencies(self, root: Path) -> list[str]:
        linters = []
        linter_packages = {
            'flake8': 'flake8',
            'pylint': 'pylint', 
            'black': 'black --check .',
            'isort': 'isort --check-only .',
            'mypy': 'mypy .',
            'bandit': 'bandit -r .',
            'pydocstyle': 'pydocstyle',
            'pycodestyle': 'pycodestyle',
            'pyflakes': 'pyflakes',
        }
        dependency_files = [
            'requirements.txt',
            'requirements-dev.txt', 
            'dev-requirements.txt',
            'setup.py',
            'Pipfile',
            'pyproject.toml'
        ]
        
        for dep_file in dependency_files:
            dep_path = root / dep_file
            if dep_path.exists():
                try:
                    content = dep_path.read_text().lower()
                    for pkg, command in linter_packages.items():
                        if pkg in content:
                            linters.append(command)
                except:
                    continue  
        
        return linters

    def _find_by_build_tools(self, root: Path) -> list[str]:
        linters = []
 
        makefile_path = root / 'Makefile'
        if makefile_path.exists():
            try:
                content = makefile_path.read_text()
                if 'lint:' in content:
                    linters.append('make lint')
                elif 'flake8' in content:
                    linters.append('flake8')
                elif 'pylint' in content:
                    linters.append('pylint')
            except:
                pass  
        tox_path = root / 'tox.ini'
        if tox_path.exists():
            try:
                content = tox_path.read_text()
                if '[testenv:lint]' in content:
                    linters.append('tox -e lint')
            except:
                pass  

        precommit_path = root / '.pre-commit-config.yaml'
        if precommit_path.exists():
            linters.append('pre-commit run --all-files')

        return linters

    def _check_flake8_in_setup_cfg(self, root: Path) -> tp.Optional[str]:
        setup_cfg_path = root / 'setup.cfg'
        if setup_cfg_path.exists():
            try:
                content = setup_cfg_path.read_text()
                if '[flake8]' in content or '[tool:flake8]' in content:
                    return 'flake8'
            except:
                pass  
        return None

    def _check_pylint_in_setup_cfg(self, root: Path) -> tp.Optional[str]:
        setup_cfg_path = root / 'setup.cfg'
        if setup_cfg_path.exists():
            try:
                content = setup_cfg_path.read_text()
                if '[pylint]' in content or '[tool:pylint]' in content:
                    return 'pylint'
            except:
                pass
        return None

    def _check_black_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()
                if '[tool.black]' in content:
                    return 'black --check .'
            except:
                pass
        return None

    def _check_mypy_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()
                if '[tool.mypy]' in content:
                    return 'mypy .'
            except:
                pass  
        return None

    def detect_python_version_by_syntax(self,root) -> str: 
        version_features = {
           (3, 8): [
               'walrus_operator',        
               'positional_only_args',   
                'fstring_self_documenting' 
                ],
            (3, 9): [
                'dict_union_operators',  
                'str_remove_methods',     
                'type_hinting_generics', 
                'zoneinfo_module' 
            ],
            (3, 10): [
                'match_statement', 
                'union_operator_in_types',
                'parenthesized_context_managers'
            ],
            (3, 11): [
                'exception_group',  
                'try_star_syntax',   
                'variadic_generics', 
                'tomllib_module'  
            ],
            (3, 12): [
                'type_parameter_syntax', 
                'fstring_debugging',
                'pattern_matching_enhancements'
            ]
            }

        found_features: tp.Set[str] = set()
        py_files = list(root.glob("**/*.py"))[:30]

        for py_file in py_files:
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if ':=' in content:
                        found_features.add('walrus_operator')
                    if re.search(r'\bmatch\b.*\bcase\b', content):
                        found_features.add('match_statement')
                    if 'removeprefix' in content or 'removesuffix' in content:
                        found_features.add('str_remove_methods')
                    if re.search(r'\w+\s*\|\s*\w+', content) and any(word in content for word in ['dict', 'Dict', 'typing.Dict']):
                        found_features.add('dict_union_operators')
                    if re.search(r'def\s+\w+\(.*\)\s*->\s*[^:]+?\s*\|\s*[^:]+?:', content):
                        found_features.add('union_operator_in_types')
                    if 'except*' in content:
                        found_features.add('exception_group')
                    if re.search(r'def\s+\w+\([^)]*\/[^)]*\)', content):
                        found_features.add('positional_only_args')
                    
                except (UnicodeDecodeError, Exception):
                    continue
        min_version: Tuple[int, int] = (3, 7)
        sorted_versions = sorted(version_features.keys())
        for version in sorted_versions:
            features_in_version = version_features[version]
            if any(feature in found_features for feature in features_in_version):
                min_version = max(min_version, version)
                major, minor = min_version
        if min_version > (3, 7):
            return f"Python {major}.{minor}+"
        else:
            return "Python 3.7+"

    def _has_test_config(self, config_path: Path) -> bool:
        try:
            content = config_path.read_text()
            if config_path.name == 'pyproject.toml':
                return '[tool.pytest]' in content or '[tool.pytest.ini_options]' in content
            elif config_path.name == 'setup.cfg':
                return '[tool:pytest]' in content or ('[aliases]' in content and 'test' in content)
            elif config_path.name == 'tox.ini':
                return '[pytest]' in content or '[testenv]' in content
            return True
        except:
            return False























