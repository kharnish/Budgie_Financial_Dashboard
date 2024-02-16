from bson.objectid import ObjectId
from datetime import datetime, timedelta
from difflib import get_close_matches
from dotenv import load_dotenv
import numpy as np
import os
import pandas as pd

from maintain_transactions import MaintainDatabase


class BudgieDF(pd.DataFrame):
    def find(self, value_filter=None):
        """

        Args:
            value_filter (dict):
        """
        if value_filter is None:
            return self  # .get_data_list()
        else:
            if len(value_filter) == 1:
                return BudgieDF(self[self[list(value_filter.keys())[0]] == list(value_filter.values())[0]])
            elif len(value_filter) == 2:
                return BudgieDF(self[(self[list(value_filter.keys())[0]] == list(value_filter.values())[0]) & (self[list(value_filter.keys())[1]] == list(value_filter.values())[1])])

    def distinct(self, value):
        vals_list = list(self[value].unique())
        return sorted(vals_list)

    def get_data_list(self):
        return [item[1] for item in self.iterrows()]

    def sort(self, by):
        if isinstance(by, dict):
            ascending = True
            key = list(by.keys())[0]
            if by.get(key) == -1:
                ascending = False
            return BudgieDF(self.sort_values(list(by.keys())[0], ascending=ascending))
        else:
            return BudgieDF(self.sort_values(list(by.keys())[0]))


class MaintainCSV(MaintainDatabase):
    def __init__(self):
        super().__init__()
        self.file_dir = None

    def load_initial_data(self):
        load_dotenv()
        self.file_dir = os.getenv("DATA_DIR")
        self.transactions_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'transactions.csv')))
        self.transactions_table['date'] = pd.to_datetime(self.transactions_table['date'])
        self.budget_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'budget.csv')))
        self.accounts_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'accounts.csv')))

    def save_files(self):
        """Save all data files to a CSV"""
        self.transactions_table.to_csv(os.path.join(self.file_dir, 'transactions.csv'), index=False)
        self.budget_table.to_csv(os.path.join(self.file_dir, 'budget.csv'), index=False)
        self.accounts_table.to_csv(os.path.join(self.file_dir, 'accounts.csv'), index=False)

    def add_one_transaction(self, category, amount, t_date, description, account, note):
        """Add a single manual transaction to the dataframe"""
        transaction = {'date': [datetime.strptime(t_date, '%Y-%m-%d')],
                       'category': [category],
                       'description': [description],
                       'amount': [amount],
                       'currency': ['USD'],
                       'original description': [description],
                       'account name': [account],
                       'notes': [note]}
        self.transactions_table = BudgieDF(pd.concat([self.transactions_table, pd.DataFrame(transaction)]))

    def _get_categories(self, account):
        """Get all the descriptions corresponding categories"""
        m = self.transactions_table[self.transactions_table['account name'] == account]
        k = m.drop_duplicates(subset=['original description'])

        self.autocategories = {}
        for i, row in k.iterrows():
            self.autocategories[row['original description']] = {'category': row['category'], 'date': row['date']}

    def query_transactions(self, conf_dict):
        """Query dataframe according to configuration dict parameters

        Args:
             conf_dict:

        Returns: Pandas Dataframe of transactions
        """
        transactions = self.transactions_table[(self.transactions_table['date'] >= conf_dict['start_date']) & (self.transactions_table['date'] <= conf_dict['end_date'])]
        if len(conf_dict['filter_value']) == 0:
            pass
        else:
            transactions = transactions[transactions[conf_dict['field_filter'].lower()].isin(conf_dict['filter_value'])]

        if len(transactions) == 0:
            transactions = self.empty_transaction

        return transactions

    def get_oldest_transaction(self):
        return self.transactions_table['date'].min()

    def edit_transaction(self, change_dict):
        """Update transaction based on edits in Transaction table"""
        change_dict['data']['date'] = datetime.strptime(change_dict['data']['date'], '%m-%d-%Y')
        new_dict = change_dict['data']
        tid = new_dict['_id']
        existing = self.transactions_table[self.transactions_table['_id'] == tid]
        for key, val in new_dict.items():
            self.transactions_table.loc[existing.index, key] = new_dict[key]

    def edit_many_transactions(self, transaction_list):
        """Edit data for multiple transactions at one time"""
        for new_trans in transaction_list:
            try:
                new_trans['date'] = datetime.strptime(new_trans['date'], '%Y-%m-%d')
            except ValueError:
                new_trans['date'] = datetime.strptime(new_trans['date'], '%m-%d-%Y')
            tid = new_trans['_id']
            existing = self.transactions_table[self.transactions_table['_id'] == tid]
            for key, val in new_trans.items():
                self.transactions_table.loc[existing.index, key] = new_trans[key]

    def delete_transaction(self, transaction_dict):
        """Delete a list of transactions from the Transactions table"""
        for trans in transaction_dict:
            rm_i = self.transactions_table[self.transactions_table['_id'] == trans['_id']].index
            self.transactions_table = BudgieDF(self.transactions_table.drop(rm_i))

    def add_budget_item(self, category, value):
        """Add new budget item in dataframe with category and monthly value"""
        existing = self.budget_table[self.budget_table['category'] == category]
        if len(existing) == 1:
            self.budget_table.loc[existing.index, 'value'] = value
        else:
            self.budget_table = BudgieDF(pd.concat([self.budget_table, pd.DataFrame({'category': [category], 'value': [value]})]))

    def rm_budget_item(self, category, value):
        """Delete budget item in dataframe"""
        rm_i = self.budget_table[(self.budget_table['category'] == category) & (self.budget_table['value'] == value)].index
        self.budget_table = BudgieDF(self.budget_table.drop(rm_i))

    def add_account(self, account_name, status='open', initial_balance=0):
        """Add new account in dataframe with current status and beginning balance for net worth"""
        self.accounts_table = BudgieDF(pd.concat([self.accounts_table, pd.DataFrame({'account name': [account_name], 'status': [status], 'initial balance': [initial_balance]})]))

    def export_data_to_csv(self, root_dir=''):
        for coll in [self.transactions_table, self.budget_table, self.accounts_table]:
            coll.to_csv(coll.name + '.csv', index=False)


if __name__ == '__main__':
    md = MaintainCSV()
