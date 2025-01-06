import os
import traceback
import csv
from PIL import Image
from datetime import datetime, timedelta
import sys
from tqdm import tqdm

def process_folder(parent_folder, folder_type):
    # Create empty lists to store data
    folders = []
    images = []
    metadata = []

    # Get list of all subfolders recursively
    for root, dirs, files in os.walk(parent_folder):
        folders.extend([os.path.join(root, d) for d in dirs])
        images.extend([os.path.join(root, f) for f in files if f.lower().endswith('.jpg')])

    # Loop through each folder with progress bar
    for folder in tqdm(folders, desc=f"Processing {folder_type} folders"):
        # Get images in this folder
        folder_images = [image for image in images if os.path.dirname(image) == folder]
        # Loop through images with progress bar
        for image_path in tqdm(folder_images, desc=f"Processing images in {folder}", leave=False):
            # Get metadata
            date_taken = None
            try:
                with Image.open(image_path) as img:
                    exif_data = img._getexif()
                    date_taken = exif_data.get(36867)  # 36867 corresponds to DateTimeOriginal tag
            except Exception as e:
                print(f"Error processing image '{image_path}': {e}")
                traceback.print_exc()
            if date_taken:
                date, time = date_taken.split()
                # Split into date and time
                props = {
                    'DateTaken': date,
                    'TimeTaken': time,
                    'Image': os.path.basename(image_path),
                    'Pole': os.path.basename(folder),
                    'Type': folder_type
                }
                metadata.append(props)

    # Sort the metadata list based on TimeTaken in ascending order
    metadata.sort(key=lambda x: datetime.strptime(x['TimeTaken'], '%H:%M:%S'))

    # Analyze time intervals and calculate CycleTotalHour
    cycle_count = 1
    cycle_start_time = None
    total_cycle_duration = timedelta()
    for i in range(1, len(metadata)):
        time_difference = datetime.strptime(metadata[i]['TimeTaken'], '%H:%M:%S') - datetime.strptime(metadata[i - 1]['TimeTaken'], '%H:%M:%S')
        if time_difference.total_seconds() >= 60:
            metadata[i - 1]['CycleCount'] = f'CYCLE {cycle_count}'
            if cycle_start_time:
                # Calculate cycle duration
                cycle_end_time = datetime.strptime(metadata[i - 1]['TimeTaken'], '%H:%M:%S')
                cycle_duration = cycle_end_time - cycle_start_time
                metadata[i - 1]['CycleTotalHour'] = str(cycle_duration)
                total_cycle_duration += cycle_duration
            cycle_count += 1
            cycle_start_time = None
        else:
            if not cycle_start_time:
                cycle_start_time = datetime.strptime(metadata[i - 1]['TimeTaken'], '%H:%M:%S')

    # For the last image, if there's no gap greater than 1 minute, consider it as the last cycle
    if cycle_start_time:
        cycle_end_time = datetime.strptime(metadata[-1]['TimeTaken'], '%H:%M:%S')
        cycle_duration = cycle_end_time - cycle_start_time
        metadata[-1]['CycleCount'] = f'CYCLE {cycle_count}'
        metadata[-1]['CycleTotalHour'] = str(cycle_duration)
        total_cycle_duration += cycle_duration

    # Calculate the total time difference between first and last TimeTaken values
    total_time_difference = datetime.strptime(metadata[-1]['TimeTaken'], '%H:%M:%S') - datetime.strptime(metadata[0]['TimeTaken'], '%H:%M:%S')
    total_hours, remainder = divmod(total_time_difference.total_seconds(), 3600)
    total_minutes, total_seconds = divmod(remainder, 60)
    total_time_formatted = "{:02}:{:02}:{:02}".format(int(total_hours), int(total_minutes), int(total_seconds))

    # Print results
    print(f"{folder_type} Data Capture (Pole):", len(folders))
    print(f"{folder_type} Start Time:", metadata[0]['TimeTaken'])
    print(f"{folder_type} End Time:", metadata[-1]['TimeTaken'])
    print(f"{folder_type} Hours Data Capture (By Battery Cycle):", total_cycle_duration)
    print(f"{folder_type} Battery Cycles:", cycle_count)  # New print for total cycles

    summary = [
        [f"{folder_type} Data Capture (Pole)", len(folders)],
        [f"{folder_type} Start Time", metadata[0]['TimeTaken']],
        [f"{folder_type} End Time", metadata[-1]['TimeTaken']],
        [f"{folder_type} Hours Data Capture (By Battery Cycle)", str(total_cycle_duration)],
        [f"{folder_type} Battery Cycles", cycle_count],
        [],
        ["DateTaken", "TimeTaken", "Image", "Pole", "CycleCount", "CycleTotalHour"]
    ]

    for data in metadata:
        summary.append([data['DateTaken'], data['TimeTaken'], data['Image'], data['Pole'], data.get('CycleCount', ''), data.get('CycleTotalHour', '')])

    return summary

if __name__ == "__main__":
    parent_folders = {}
    for folder_type in ["VISUAL", "THERMAL"]:
        while True:
            folder_path = input(f"Input your {folder_type} folder path: ").strip()
            if not folder_path:
                break
            if not os.path.exists(folder_path):
                print("Error: Folder path does not exist.")
                continue
            parent_folders[folder_type] = folder_path
            break

    if not parent_folders:
        print("No parent folders provided. Exiting.")
        sys.exit(1)

    visual_summary = process_folder(parent_folders["VISUAL"], "VISUAL") if "VISUAL" in parent_folders else []
    thermal_summary = process_folder(parent_folders["THERMAL"], "THERMAL") if "THERMAL" in parent_folders else []

    # Determine the maximum length for alignment
    max_length = max(len(visual_summary), len(thermal_summary))

    # Extend shorter summary with empty lists for alignment
    while len(visual_summary) < max_length:
        visual_summary.append([""] * 6)

    while len(thermal_summary) < max_length:
        thermal_summary.append([""] * 6)

    # Ask the user for the CSV file name
    csv_file_name = input("Enter the name of the CSV file to save the output (without extension): ").strip()
    if not csv_file_name:
        print("No CSV file name provided. Exiting.")
        sys.exit(1)

    csv_file_path = f"{csv_file_name}.csv"
    with open(csv_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for v_row, t_row in zip(visual_summary, thermal_summary):
            csv_writer.writerow(v_row + [""] * 2 + t_row)  # Insert two empty columns between visual and thermal data
