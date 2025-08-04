#!/usr/bin/env python
"""
Script to run LangSmith evaluations on the Zalo bot agent.
This can be scheduled to run periodically to evaluate agent performance.
"""

import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.smith import RunEvalConfig
from services.advisor import agent_advisor
from services.config import is_langsmith_configured, LANGCHAIN_PROJECT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evaluation():
    """Run evaluation on recent agent runs"""
    if not is_langsmith_configured():
        logger.error("LangSmith is not configured. Please set up your environment variables.")
        return False
    
    try:
        # Create evaluation config
        eval_config = RunEvalConfig(
            evaluators=[
                "qa",  # Evaluates question answering
                "criteria",  # Custom criteria
            ],
            custom_evaluators=[],
            eval_llm="gpt-4"  # Use a strong model for evaluation
        )
        
        # Run evaluation
        agent_advisor.run_evaluation(eval_config)
        logger.info(f"Evaluation started for project {LANGCHAIN_PROJECT}")
        return True
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        return False

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1) 