from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from employee_app.config import get_min_salary, load_config
from employee_app.exceptions import ConfigurationError

VALID = ("departments:\n  it: Інформаційні технології\n  HR: Персонал\n"
         "min_salary: 8000\ncurrency: uah\n")


def test_load_valid_config(write_file: Callable[[str, str], Path]) -> None:
    config = load_config(write_file("config.yaml", VALID))
    assert config.departments == {"IT": "Інформаційні технології", "HR": "Персонал"}
    assert config.min_salary == pytest.approx(8_000)
    assert config.max_salary == pytest.approx(1_000_000)  # default
    assert config.currency == "UAH"
    assert config.skip_invalid is True


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found") as exc_info:
        load_config(tmp_path / "absent.yaml")
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_invalid_yaml_keeps_original_cause(write_file: Callable[[str, str], Path]) -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(write_file("bad.yaml", "departments: [IT"))
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("min_salary: 1\n", id="no-departments"),
        pytest.param("departments: {}\nmin_salary: 1\n", id="empty-departments"),
        pytest.param("departments: [IT, HR]\nmin_salary: 1\n", id="departments-not-mapping"),
        pytest.param("departments: {IT: IT}\n", id="no-min-salary"),
        pytest.param("departments: {IT: IT}\nmin_salary: -1\n", id="negative-min-salary"),
        pytest.param("departments: {IT: IT}\nmin_salary: 10\nmax_salary: 10\n",
                     id="min-equals-max"),
        pytest.param("departments: {IT: IT}\nmin_salary: lots\n", id="non-numeric-min"),
        pytest.param("departments: {IT: IT}\nmin_salary: 1\ncurrency: HRYVNIA\n",
                     id="bad-currency"),
    ],
)
def test_invalid_configuration(write_file: Callable[[str, str], Path], text: str) -> None:
    with pytest.raises(ConfigurationError):
        load_config(write_file("config.yaml", text))


def test_min_salary_from_environment(monkeypatch: pytest.MonkeyPatch,
                                     write_file: Callable[[str, str], Path]) -> None:
    monkeypatch.setenv("EMPLOYEE_MIN_SALARY", "15000")
    assert get_min_salary(8_000) == 15_000
    assert load_config(write_file("config.yaml", VALID)).min_salary == 15_000


def test_invalid_min_salary_in_environment(monkeypatch: pytest.MonkeyPatch,
                                           write_file: Callable[[str, str], Path]) -> None:
    monkeypatch.setenv("EMPLOYEE_MIN_SALARY", "abc")
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(write_file("config.yaml", VALID))
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_default_min_salary_without_environment() -> None:
    assert get_min_salary(8_000) == 8_000
