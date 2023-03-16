README FILE

The file in this folder is a Custom Power BI Connector that allows you to easily access some standard queries for Spire GraphQL API (Vessels 2.0, Vessels 2.0 with Vessel to Port ETA, Port Events API) without having to code anything. 

In order to try the connector on Power BI, you would need the following:

Prerequisites:
Power BI Desktop installed on your machine
A Spire GraphQL API account with a valid token


Step 1: Download and Install the SpireGraphQL_PowerBI Connector

Download the SpireGraphQL_PowerBI Connector from this Spire GitHub repository.
Copy the file 'SpireGraphQLAPI_PowerBI.mez' to the following location: C:\Users\{YourUsername}\Documents\Power BI Desktop\Custom Connectors.

Step 2: Allow Custom Connectors in Power BI Desktop

Open Power BI Desktop.
Go to File > Options and settings > Security.
Enable the “Allow any extension to load without validation or warning” option.
Restart Power BI Desktop.

Step 3: Connect to Spire GraphQL API Data

Open Power BI Desktop.
Go to Home > Get Data > More > Other > SpireGraphQL_PowerBI.
Enter your Spire GraphQL API token in the “Account key” field.
Select the service you want to use from the drop-down list (Vessels 2.0, Vessels 2.0 with Vessel to Port ETA, or Port Events API).
Enter the necessary query parameters for the selected service.
Click “Apply” to load a preview of the data
Click “Load” or “Transform Data” to retrieve the data in your project (Make sure to check the query previously in the navigation table).

Step 4: Transform and Visualize the Data

Power BI will retrieve the data.
Transform the data as needed using the Query Editor.
Create your report or dashboard using the transformed data.

Conclusion:
The SpireGraphQL_PowerBI Connector provides an easy way to connect to the Spire GraphQL API and retrieve AIS data from the Vessels 2.0 and Port Events API services. By following this step-by-step tutorial, you can install and use the SpireGraphQL_PowerBI Connector to access this valuable data and create insightful reports and dashboards in Power BI.
