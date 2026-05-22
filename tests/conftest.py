"""Pytest setup: put the engine module on sys.path so we can test it in
isolation without importing the rest of the integration (which depends on
Home Assistant).
"""
import os
import sys

ENGINE_PARENT = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "dynamic_tariff_savings"
)
sys.path.insert(0, os.path.abspath(ENGINE_PARENT))
