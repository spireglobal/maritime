# SPIRE TCP to CSV DEMO
Connects to the Spire TCP stream and optionally outputs:
* a parsed csv
* a log file containing the raw stream text
* parsed data to a bigquery table

## Purpose
* This code is for demonstration purposes only
* Running the code for more than a few minutes, or for more than a few million lines is not appropriate to the design of the tool

## REQUIREMENTS
* Python >= 3.6
* Please follow any and all instructions on [Python install](https://www.python.org/downloads/) and setting the Python Path
* This readme is written assuming intermediate python experience

## SETUP
### Install required libraries
1. Set up a python virtual environment as you desire:
* [venv](https://docs.python.org/3/library/venv.html)
* [pipenv](https://pipenv.pypa.io/en/latest/) 
* [conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
``` pip3 install -r requirements.txt```

### GCP AND BIGQUERY
There is an **option** to store the parsed stream into a BigQuery table.  Please consult Google documentation regarding:
* Obtaining GCP access
* Authentication setup for GCP on your compute instance
* Enabling BigQuery

## SETTINGS YAML
Before running, edit the ```settings.yaml``` file

| Varliable         | Description                  | Default                    | 
| ----------------- | -----------------            |-----------------           |
|server             | TCP server URL               | streamingv2.ais.spire.com  |
|port               | TCP server port              | 56784                      |
|token              | Authorization token          | _USER SUPPLIED_            |
|max_messages       | Max messages to capture      | _USER SUPPLIED_ OR 0       |
|max_minutes        | Max minutes to capture stream| _USER SUPPLIED_ OR 0       |
|csv_path           | Path to csv output file      | output.csv                 |
|raw_path           | Path to log file for raw feed| raw.log                    |
|program_log        | Path to program log          | tcp_2_csv.log              |
|gcp_dataset_id     | Google Cloud dataset for BQ  | _USER SUPPLIED_            |
|gcp_table_id       | GCP table for BQ             | _USER SUPPLIED_            |
|gcp_project_id     | GCP project for BQ           | _USER SUPPLIED_            |

### SETTING NOTES 
* You must specify either ```max_messages``` or ```max_minutes```, but not both
* If you do not specify any of the gcp settings, writing to BigQuery will be skipped
* If you do not specify ```csv_path```, writing the csv will be skipped
* If you do not specify ```raw_path```, writing the raw tcp log will be skipped 
* If you do not specify ```program_log```, writing the program log will be skipped, you will only see it in the terminal




