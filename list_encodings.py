import os
import chardet
 
found_encodings = []

def list_file_encodings(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                if encoding not in found_encodings:
                    found_encodings.append(encoding)
        else:
          list_file_encodings(file_path)
 
# Replace 'your_folder_path' with the path to your folder
folder_path = './scrapers/data/Muis/'
list_file_encodings(folder_path)
print(found_encodings)