def convert to_dict(data):
    """
    Convert the input data to a dictionary format.

    Args:
        data: The input data to be converted.

    Returns:
        dict: A dictionary representation of the input data.
    """
    if isinstance(data, dict):
        return data
    elif isinstance(data, list):
        return {i: item for i, item in enumerate(data)}
    else:
        raise ValueError("Input data must be a dictionary or a list.")
def monitor_data(data):
    """
    Monitor the input data and print its dictionary representation.

    Args:
        data: The input data to be monitored.
    """
    try:
        data_dict = convert_to_dict(data)
        print("Data in dictionary format:", data_dict)
    except ValueError as error:
        print(f"Error: {error}")
def monitor_data(data):
    print("Monitoring Started")