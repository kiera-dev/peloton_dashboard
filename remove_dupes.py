import json

def remove_duplicates(json_file_path):
    # Read existing JSON data
    with open(json_file_path, 'r') as json_file:
        existing_data = json.load(json_file)

    # Create a set to store unique timestamps
    unique_timestamps = set()

    # Filter out duplicate entries based on 'created_at' timestamp
    unique_data = []
    for entry in existing_data:
        timestamp = entry['created_at']
        if timestamp not in unique_timestamps:
            unique_data.append(entry)
            unique_timestamps.add(timestamp)

    # Update existing_data with unique entries
    existing_data = unique_data

    # Sort existing_data based on 'created_at' timestamp
    existing_data.sort(key=lambda x: x['created_at'])

    # Save the updated JSON back to the file
    with open(json_file_path, 'w') as json_file:
        json.dump(existing_data, json_file, indent=4)

    print("Duplicate entries removed and file updated.")


# Usage: Pass the path to your JSON file as an argument
if __name__ == "__main__":
    json_file_path = 'workout_data.json'  # Replace this with your JSON file path
    remove_duplicates(json_file_path)