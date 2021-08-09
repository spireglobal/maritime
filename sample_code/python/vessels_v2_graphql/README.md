# Spire customer / developer resource
The code is intended for demonstration purposes for Spire customers and is in no way intended for production use

# Setup
## Python Environment
1. Use a virtual environment, pipenv or other tool and enable the python environment
2. Install the requirements, for example
```bash
pip3 install -r requirements.txt
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
|pages_to_process                    |Max number of pages to process.  A helpful setting for debugging.  If set to 0, all pages are processed|
|test_name                           |Optional label that fills the csv column ```test_name```|

**Note:**
* Files are all assumed to be in the same directory as the program

## Queries
### Important
* As a demo, this client **requires** each query to include a section to request ```pageInfo```.
* Every query must contain the following:

```json
pageInfo{
  endCursor: String
  hasNextPage: Boolean!
}
```

* For context, consult the sample queries in the files discussed below
* Do not place any comments or any text that does not represent a query in the query text file you create
* Do not add any of the following input parameters to your query.  These will be inserted as part of the paging routine:
  * first
  * after
* This demo uses a value of 100 for ```first```, which means only 100 items per page are returned.  The service allows up to 1000 items, however the demo is not designed for specifying number of items per page
  
### Samples

|File                   |Purpose                                |
|-----------------------|---------------------------------------|
|sample_1.txt           |Will return all Vessel, Voyage and PositionUpdates available for the global fleet.  Every available field is requested|
|sample_2.txt           |Same as above, but specifying a set of mmsi|
|sample_3.txt           |All vessels in the Indian Ocean|

### Create a new query
1. Create a text file (file with .txt extension)
2. Write a query.  Use the samples as a guide.  Also see the important note regarding ```pageInfo``` above
3. Edit the ```settings.yaml``` file and add the name of the file you created after ```name_of_gql_query_file```

For example:

settings.yaml
```
name_of_gql_query_file: 'my-new_query.txt'
```   

# Run the program
Exact instructions depend upon how you set up the Python environment.  ```run.py``` contains the program logic

pipenv example:

```
pipenv run python3 run.py
```

virtual environment example:
* ```my_virtual_env``` as the directory containing the Python virtual environment
* ```vessels_v2_graphql``` as the directory containing this repository

```
source my_virtual_env/bin/activate  [ENTER]
cd vessels_v2_graphql [ENTER]
python3 run.py
```


# Logging
The program creates a log file for debugging purposes named ```demo_client.log```

# Troubleshooting
* Read again the section titled **Important**
* Errors will occur if the ```pageInfo``` section is not included
* Errors will occur if the query text file contains comments (#) or any text that does not conform to GraphQL query syntax
* Errors will occur if the query text file contains ```_limit```, ```_after```, ```_cursor```, or ```_correlationId```
