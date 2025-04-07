"""
Common path definitions for ArxivDigest-extra.
This module provides consistent paths throughout the application.
"""
import os

# Get the project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define common directories
DATA_DIR = os.path.join(ROOT_DIR, "data")
DIGEST_DIR = os.path.join(ROOT_DIR, "digest")
SRC_DIR = os.path.join(ROOT_DIR, "src")

# Create directories if they don't exist
for directory in [DATA_DIR, DIGEST_DIR]:
    os.makedirs(directory, exist_ok=True)