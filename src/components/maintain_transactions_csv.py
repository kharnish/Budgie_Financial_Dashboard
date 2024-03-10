from datetime import datetime
from dotenv import load_dotenv
import os
import sys
import pandas as pd
import uuid

from maintain_transactions import MaintainDatabase, EMPTY_TRANSACTION


class BudgieDF(pd.DataFrame):
    def find(self, value_filter=None):
        """

        Args:
            value_filter (dict):
        """
        if value_filter is None:
            return self
        else:
            try:  # First check for date filter
                dates = value_filter.pop('date')
                temp = self[(self['date'] >= dates['$gte']) & (self['date'] <= dates['$lte'])]
            except KeyError:
                temp = self

            try:  # General catch all if the filter criteria doesn't exist in the columns
                if len(value_filter) == 1:
                    return BudgieDF(temp[temp[list(value_filter.keys())[0]] == list(value_filter.values())[0]])
                elif len(value_filter) == 2:
                    return BudgieDF(temp[(temp[list(value_filter.keys())[0]] == list(value_filter.values())[0]) & (temp[list(value_filter.keys())[1]] == list(value_filter.values())[1])])
            except KeyError:
                return BudgieDF()

    def distinct(self, value):
        try:
            vals_list = list(self[value].unique())
        except KeyError:
            vals_list = []
        return sorted(vals_list)

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
        self.file_dir = None if self.file_dir is None else self.file_dir

    def load_initial_data(self):
        # Get CSV file directory depending on if it's running from an executable bundle or regular environment
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            self.file_dir = os.path.abspath(os.path.join(os.getcwd(), 'data'))
            print('CSV Data Directory: ', self.file_dir)
        else:
            # we are running in a normal Python environment
            load_dotenv()
            self.file_dir = os.getenv("DATA_DIR")

        if not os.path.isdir(self.file_dir):
            os.makedirs(self.file_dir)

        try:
            self.transactions_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'transactions.csv')))
            self.transactions_table['date'] = pd.to_datetime(self.transactions_table['date'])
        except FileNotFoundError:
            self.transactions_table = BudgieDF(EMPTY_TRANSACTION)

        try:
            self.budget_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'budget.csv')))
        except FileNotFoundError:
            self.budget_table = BudgieDF()

        try:
            self.accounts_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'accounts.csv')))
        except FileNotFoundError:
            self.accounts_table = BudgieDF()

        try:
            self.categories_table = BudgieDF(pd.read_csv(os.path.join(self.file_dir, 'categories.csv')))
        except FileNotFoundError:
            self.categories_table = BudgieDF()

    def load_transactions(self, sheet, account=None):
        """Import transaction CSV and save many transactions to dataframe"""
        transaction_list = self._add_transactions(sheet, account)
        for trans in transaction_list:
            trans['_id'] = str(uuid.uuid4())

        # Insert transactions into database
        if len(transaction_list) > 0:
            if len(self.transactions_table) == 1:  # don't let it include the EMPTY_TRANSACTIONS item in the actual data
                self.transactions_table = BudgieDF(pd.DataFrame(transaction_list))
            else:
                self.transactions_table = BudgieDF(pd.concat([self.transactions_table, pd.DataFrame(transaction_list)]).reset_index(drop=True))
        self.export_data_to_csv()
        return len(transaction_list)

    def export_data_to_csv(self, root=None):
        """Save all data files to a CSV"""
        tables = [self.transactions_table, self.budget_table, self.accounts_table, self.categories_table]
        file_names = ['transactions.csv', 'budget.csv', 'accounts.csv', 'categories.csv']
        for i in range(4):
            if len(tables[i]) > 0:
                tables[i].to_csv(os.path.join(self.file_dir, file_names[i]), index=False)

    def add_one_transaction(self, category, amount, t_date, description, account, note):
        """Add a single manual transaction to the dataframe"""
        transaction = {'_id': str(uuid.uuid4()),
                       'date': [datetime.strptime(t_date, '%Y-%m-%d')],
                       'category': [category],
                       'description': [description],
                       'amount': [amount],
                       'original description': [description],
                       'account name': [account],
                       'notes': [note]}

        # Insert transactions into CSV
        if len(self.transactions_table) == 1 and self.transactions_table.loc[0]['description'] == 'No Available Data':  # don't let it include the EMPTY_TRANSACTIONS item in the actual data
            self.transactions_table = BudgieDF(pd.DataFrame(transaction))
        else:
            self.transactions_table = BudgieDF(pd.concat([self.transactions_table, pd.DataFrame(transaction)]).reset_index(drop=True))
        self.export_data_to_csv()

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
            transactions = EMPTY_TRANSACTION

        return transactions

    def get_oldest_transaction(self):
        return self.transactions_table['date'].min()

    def edit_transaction(self, change_dict):
        """Update transaction based on edits in Transaction table"""
        change_dict[0]['data']['date'] = datetime.strptime(change_dict[0]['data']['date'], '%m-%d-%Y')
        new_dict = change_dict[0]['data']
        tid = new_dict['_id']
        existing = self.transactions_table[self.transactions_table['_id'] == tid]
        for key, val in new_dict.items():
            self.transactions_table.loc[existing.index, key] = new_dict[key]
        self.export_data_to_csv()

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
        self.export_data_to_csv()

    def delete_transaction(self, transaction_dict):
        """Delete a list of transactions from the Transactions table"""
        for trans in transaction_dict:
            rm_i = self.transactions_table[self.transactions_table['_id'] == trans['_id']].index
            self.transactions_table = BudgieDF(self.transactions_table.drop(rm_i))
        self.export_data_to_csv()

    """====== Budget ======"""
    def add_budget_item(self, category, value):
        """Add new budget item in dataframe with category and monthly value"""
        try:  # Check for when there's no budget items yet
            existing = self.budget_table[self.budget_table['category'] == category]
        except KeyError:
            existing = []

        if len(existing) == 1:
            self.budget_table.loc[existing.index, 'value'] = value
        else:
            self.budget_table = BudgieDF(pd.concat([self.budget_table, pd.DataFrame({'category': [category],
                                                                                     'value': [value],
                                                                                     '_id': uuid.uuid4()})], ignore_index=True))
        self.export_data_to_csv()

    def get_budget_dict(self):
        """Get dictionary of all positive and negative budget line items"""
        pos_dict = {}
        neg_dict = {}
        for i, item in self.budget_table.find().iterrows():
            if item['value'] > 0:
                pos_dict[item['category']] = item['value']
            else:
                neg_dict[item['category']] = item['value']
        return pos_dict, neg_dict

    def rm_budget_item(self, category, value):
        """Delete budget item in dataframe"""
        rm_i = self.budget_table[(self.budget_table['category'] == category) & (self.budget_table['value'] == value)].index
        self.budget_table = BudgieDF(self.budget_table.drop(rm_i))
        self.export_data_to_csv()

    """====== Account ======"""
    def add_account(self, account_name, status='open', initial_balance=0):
        """Add new account in dataframe with current status and beginning balance for net worth"""
        self.accounts_table = BudgieDF(pd.concat([self.accounts_table, pd.DataFrame({'account name': [account_name],
                                                                                     'status': [status],
                                                                                     'initial balance': [initial_balance],
                                                                                     '_id': uuid.uuid4()})], ignore_index=True))

    def edit_account(self, change_dict):
        """Update account based on edits in Accounts table"""
        new_dict = change_dict[0]['data']
        tid = new_dict['_id']
        existing = self.accounts_table[self.accounts_table['_id'] == tid]
        for key, val in new_dict.items():
            self.accounts_table.loc[existing.index, key] = new_dict[key]
        self.export_data_to_csv()

    def delete_account(self, row_data):
        """Delete account in database"""
        rm_i = self.accounts_table[(self.accounts_table['_id'] == row_data['_id'])].index
        self.accounts_table = BudgieDF(self.accounts_table.drop(rm_i))

    """====== Category ======"""
    def add_category(self, category_name, category_parent=None):
        """Add new category in dataframe"""
        self.categories_table = BudgieDF(pd.concat([self.categories_table, pd.DataFrame({'parent': [category_parent],
                                                                                         'category name': [category_name],
                                                                                         '_id': uuid.uuid4()})], ignore_index=True))

    def delete_category(self, row_data):
        """Delete category in database"""
        pass
        # rm_i = self.categories_table[(self.categories_table['_id'] == row_data['_id'])].index
        # self.categories_table = BudgieDF(self.categories_table.drop(rm_i))


if __name__ == '__main__':
    md = MaintainCSV()
