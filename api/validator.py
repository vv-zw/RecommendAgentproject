# api/validator.py
from typing import Tuple, Dict, Any

def validate_recommend_request(data: Any) -> Tuple[bool, str]:
    """
    Validates the incoming request data for the recommend endpoint.
    :param data: The parsed JSON data from the request.
    :return: A tuple containing a boolean (True if valid) and an error message string.
    """
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object."

    # Check for user_id
    if "user_id" not in data:
        return False, "Missing required field: user_id."

    # Check for query
    if "query" not in data or not data["query"]:
        return False, "Missing or empty required field: query."
    
    if not isinstance(data["query"], str):
        return False, "Field 'query' must be a string."

    # Check for context
    if "context" not in data or not isinstance(data.get("context"), dict):
        return False, "Missing or invalid field: context must be an object."

    return True, ""

if __name__ == '__main__':
    print("--- Testing validator.py ---")
    
    # Test cases
    valid_case = {"user_id": 1, "query": "hello", "context": {}}
    missing_query_case = {"user_id": 1, "context": {}}
    invalid_context_case = {"user_id": 1, "query": "hello", "context": []}
    not_a_dict_case = []

    print(f"Valid case: {validate_recommend_request(valid_case)}")
    print(f"Missing query: {validate_recommend_request(missing_query_case)}")
    print(f"Invalid context: {validate_recommend_request(invalid_context_case)}")
    print(f"Not a dict: {validate_recommend_request(not_a_dict_case)}")
