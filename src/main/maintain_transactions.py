import pandas as pd
import pymongo
from dotenv import load_dotenv
import os
from datetime import datetime
from difflib import SequenceMatcher, get_close_matches
import numpy as np
from datetime import timedelta


class MaintainTransactions:
    def __init__(self):
        load_dotenv()
        client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
        client = client_mongo[os.getenv("MONGO_DB")]
        self.transaction_table = client[os.getenv("TRANSACTIONS_CLIENT")]
        self.budget_table = client[os.getenv("BUDGET_CLIENT")]
        self.rule_table = client[os.getenv("RULE_CLIENT")]
        self.autocategories = None

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

        # If only one account, get autocategorization categories from previous data
        if account:
            self._get_categories(account)

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
                        if abs((dup['date'] - row['date'])) < timedelta(days=10):
                            print(f"Inserted a possible duplicate item: {row['date']} / {dup['date']}, {dup['original description']}, ${dup['amount']:.2f}")
                            transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                        break
            else:
                # there's no match, so add the transaction
                # but first, get the category
                transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
        if len(transaction_list) > 0:
            self.transaction_table.insert_many(transaction_list)
        return len(transaction_list)

    @staticmethod
    def _make_transaction_dict(td, category, account):
        """Convert transaction dictionary into standard transaction dictionary"""
        default_transaction = {'date': td['date'],
                               'category': category,
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

    def _get_categories(self, account):
        k = list(self.transaction_table.aggregate([
            {'$match': {  # match with only this account
                'account name': account}},
            {'$group': {  # get the most recent, unique original description
                '_id': '$original description',
                'date': {'$last': '$date'},
                'cat': {'$last': '$category'}}}
        ]))
        self.autocategories = {}
        for cat in k:
            self.autocategories[cat['_id']] = {'category': cat['cat'], 'date': cat['date']}

    def _autocategorize(self, row):
        try:
            matches = get_close_matches(row['original description'], self.autocategories.keys(), cutoff=0.7)
            matches_data = [self.autocategories[match] for match in matches]
            i_most_recent = np.argmax([cat['date'] for cat in matches_data])
            return matches_data[i_most_recent]['category']
        except (ValueError, AttributeError):
            return row['category'] if row['category'] != '' else 'unknown'

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

    def add_rule(self):
        # If description contains DFAS and amount between 1500 and 2500: categorize as Income
        rule = {'if': {'description': {'contains': 'dfas'}, 'amount': {'between': [1000, 2500]}},
                'then': {'category': 'Income'}}
        self.rule_table.insert_one(rule)

        # If description contains District and amount between 500 and 900: categorize as Tithe
        rule = {'if': {'description': {'contains': 'district'}, 'amount': {'between': [500, 900]}},
                'then': {'category': 'Income'}}
        self.rule_table.insert_one(rule)


if __name__ == '__main__':
    mt = MaintainTransactions()
    lm_path = '\\\\spacenet\\BranchData\\Code 8121\\Harnish\\Aloha_Data_Visualizer\\src\\budget_tracker\\lunchmoney-20231220133052.csv'
    # print(mt.add_transactions(lm_path))
    mint_csv_path = '\\\\spacenet\\BranchData\\Code 8121\\Harnish\\Aloha_Data_Visualizer\\src\\budget_tracker\\mint_transactions_20231214.csv'

    amex_path = '\\\\spacenet\\BranchData\\Code 8121\\Harnish\\Aloha_Data_Visualizer\\src\\budget_tracker\\transactions_amex_12-1_01-08.CSV'
    # print(mt.add_transactions(amex_path, 'More Rewards Amex'))
    checking_path = '\\\\spacenet\\BranchData\\Code 8121\\Harnish\\Aloha_Data_Visualizer\\src\\budget_tracker\\transactions_checking_12-1_01-08.CSV'
    # print(mt.add_transactions(checking_path, 'Flagship Checking'))
    boa_path = '\\\\spacenet\\BranchData\\Code 8121\\Harnish\\Aloha_Data_Visualizer\\src\\budget_tracker\\Transaction_BOA_12-01_01-08.csv'
    print(mt.add_transactions(boa_path, 'Customized Cash Rewards World Mastercard Card'))
