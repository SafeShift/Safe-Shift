"""Tests for actions/ — action handlers and integration clients (Kevin + Emilio).

Covers: alert/rest_break/phone_notify handler dispatch, rest_finder Nominatim query,
alerting_client payload, notify_client ntfy push, logging_client JSONL write.
External HTTP calls are mocked.

Owner: Josh (fixtures) / Kevin + Emilio (test cases)
Imports from: core.models, actions.*
"""
