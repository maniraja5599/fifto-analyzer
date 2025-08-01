from celery import shared_task
from . import utils
import time

@shared_task
def generate_analysis_task(instrument_name, calculation_type, selected_expiry_str):
    """
    Celery task for generating analysis in the background.
    This prevents the UI from hanging during long-running operations.
    """
    try:
        return utils.generate_analysis(instrument_name, calculation_type, selected_expiry_str)
    except Exception as e:
        return None, f"Error in analysis task: {str(e)}"
