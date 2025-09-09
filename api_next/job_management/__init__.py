# Copyright (c) 2025, API Next and contributors
# For license information, please see license.txt

"""
Job Management Module

This module contains DocTypes and business logic for job order management,
including workflow state machines, phase tracking, and resource allocation.
"""

from . import workflow

__all__ = ["workflow"]