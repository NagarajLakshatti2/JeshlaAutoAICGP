"""Deterministic routing and tool-exposure rules, independent of providers and UI.

Policy modules do not open databases or call models. Legacy module paths remain
available as aliases while callers migrate incrementally.
"""
