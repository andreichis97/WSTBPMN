import requests

read_file = open("D:\\Andrei\\ModellingTools\\WST_BPMN_Modeling_Tool\\Results\\upload_graph_details.txt", "r")
lines = read_file.readlines()
# Set the repository ID and graph URI
repository_id = lines[0].strip()
file_path = lines[1].strip()
read_file.close()

#Setting request headers
if( ".trig" in file_path):
    headers = {
        'Content-Type': 'application/x-trig'
    }
else:
    headers = {
        'Content-Type': 'application/x-turtle'
    }

# Define the API endpoint
url = f"http://localhost:7200/repositories/{repository_id}/statements"

# Open the file and read its content
with open(file_path, 'r') as file:
    content = file.read()

# Make the POST request to load the file
response = requests.post(
    url.format(repositoryID=repository_id),
    headers=headers,
    data=content
)

# Check the response status code
print(response.status_code)
if (response.status_code == 200 or response.status_code == 204):
    print('File loaded successfully.')
else:
    print('Error loading file:', response.text)
