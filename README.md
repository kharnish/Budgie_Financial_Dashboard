# Spearmint Money Management

_A quick visualizer to get a hold on your personal finances._

## Usage
Instantiate a Mongo database and store the information in a `.env` file in the top level of this repository following the template
    
    MONGO_HOST=mongodb://X.X.X.X:X/
    MONGO_DB=database_name
    TRANSACTIONS_CLIENT=transactions
    BUDGET_CLIENT=budget

Start the Dash app with `python app()` and then access the app at http://127.0.0.1:8050/.

Add new transactions by selecting an existing account from the dropdown, then uploading the transaction CSV from your bank.

## Security
All transaction data is stored locally in your MongoDB. 

It should go without saying, but please do not commit any personal information into the repository.

## Troubleshooting

If your bank's CSV fails to be uploaded, make an issue that includes the header of the CSV.
