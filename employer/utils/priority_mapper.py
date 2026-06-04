# utils/priority_mapper.py
import logging

logger = logging.getLogger(__name__)

PRIORITY_MAPPING = {
    'High': 0.35,
    'Medium': 0.20,
    'Low': 0.10,
    'None': 0.05
}

def map_priorities_to_weights(priorities):
    """
    Maps priority levels to normalized weights for job evaluation criteria.

    Args:
        priorities (dict): Dictionary with keys (skills, experience, etc.) and values (High, Medium, Low, None).

    Returns:
        tuple: (weights, error_message)
            - weights (dict): Normalized weights for each criterion.
            - error_message (str): Error message if validation fails, else empty string.
    """
    required_keys = {'skills', 'experience', 'education', 'projects', 'soft_skills', 'additional_info'}
    if set(priorities.keys()) != required_keys:
        logger.error(f"Missing or extra priority keys: {required_keys}")
        return None, f"Missing or extra priority keys: {required_keys}"
    
    high_count = sum(1 for p in priorities.values() if p == 'High')
    if high_count == 0:
        logger.error("At least one component must have High priority")
        return None, "At least one component must have High priority"
    
    weights = {}
    for key, priority in priorities.items():
        if priority not in PRIORITY_MAPPING:
            logger.error(f"Invalid priority for {key}: {priority}")
            return None, f"Invalid priority for {key}: {priority}"
        weights[key] = PRIORITY_MAPPING[priority]
        
    total = sum(weights.values())
    if total == 0:
        logger.error("All weights are zero")
        return None, "All weights are zero"
        
    weights = {k: v / total for k, v in weights.items()}
    
    for key, value in weights.items():
        if not (0.05 <= value <= 0.40):
            logger.error(f"Weight for {key} ({value:.2f}) must be between 0.05 and 0.40")
            return None, f"Weight for {key} ({value:.2f}) must be between 0.05 and 0.40"
    
    return weights, ""