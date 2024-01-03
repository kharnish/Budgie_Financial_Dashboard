import pandas as pd
import pymongo
from dotenv import load_dotenv
import os


class MaintainTransactions:
    def __init__(self):
        load_dotenv()
        client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
        client = client_mongo[os.getenv("MONGO_DB")]
        self.table = client[os.getenv("TRANSACTIONS_CLIENT")]

    def add_transactions(self, sheet, account=None):
        """Add transactions to a database, ensuring duplicates are not added"""
        if isinstance(sheet, str):
            df = pd.read_csv(sheet)
        else:
            df = sheet

        # Standardize sheet columns
        df.columns = [col.lower().replace('_', ' ') for col in df.columns]
        if 'transaction date' in df.columns:
            df = df.rename(columns={'transaction date': 'date'})
        else:
            df = df.rename(columns={'posted date': 'date'})
        if 'original name' in df.columns:
            df = df.rename(columns={'payee': 'description', 'original name': 'original description'})
        else:
            df = df.rename(columns={'payee': 'description'})
        df['date'] = pd.to_datetime(df['date'])
        if 'credit' in df.columns and 'debit' in df.columns:
            df['amount'] = df['credit'].fillna(-df['debit'])
        if 'category' not in df.columns:
            df['category'] = ''
        if 'original description' not in df.columns:
            df['original description'] = df['description']
        account_labels = True if 'account name' in df.columns else False
        if not account_labels and not account:
            return 'Error: Must provide account name if not given in CSV'
        df = df.fillna('')

        # Check to ensure all the necessary columns were converted
        necessary_columns = ['date', 'description', 'amount']
        for col in necessary_columns:
            if col not in df.columns:
                print(f"Error: CSV does not contain '{col}' column")
                return None

        # Add all non-duplicate transactions to database
        transaction_list = []
        for i, row in df.iterrows():
            if account_labels:
                account = row['account name']

            duplicates = list(self.table.find({'amount': row['amount'], 'original description': row['original description'],
                                               'account name': account}))

            if len(duplicates) > 0:
                for dup in duplicates:
                    if dup['date'] == row['date']:
                        # It's an exact match for amount, description, and date, so definitely a duplicate
                        break
                    else:
                        # It's a match for amount and description but not date, so check if it updated a pending transaction
                        print(f"Found a duplicate item with a different date: {dup['original description']}")
                        pass
            else:
                # there's no match, so add the transaction
                transaction_list.append(self.make_transaction_dict(row, account))
        if len(transaction_list) > 0:
            self.table.insert_many(transaction_list)
        return len(transaction_list)

    @staticmethod
    def make_transaction_dict(td, account):
        """Convert transaction dictionary into standard transaction dictionary"""
        default_transaction = {'date': td['date'],
                               'category': td['category'] if td['category'] != '' else 'unknown',
                               'description': td['description'],
                               'amount': td['amount'],
                               'currency': 'USD',
                               'original description': td['original description'],
                               'account name': account,
                               'notes': ''}
        return default_transaction


if __name__ == '__main__':
    mt = MaintainTransactions()
    mint_csv_path = ''
    print(mt.add_transactions(mint_csv_path))
