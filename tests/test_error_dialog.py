"""Test for ErrorDialog exception handling and redaction."""

import sys
from app.ui.dialogs.error_dialog import ErrorDialog


def test_error_dialog_traceback_redaction(qtbot):
    try:
        raise ValueError("Secret failure with token ghp_1234567890abcdef and uuid 12345678-1234-4234-8234-123456789abc")
    except ValueError as e:
        exc_type, exc_val, exc_tb = sys.exc_info()
        dialog = ErrorDialog(exc_type, exc_val, exc_tb)
        qtbot.addWidget(dialog)

        # Verify credentials redacted in dialog text
        assert "ghp_" not in dialog.error_text
        assert "[REDACTED-TOKEN]" in dialog.error_text
        assert "[REDACTED-UUID]" in dialog.error_text
        assert "Secret failure" in dialog.error_text
