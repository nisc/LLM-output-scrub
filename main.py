"""
Main entry point for LLM Output Scrub macOS app.
This module launches the GUI application using rumps.
"""

from llm_output_scrub.llm_output_scrub import LLMOutputScrub

if __name__ == "__main__":
    LLMOutputScrub().run()
