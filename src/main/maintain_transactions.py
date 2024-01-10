import pandas as pd
import pymongo
from dotenv import load_dotenv
import os
from datetime import datetime


class MaintainTransactions:
    def __init__(self):
        load_dotenv()
        client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
        client = client_mongo[os.getenv("MONGO_DB")]
        self.transaction_table = client[os.getenv("TRANSACTIONS_CLIENT")]
        self.budget_table = client[os.getenv("BUDGET_CLIENT")]

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

            duplicates = list(self.transaction_table.find({'amount': row['amount'], 'original description': row['original description'],
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
            self.transaction_table.insert_many(transaction_list)
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

    def edit_transaction(self, change_dict):
        """Update transaction based on edits in Transaction table"""
        change_dict['data']['date'] = datetime.strptime('01-01-2024', '%m-%d-%Y')
        new_dict = change_dict['data']
        old_dict = change_dict['data'].copy()
        old_dict[change_dict['colId']] = change_dict['oldValue']
        return self.transaction_table.update_one(old_dict, {'$set': new_dict})

    def add_budget_item(self, category, value):
        """Add new budget item in database with category and monthly value"""
        existing = list(self.budget_table.find({'category': category}))
        if len(existing) == 1:
            self.budget_table.update_one({'category': category}, {"$set": {'value': value}})
        else:
            self.budget_table.insert_one({'category': category, 'value': value})

    def rm_budget_item(self, category, value):
        """Delete budget item in database"""
        self.budget_table.delete_one({'category': category, 'value': value})


if __name__ == '__main__':
    mt = MaintainTransactions()
    # mint_csv_path = ''
    # print(mt.add_transactions(mint_csv_path))
