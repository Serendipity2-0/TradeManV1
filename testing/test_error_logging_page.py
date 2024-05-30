import pytest
import os
import tempfile
import sys
from unittest.mock import patch, mock_open

# Get the directory of the current test file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the project root directory (parent directory of the current directory)
project_root = os.path.abspath(os.path.join(current_dir, ".."))

# Add the project root directory to sys.path
sys.path.append(project_root)

from Executor.ExecutorDashBoard.error_logging_page import (
    extract_error_details_with_timestamp,
    read_n_process_err_log,
)


# Mock the LoggerSetup
@pytest.fixture
def mock_logger_setup():
    with patch(
        "Executor.ExecutorDashBoard.error_logging_page.LoggerSetup"
    ) as MockLogger:
        mock_logger = MockLogger()
        yield mock_logger


# Test for extract_error_details_with_timestamp
@pytest.mark.parametrize(
    "line, expected_output",
    [
        (
            "2024-05-30 12:00:00.123 | ERROR    | module.path:Something - An error occurred",
            ("2024-05-30 12:00:00.123", "path", "An error occurred"),
        ),
        (
            "2024-05-30 12:00:00.123 | ERROR    | module.path.submodule:Something - Another error",
            ("2024-05-30 12:00:00.123", "submodule", "Another error"),
        ),
        (
            "2024-05-30 12:00:00.123 | INFO     | module.path:Something - Not an error",
            (None, None, None),
        ),
        ("Invalid log line", (None, None, None)),
    ],
)
def test_extract_error_details_with_timestamp(line, expected_output, mock_logger_setup):
    assert extract_error_details_with_timestamp(line) == expected_output


# Test for read_n_process_err_log
def test_read_n_process_err_log(mock_logger_setup):
    mock_error_log_content = (
        "2024-05-30 12:00:00.123 | ERROR    | module.path:Something - An error occurred\n"
        "2024-05-30 12:00:01.123 | ERROR    | module.path.submodule:Something - Another error\n"
    )

    with patch("builtins.open", mock_open(read_data=mock_error_log_content)):
        with tempfile.NamedTemporaryFile(
            delete=False
        ) as tmp_error_log, tempfile.NamedTemporaryFile(delete=False) as tmp_error_csv:

            error_log_path = tmp_error_log.name
            error_log_csv_path = tmp_error_csv.name

            with patch.dict(
                os.environ,
                {
                    "ERROR_LOG_PATH": error_log_path,
                    "ERROR_LOG_CSV_PATH": error_log_csv_path,
                },
            ):
                result_df = read_n_process_err_log()

                assert not result_df.empty
                assert "Timestamp" in result_df.columns
                assert "Module" in result_df.columns
                assert "Error" in result_df.columns
                assert "Count" in result_df.columns

                assert result_df.iloc[0]["Error"] == "Another error"
                assert result_df.iloc[1]["Error"] == "An error occurred"

                with open(error_log_csv_path, "r") as f:
                    csv_content = f.read()
                    assert "Timestamp,Module,Error,Count" in csv_content
                    assert "An error occurred" in csv_content
                    assert "Another error" in csv_content
