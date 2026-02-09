"""Tests for error handling utilities: validation helpers and exception handlers."""

import pytest
from fastapi import HTTPException

from ralf_spike_2.errors import (
    DuplicateTitleError,
    TodoNotFoundError,
    validate_path_id,
    validate_title,
)


class TestValidatePathId:
    """Tests for validate_path_id()."""

    def test_valid_positive_integer(self) -> None:
        """validate_path_id('3') returns 3."""
        assert validate_path_id("3") == 3

    def test_rejects_non_numeric(self) -> None:
        """validate_path_id('abc') raises 422 with correct message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("abc")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "id must be a positive integer"

    def test_rejects_zero(self) -> None:
        """validate_path_id('0') raises 422 (not positive)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("0")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "id must be a positive integer"

    def test_rejects_negative(self) -> None:
        """validate_path_id('-1') raises 422."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("-1")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "id must be a positive integer"

    def test_accepts_large_positive(self) -> None:
        """validate_path_id('999') returns 999."""
        assert validate_path_id("999") == 999

    def test_rejects_float_string(self) -> None:
        """validate_path_id('3.5') raises 422."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("3.5")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "id must be a positive integer"


class TestValidateTitle:
    """Tests for validate_title()."""

    def test_trims_whitespace(self) -> None:
        """validate_title('  hello  ') returns 'hello'."""
        assert validate_title("  hello  ") == "hello"

    def test_rejects_empty_string(self) -> None:
        """validate_title('') raises 422 with 'title must not be blank'."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "title must not be blank"

    def test_rejects_whitespace_only(self) -> None:
        """validate_title('   ') raises 422 with 'title must not be blank'."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("   ")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "title must not be blank"

    def test_rejects_too_long(self) -> None:
        """validate_title('a' * 501) raises 422 with length message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("a" * 501)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "title must be 500 characters or fewer"

    def test_accepts_exactly_500(self) -> None:
        """validate_title('a' * 500) returns the title (boundary)."""
        result = validate_title("a" * 500)
        assert len(result) == 500

    def test_accepts_normal_title(self) -> None:
        """validate_title('Buy milk') returns 'Buy milk'."""
        assert validate_title("Buy milk") == "Buy milk"

    def test_length_check_uses_trimmed_value(self) -> None:
        """Length check applies to the trimmed value, not the original."""
        # 500 chars + surrounding whitespace should succeed
        padded = "  " + "a" * 500 + "  "
        result = validate_title(padded)
        assert len(result) == 500


class TestTodoNotFoundError:
    """Tests for TodoNotFoundError."""

    def test_status_code_404(self) -> None:
        """TodoNotFoundError has status code 404."""
        error = TodoNotFoundError()
        assert error.status_code == 404

    def test_detail_message(self) -> None:
        """TodoNotFoundError has correct detail message."""
        error = TodoNotFoundError()
        assert error.detail == "Todo not found"


class TestDuplicateTitleError:
    """Tests for DuplicateTitleError."""

    def test_status_code_409(self) -> None:
        """DuplicateTitleError has status code 409."""
        error = DuplicateTitleError()
        assert error.status_code == 409

    def test_detail_message(self) -> None:
        """DuplicateTitleError has correct detail message."""
        error = DuplicateTitleError()
        assert error.detail == "A todo with this title already exists"


class TestErrorResponseFormat:
    """Tests that all errors use the {"detail": "..."} format."""

    def test_validate_path_id_format(self) -> None:
        """validate_path_id error uses detail string format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("abc")
        assert isinstance(exc_info.value.detail, str)

    def test_validate_title_blank_format(self) -> None:
        """validate_title blank error uses {"detail": "..."} format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("")
        assert isinstance(exc_info.value.detail, str)

    def test_validate_title_length_format(self) -> None:
        """validate_title length error uses {"detail": "..."} format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("a" * 501)
        assert isinstance(exc_info.value.detail, str)

    def test_not_found_format(self) -> None:
        """TodoNotFoundError uses {"detail": "..."} format."""
        error = TodoNotFoundError()
        assert isinstance(error.detail, str)

    def test_duplicate_format(self) -> None:
        """DuplicateTitleError uses {"detail": "..."} format."""
        error = DuplicateTitleError()
        assert isinstance(error.detail, str)

    def test_only_one_error_per_request(self) -> None:
        """Each error raises a single exception with a single string detail."""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("abc")
        # detail should be a plain string, not a list or array
        assert not isinstance(exc_info.value.detail, list)
        assert isinstance(exc_info.value.detail, str)


class TestValidationOrder:
    """Tests for validation order enforcement.

    The validation order is: missing -> type -> blank -> length -> uniqueness.
    These tests verify the helper functions enforce their respective priorities.
    Comprehensive validation-order integration tests will be in the endpoint tests.
    """

    def test_blank_takes_priority_over_length(self) -> None:
        """An empty string is 'blank' not 'too long' (blank before length)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("")
        assert exc_info.value.detail == "title must not be blank"

    def test_whitespace_is_blank_not_length(self) -> None:
        """A whitespace-only string is 'blank' not a length issue."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("   ")
        assert exc_info.value.detail == "title must not be blank"
