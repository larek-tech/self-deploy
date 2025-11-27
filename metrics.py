from larek.commands import analyze
from larek import models
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Metrics:
    def __init__(self):
        self.language_metrics = {}
        self.dockerfile_metrics = {}
        self.config_metrics = {}
        self.entrypoint_metrics = {}


def calculate_metrics(expected: set, actual: set) -> dict:
    """Рассчитать precision, recall и f1"""
    tp = len(expected & actual)
    fp = len(actual - expected)
    fn = len(expected - actual)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    if len(expected) == 0 and len(actual) == 0:
        precision = 1.0
        recall = 1.0
        f1 = 1.0

    return {"precision": precision, "recall": recall, "f1": f1}


def compare(repo_path: Path, res: models.RepoSchema) -> Metrics:
    """Сравнить результаты анализа с ожидаемыми значениями и вернуть метрики."""

    metrics = Metrics()

    expected_langs = {repo_path.parent.name}
    actual_langs = {lang.name for service in res.services for lang in [service.lang]}
    metrics.language_metrics = calculate_metrics(expected_langs, actual_langs)

    expected_dockerfiles = {
        f"sample/{repo_path.parent.name}/" + str(file.relative_to(repo_path.parent))
        for file in repo_path.rglob("*")
        if file.is_file() and "Dockerfile" in file.name
    }
    actual_dockerfiles = {
        df for service in res.services for df in service.docker.dockerfiles
    }
    if len(expected_dockerfiles) > 0:
        print(expected_dockerfiles)
        print(actual_dockerfiles)
    metrics.dockerfile_metrics = calculate_metrics(
        expected_dockerfiles, actual_dockerfiles
    )

    expected_configs = {
        f"sample/{repo_path.parent.name}/" + str(file.relative_to(repo_path.parent))
        for file in repo_path.rglob("*")
        if file.is_file()
        and file.suffix in {".yaml", ".yml", ".json", ".ini", ".cfg", ".conf"}
        and file.name != "report.yaml"
    }
    actual_configs = {cfg.path for service in res.services for cfg in service.configs}
    metrics.config_metrics = calculate_metrics(expected_configs, actual_configs)

    expected_entrypoints = {
        f"sample/{repo_path.parent.name}/" + str(file.relative_to(repo_path.parent))
        for file in repo_path.rglob("*")
        if file.is_file()
        and (
            "main" in file.name.lower()
            or "app" in file.name.lower()
            or "index" in file.name.lower()
        )
    }
    actual_entrypoints = {ep for service in res.services for ep in service.entrypoints}
    metrics.entrypoint_metrics = calculate_metrics(
        expected_entrypoints, actual_entrypoints
    )

    return metrics


def main():
    repos_base_path = Path("sample/")
    metrics = []
    for lang_dir in repos_base_path.iterdir():
        if lang_dir.is_dir():
            for repo_dir in lang_dir.iterdir():
                if repo_dir.is_dir():
                    print(f"Анализируем репозиторий {repo_dir}.")
                    try:
                        res = analyze.analyze(str(repo_dir))
                    except Exception as e:
                        print(f"Ошибка при анализе репозитория {repo_dir}: {e}")
                        continue
                    metrics.append(compare(repo_dir, res))

    res = Metrics()
    n = len(metrics)
    for m in metrics:
        for key, value in m.language_metrics.items():
            res.language_metrics[key] = round(
                res.language_metrics.get(key, 0) + value / n, 3
            )
        for key, value in m.dockerfile_metrics.items():
            res.dockerfile_metrics[key] = round(
                res.dockerfile_metrics.get(key, 0) + value / n, 3
            )
        for key, value in m.config_metrics.items():
            res.config_metrics[key] = round(
                res.config_metrics.get(key, 0) + value / n, 3
            )
        for key, value in m.entrypoint_metrics.items():
            res.entrypoint_metrics[key] = round(
                res.entrypoint_metrics.get(key, 0) + value / n, 3
            )

    print("Средние метрики по всем репозиториям:")
    print("Языки программирования:", res.language_metrics)
    print("Dockerfile:", res.dockerfile_metrics)
    print("Конфигурационные файлы:", res.config_metrics)
    print("Точки входа:", res.entrypoint_metrics)


if __name__ == "__main__":
    main()
