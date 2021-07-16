# Setup
## Python Environment
1. Use a virtual environment, pipenv or other tool and enable the python environment
2. Install the requirements, for example
```bash
pip install -r requirements.txt
```
## Settings
Edit the settings.yaml file

|Setting                             |Info                                |
|------------------------------------|------------------------------------|
|endpoint                            |The url to the service              |
|token                               |Authentication token                |
|name_of_gql_query_file              |Name of file containing query to execute|
|name_of_raw_output_file             |Name of raw output log. If blank, no log is produced|
|name_of_csv_file                    |Name of csv file. If blank, no file is produced|
|items_per_page                      |Number of objects to return per page.  Max 1000|
|pages_to_process                    |Max number of pages to process.  A helpful setting for debugging.  If set to 0, all pages are processed|

**Note:** Files are all assumed to be in the same directory as the program

## Sample queries
Prior to running the program, please review each of the sample files

|File                   |Purpose                                |
|-----------------------|---------------------------------------|
|sample_1.txt           |Will return all Vessel, Voyage and PositionUpdates available for the global fleet.  Every available field is requested|
|sample_2.txt           |Same as above, but specifying a set of mmsi|
|sample_3.txt           |All vessels in the Indian Ocean|