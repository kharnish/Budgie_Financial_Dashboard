# Spearmint Money Management

_A quick visualizer to get a hold on your personal finances._

## Usage
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

To load a transaction file which contains multiple accounts (i.e. from from Mint), ensure there is an `account_name` column
in the CSV file and simply leave the "New account name" input empty when uploading the file.

Once you categorize the transactions, you can add a budget and see your current status for different categories in the Budget tab.

## Security
All transaction data is stored locally in your MongoDB. 

It should go without saying, but please do not commit any personal information into the repository.

## Troubleshooting

If your bank's CSV fails to be uploaded, make an issue that includes the header of the CSV.
