import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek.models import Service
import Array

class PythonAnalyze(BaseAnalyzer):

    def analyze(self, root: Path) -> tp.Optional[Service]:
        return Service(

            name=self.get_repo_name(root),
            language=self.detect_language(root),
            #На подумать
            version=self.detect_python_version_by_syntax(root),
            dependencies=self.get_dependencies(root),
            packet_managers = self.get_packet_managers(root),
            libs=self.get_libs(root),
            config=self.get_config(root),
            detected_docker=self.get_docker(root),
            detected_entrypoint=self.get_entrypoint(root),
            detected_tests=self.get_tests(root),
            detected_linters=self.get_linters(root)
            )
    
    def get_repo_name(self, root) -> str:   
        try:
            return root.name
        except:  #Типа если файл заканчивается "\" 
            return normalized_path.name

    def detect_language(self, root) -> str:
        language_indicators = {".py": "python"}
            for repofile in root.iterdir():
                if repofile.is_file():
            normalized_path = root.resolve(
                    if repofile.suffix in language_indicators:
                        return language_indicators[repofile.suffix])
            return "Unknown""  

    #Зависимости
    def get_dependencies(self, root) -> list[str]:
        dependencies = []  #list

        setup_file = root / "setup.py" #Я не нашел, как он может называться по-другому, и вроде один файл на репо
        if setup_file.exists():
            dependencies.append("setup.py")

        toml_file = root / "pyproject.toml" #Я не нашел, как он может называться по-другому, и вроде один файл на репо
        if toml_file.exists():
            dependencies.append("pyproject.toml")

        req_files = list(root.glob("requirements*.txt"))
        for file in req_files:
            dependencies.append(file.name)

        return dependencies

    def get_packet_managers(self, root) -> str:
         managers = []
        validators = [
            self._is_poetry_project,
            self._is_pipenv_project, 
            self._is_pdm_project,
            self._is_rye_project,
            self._is_hatch_project,
            self._is_uv_project,
            self._is_setuptools_project,
            self._is_requirements_project
        ]
        
        for validator in validators:
            manager = validator(root)
            if manager:
                managers.append(manager)
        
        return managers

    def _is_poetry_project(self, root: Path) -> str:
        if (root / 'poetry.lock').exists():
            return 'poetry'
  
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text()
            if '[tool.poetry]' in content:
                return 'poetry'
        return None

    def _is_pipenv_project(self, root: Path) -> str:
        if (root / 'Pipfile').exists():
            return 'pipenv'
        return None

    def _is_pdm_project(self, root: Path) -> str:
        if (root / 'pdm.lock').exists() or (root / 'pdm.toml').exists():
            return 'pdm'
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text()
            if '[tool.pdm]' in content:
                return 'pdm'
        return None

    def _is_rye_project(self, root: Path) -> str:
        if (root / 'requirements.lock').exists() or (root / 'rye.toml').exists():
            return 'rye'
        return None

    def _is_hatch_project(self, root: Path) -> str:
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text()
            if '[tool.hatch]' in content:
                return 'hatch'
        return None

    def _is_uv_project(self, root: Path) -> str:
        if (root / 'uv.lock').exists():
            return 'uv'
        return None

    def _is_setuptools_project(self, root: Path) -> str:
        if (root / 'setup.py').exists() or (root / 'setup.cfg').exists():
            return 'setuptools'
        return None

    def _is_requirements_project(self, root: Path) -> str:
        requirements_files = list(root.glob('requirements*.txt'))
        if requirements_files and not self._has_modern_package_manager(root):
            return 'pip-requirements'
        return None

    def _has_modern_package_manager(self, root: Path) -> bool:
        modern_indicators = [
            'pyproject.toml', 'poetry.lock', 'Pipfile', 
            'pdm.lock', 'requirements.lock', 'uv.lock'
        ]
        return any((root / indicator).exists() for indicator in modern_indicators)



    #библитеки импорта
    def get_libs(self, root) -> list[str]:
        libraries = []
        req_files = list(root.glob("**/requirements*.txt")) #Тут нашел альтернативы, звёздочкой вроде их учитываю, может в папках разных храниться
        for file in req_files:
            with open(file, "r", encoding='utf-8') as f:
                libraries.extend(line.strip() for line in f if line.strip() and not line.startswith("#") and not line.startswith("-r") and not line.startswith("--") and not line.startswith("-f"))
        return libraries
  
    #сторонние файлы
    def get_config(self, root) -> list[str]:
        config_files: tp.Set[str] = set() 
        patterns = ['**/*.cfg', '**/*.ini', '**/*.yml', '**/*.yaml', '**/.env*', '**/config/*']
        for key in patterns:
            for file in root.glob(key):
                if file.is_file():
                    config_files.add(file.name)
        return list(config_files)

    def get_docker(self, root) -> str:
        for docker_file in root.glob("**/Dockerfile*"):
            return str(docker_file)
        for compose_file in root.glob("**/docker-compose*.yml"):
            return str(compose_file)
        return None
    #Надо сделать dockerfile, если его нет
    
    def get_entrypoint(self, root) -> str:

        entrypoints = [
            "main.py",
            "app.py", 
            "run.py",
            "manage.py",  
            "wsgi.py",    
            "asgi.py",   
            "application.py",
            root.name + ".py",  
        ] 
        for candidate in entrypoints:
            candidate_file = root / candidate
            if candidate_file.exists():
                with open(candidate_file, "r", encoding='utf-8') as f:
                    content = f.read()
                    if "if __name__ == '__main__':" in content:
                        return str(candidate_file)
                    elif any(keyword in content for keyword in ["main()", "app.run", "manage.run", "execute"]):
                        return str(candidate_file)
    
        return ""

    #Пока не понимаю, как из setup.py достать, это заносить не буду, entrypoints
    #setup_file = root / "setup.py"
    #if setup_file.exists():
        #with open(setup_file, "r", encoding='utf-8') as f:
            #content = f.read()
            #if "console_scripts" in content:    
                # Упрощенный парсинг - ищем шаблон типа "name=module:function"
                #import re
                #matches = re.findall(r'console_scripts\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
                #if matches:
                    # Берем первый скрипт из console_scripts
                #    scripts = re.findall(r'"([^"]+)"', matches[0])
                #    if scripts:
                #        script_def = scripts[0].split('=')
                #        if len(script_def) == 2:
                #            module_path = script_def[1].split(':')[0]
                #        return f"{module_path.replace('.', '/')}.py"  

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
            content = setup_py.read_text()
            if 'test_suite' in content or 'pytest' in content:
                test_commands.append('python setup.py test')
        test_dirs = ['tests', 'test', 'spec']
        for test_dir in test_dirs:
            if (root / test_dir).exists():
                test_commands.append('pytest')
                break

        makefile = root / 'Makefile'
        if makefile.exists():
            content = makefile.read_text()
            if 'test:' in content or 'pytest' in content:
                test_commands.append('make test')

        tox_ini = root / 'tox.ini'
        if tox_ini.exists():
            content = tox_ini.read_text()
            if '[testenv]' in content:
                test_commands.append('tox')
                
        python_files = list(root.glob('**/test_*.py')) + list(root.glob('**/*_test.py'))
        if python_files and 'unittest' in str(python_files[0].read_text()):
            test_commands.append('python -m unittest discover')

        return test_commands[0] if test_commands else None #Команда по запуску теста
        


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
        # Flake8
        '.flake8': 'flake8',
        'setup.cfg': self._check_flake8_in_setup_cfg(root),
        
        # Pylint
        '.pylintrc': 'pylint',
        'pylintrc': 'pylint',
        'setup.cfg': self._check_pylint_in_setup_cfg(root),
        
        # Black
        'pyproject.toml': self._check_black_in_pyproject(root),
        
        # MyPy
        'mypy.ini': 'mypy .',
        '.mypy.ini': 'mypy .',
        'pyproject.toml': self._check_mypy_in_pyproject(root),
        
        # Bandit
        '.bandit': 'bandit -r .',
        'bandit.yaml': 'bandit -r .',
        
        # Pydocstyle
        '.pydocstyle': 'pydocstyle',
        'pydocstyle.ini': 'pydocstyle',
        }
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
                content = dep_path.read_text().lower()
                for pkg, command in linter_packages.items():
                    if pkg in content:
                        linters.append(command)
        
        return linters

    def _find_by_build_tools(self, root: Path) -> list[str]:
        linters = []
        makefile_path = root / 'Makefile'
        if makefile_path.exists():
            content = makefile_path.read_text()
            if 'lint:' in content:
                linters.append('make lint')
            elif 'flake8' in content:
                linters.append('flake8')
            elif 'pylint' in content:
                linters.append('pylint')
        tox_path = root / 'tox.ini'
        if tox_path.exists():
            content = tox_path.read_text()
            if '[testenv:lint]' in content:
                linters.append('tox -e lint')

        precommit_path = root / '.pre-commit-config.yaml'
        if precommit_path.exists():
            linters.append('pre-commit run --all-files')

        return linters


    def _check_flake8_in_setup_cfg(self, root: Path) -> str:
        
        setup_cfg_path = root / 'setup.cfg'
        if setup_cfg_path.exists():
            content = setup_cfg_path.read_text()
            if '[flake8]' in content or '[tool:flake8]' in content:
                return 'flake8'
        return None

    def _check_pylint_in_setup_cfg(self, root: Path) -> tp.Optional[str]:
        setup_cfg_path = root / 'setup.cfg'
        if setup_cfg_path.exists():
            content = setup_cfg_path.read_text()
            if '[pylint]' in content or '[tool:pylint]' in content:
                return 'pylint'
        return None

    def _check_black_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / 'pyproject.toml'
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if '[tool.black]' in content:
                return 'black --check .'
        return None

    def _check_mypy_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / 'pyproject.toml'
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if '[tool.mypy]' in content:
                return 'mypy .'
        return None

# !*! на обсуждение
    def detect_python_version_by_syntax(self,root) -> str:
 
        #Для обсуждения, взял, на мой взгляд, самый действующий вариант для поиска версии
        version_features = {
           (3, 8): [
               'walrus_operator',        # Оператор := (моржовый оператор)
               'positional_only_args',   # Позиционные аргументы с /
                'fstring_self_documenting' # f-строки с = для отладки
                ],
            (3, 9): [
                'dict_union_operators',   # Операторы | и |= для словарей
                'str_remove_methods',     # Методы removeprefix() и removesuffix()
                'type_hinting_generics',  # Встроенная поддержка generic в типах
                'zoneinfo_module'         # Модуль zoneinfo (косвенный признак)
            ],
            (3, 10): [
                'match_statement',        # Структурное сопоставление (match/case)
                'union_operator_in_types', # Оператор | в аннотациях типов
                'parenthesized_context_managers' # Менеджеры контекста в скобках
            ],
            (3, 11): [
                'exception_group',        # Группы исключений и except*
                'try_star_syntax',        # Синтаксис try* для асинхронных исключений
                'variadic_generics',      # Вариативные дженерики
                'tomllib_module'          # Модуль tomllib (косвенный признак)
            ],
            (3, 12): [
                'type_parameter_syntax',  # Новый синтаксис параметров типов
                'fstring_debugging',      # Улучшенная отладка f-строк
                'pattern_matching_enhancements' # Улучшения в match/case
            ]
        }

        found_features: tp.Set[str] = set()

        for py_file in root.glob("**/*.py"):
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
    content = config_path.read_text()
    if config_path.name == 'pyproject.toml':
        return '[tool.pytest]' in content or '[tool.pytest.ini_options]' in content
    elif config_path.name == 'setup.cfg':
        return '[tool:pytest]' in content or '[aliases]' in content and 'test' in content 
    elif config_path.name == 'tox.ini':
        return '[pytest]' in content or '[testenv]' in content 
    return True 























