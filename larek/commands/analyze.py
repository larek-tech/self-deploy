import pathlib
from larek.analyzer import repo, go, java, kotlin, javascript, python
from larek import models
import pydantic_yaml


def analyze(repo_path_raw: str) -> models.RepoSchema:
    # переходим в директорию с репозиторием и генерируем отчет + build.yaml
    repo_path = pathlib.Path(repo_path_raw)
    repo_analyzer = repo.RepoAnalyzer()

    repo_analyzer.register_analyzer(go.GoAnalyzer)
    repo_analyzer.register_analyzer(java.JavaAnalyzer)
    repo_analyzer.register_analyzer(kotlin.KotlinAnalyzer)
    repo_analyzer.register_analyzer(javascript.JavaScriptAnalyzer)
    repo_analyzer.register_analyzer(python.PythonAnalyze)

    res = repo_analyzer.analyze(repo_path)

    # сохраняй отчет в формате YAML в файл report.yaml result/lang/repo.yaml
    report_path = repo_path / "report.yaml"
    pydantic_yaml.to_yaml_file(report_path, res)

    return res
