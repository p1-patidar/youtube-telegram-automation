import os
import re

# IMPORTANT: Replace this with the actual path to your folder
folder_path = '/Users/pp/Downloads/professorofhow/3-15'


def clean_srt_line(line):
    """Checks if a line is part of the actual subtitle text."""
    # It's not a text line if it's a number, a timestamp, or empty
    if line.strip().isdigit():
        return False
    if '-->' in line:
        return False
    if not line.strip():
        return False
    return True


def convert_srt_to_txt(srt_file_path):
    """Reads an SRT file, extracts the text, and saves it as a TXT file."""
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Filter the lines to keep only the subtitle text
        text_lines = [line.strip() for line in lines if clean_srt_line(line)]

        # Join the text lines together
        plain_text = '\n'.join(text_lines)

        # Create the new .txt filename
        txt_file_path = os.path.splitext(srt_file_path)[0] + '.txt'

        # Save the new text file
        with open(txt_file_path, 'w', encoding='utf-8') as file:
            file.write(plain_text)

        print(f'Successfully converted: {os.path.basename(srt_file_path)} -> {os.path.basename(txt_file_path)}')

    except Exception as e:
        print(f'Could not convert {os.path.basename(srt_file_path)}. Error: {e}')


def process_folder(path):
    """Processes all .srt files in the specified folder."""
    print(f'Scanning folder: {path}')
    for filename in os.listdir(path):
        if filename.endswith('.srt'):
            file_path = os.path.join(path, filename)
            convert_srt_to_txt(file_path)
    print('\nConversion process finished.')


# Run the script for the specified folder
if os.path.isdir(folder_path):
    process_folder(folder_path)
else:
    print(f'Error: The folder "{folder_path}" does not exist. Please update the folder_path in the script.')