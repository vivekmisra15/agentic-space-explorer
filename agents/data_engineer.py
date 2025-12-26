# agents/data_engineer.py

from __future__ import annotations  # Enables forward references for type hints (Python 3.7+ compatibility)

import time
from typing import Any, Dict, Optional

# Import shared logging and state management utilities
from core.state import log_event, update_state

# Import domain-specific data processing tools
from tools.data_tools import load_space_missions, derive_features


class DataEngineerAgent:
    """
    The DataEngineerAgent is responsible for preparing datasets so that other
    agents (e.g., analysts or machine learning components) can work with them.
    
    It performs two key tasks in sequence:
      1. Loads raw space mission data (from a remote or local source)
      2. Derives additional features or cleans the dataset for enriched analysis
    
    After each step, it updates the shared state to keep track of data files
    and progress throughout the pipeline.
    """

    def __init__(self, local_filename: str = "space_missions.csv"):
        # Initialize the agent with a default filename for local storage.
        # This file serves as the base source for raw CSV data.
        self.local_filename = local_filename

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the data engineering pipeline.
        
        Args:
            state: A shared state dictionary that tracks progress, outputs, and logs.
        
        Returns:
            Updated state dictionary containing paths to raw and enriched datasets.
        """
        start = time.time()  # Measure execution time for performance tracking

        # Log that the agent has started running
        log_event(
            state,
            "agent.start",
            {"agent": "DataEngineerAgent"},
        )

        # --- Step 1: Load raw space mission data -------------------------------
        log_event(
            state,
            "tool.start",
            {"tool": "load_space_missions", "local_filename": self.local_filename},
        )
        # The tool downloads or reads the raw dataset and returns the file path
        raw_csv_path = load_space_missions(local_filename=self.local_filename)
        log_event(
            state,
            "tool.end",
            {"tool": "load_space_missions", "output": raw_csv_path},
        )

        # Record the path of the raw dataset in the shared state.
        update_state(
            state,
            {"raw_csv_path": raw_csv_path},
            reason="data.load",  # Used for contextual log messages
        )

        # --- Step 2: Derive and enrich features --------------------------------
        log_event(
            state,
            "tool.start",
            {"tool": "derive_features", "input": raw_csv_path},
        )
        # This tool processes the raw CSV (e.g., adds computed columns, cleans data)
        enriched_csv_path = derive_features(raw_csv_path)
        log_event(
            state,
            "tool.end",
            {"tool": "derive_features", "output": enriched_csv_path},
        )

        # Record the path of the enriched dataset in the shared state.
        update_state(
            state,
            {"enriched_csv_path": enriched_csv_path},
            reason="data.enrich",
        )

        # --- Finalize agent run ------------------------------------------------
        elapsed_ms = int((time.time() - start) * 1000)
        log_event(
            state,
            "agent.end",
            {"agent": "DataEngineerAgent", "elapsed_ms": elapsed_ms},
        )

        # Return the updated state to downstream components or other agents
        return state
