"""Tests for memory/ — SQLite persistence layer (Kevin).

Covers: baseline read/write, shift history append, get_recent_frames, get_all_frames,
baseline update at shift end, cold-start default baseline.

Owner: Josh (fixtures) / Kevin (test cases)
Imports from: core.models, memory.*
"""
