"""Pytest setup: put the integration module on sys.path so we can test the
counterfactual engine in isolation without importing the rest of the
integration (which depends on Home Assistant).
"""
import os
import sys

INTEGRATION_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "dynamic_tariff_savings"
)
sys.path.insert(0, os.path.abspath(INTEGRATION_DIR))
