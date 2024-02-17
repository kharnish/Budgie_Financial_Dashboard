# Budgie Financial Dashboard

_A quick visualizer to monitor your personal finances._

Process your bank transactions in a locally-hosted database or set of CSV files to get an overview of your spending, categorize transactions, and define budget areas.

![app screenshot](/src/assets/screenshot.PNG)

## Usage
There are two ways to store data for Budgie: a Mongo database or a set of CSV files.

Note: I've not tested the limit of how large the CSV file can be, so you may experience slower performance if you have a large number of transactions (i.e. 10s of thousands of transactions).

### Mongo Database
Instantiate a Mongo database and store the information in a `.env` file in the top level of this repository following the template
    
    MONGO_HOST=mongodb://X.X.X.X:X/
    MONGO_DB=your_database_name
    TRANSACTIONS_CLIENT=transactions
    BUDGET_CLIENT=budget

Start the Dash app with `python app()` and then access the app at http://127.0.0.1:8050/.

Add a new account by selecting the "Add New Account..." option from the accounts drop down menu.
Type your desired account name and instantiate that account by selecting a transaction CSV file from your bank to upload. 
Once the account is logged in your database, you can upload more transactions CSV files under that account. 
You can select multiple files to upload simultaneously for the same account.

To load a transaction file which contains multiple accounts (i.e. transactions CSV from Mint), ensure there is an `account_name` column
in the CSV file and simply leave the "New account name" input empty when uploading the file.

After the transactions are loaded, the parameters can be updated either individually or multiple at one time.

The new transactions will attempt to be auto-categorized based on previous transactions with a similar description. 

Once you categorize the transactions, you can add a budget and see your current status for different categories in the Budget tab.

### CSV File
Create a new folder to hold your CSV data, and store the path in a `.env` file in the top level of this repository following the template.
    
    DATA_DIR=C:\path\to\data\directory

When you add new transactions or update your budget, Budgie will automatically rewrite the CSV with the new data. 
Alternatively, you can click the "Save" button in the header to manually export your data.

### Special note about Venmo
Venmo allows you to spend either from your Venmo account balance, or from a third party account. To denote when these transactions are from an alternative source, it should be marked in the 
transaction notes as "Source: [source information]" in order to properly calculate your net worth. 

## Security
All transaction data is stored locally in your MongoDB. 

It should go without saying, but please do not commit any personal information into the repository.

## Troubleshooting

If your bank's CSV fails to be uploaded, make an issue that includes the header of the CSV.
