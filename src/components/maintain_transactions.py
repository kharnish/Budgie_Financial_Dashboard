from bson.objectid import ObjectId
from datetime import datetime, timedelta
from difflib import get_close_matches
from dotenv import load_dotenv
import numpy as np
import os
import pandas as pd
import pymongo

TRANSACTIONS_CLIENT = 'transactions_3'
BUDGET_CLIENT = 'budget'
ACCOUNTS_CLIENT = 'accounts'
CATEGORIES_CLIENT = 'categories'

EMPTY_TRANSACTION = pd.DataFrame.from_dict({'_id': ['None'], 'date': [datetime.today()], 'category': ['unknown'], 'description': ['No Available Data'],
                                            'amount': [0], 'account name': ['None'], 'notes': ['None']})


class MaintainDatabase:
    def __init__(self):
        self.transactions_table = None
        self.budget_table = None
        self.accounts_table = None
        self.categories_table = None
        self.autocategories = None
        self.file_dir = os.getcwd()

        self.load_initial_data()

    def load_initial_data(self):
        load_dotenv()
        client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
        client = client_mongo[os.getenv("MONGO_DB")]
        self.transactions_table = client[TRANSACTIONS_CLIENT]
        self.budget_table = client[BUDGET_CLIENT]
        self.accounts_table = client[ACCOUNTS_CLIENT]
        self.categories_table = client[CATEGORIES_CLIENT]

    def load_transactions(self, sheet, account=None):
        """Import transaction CSV and write many transactions to database"""
        transaction_list = self._add_transactions(sheet, account)

        # Insert transactions into database, unless there was an error, then just return the error string
        if isinstance(transaction_list, str):
            return transaction_list
        elif len(transaction_list) > 0:
            self.transactions_table.insert_many(transaction_list)
        return len(transaction_list)

    def _add_transactions(self, sheet, account=None):
        """Add transactions to a database, ensuring duplicates are not added, and taking special care with Venmo transactions"""
        if isinstance(sheet, str):
            df = pd.read_csv(sheet)
        else:
            df = sheet

        # Extra check if it's a venmo CSV
        if df.columns[1] == 'Unnamed: 1':
            if isinstance(sheet, str):
                df = pd.read_csv(sheet, header=2)
                df.drop(0, inplace=True)
            else:
                df = sheet
                df.columns = df.iloc[1]
                df.drop([0, 1, 2], inplace=True)
                df = df.reset_index(drop=True)
            df.drop(len(df) - 1, inplace=True)
            df = df.rename(columns={'Datetime': 'date', 'Note': 'description', 'Amount (total)': 'amount'})
            df['amount'] = [''.join(val.split(' $')) for val in df['amount']]
            df['amount'] = df['amount'].astype(float)
            df['date'] = [val.split('T')[0] for val in df['date']]
            source = df['Funding Source'].replace({'Venmo balance': np.nan})
            if any(~source.isna()):
                df['notes'] = 'Source: ' + source

        # Standardize sheet columns
        df = df.dropna(axis='columns', how='all')
        df.columns = [col.lower().replace('_', ' ') for col in df.columns]

        if 'transaction date' in df.columns:  # Prefer to use 'transaction date' as opposed to 'posted date' if there's both
            df = df.rename(columns={'transaction date': 'date'})
        else:
            df = df.rename(columns={'post date': 'date', 'posting date': 'date', 'posted date': 'date', 'booking date': 'date'})

        if 'original name' in df.columns:
            df = df.rename(columns={'payee': 'description', 'original name': 'original description'})
        else:
            df = df.rename(columns={'payee': 'description'})

        df['date'] = pd.to_datetime(df['date'])

        if 'credit' in df.columns and 'debit' in df.columns:
            df['amount'] = df['credit'].fillna(-df['debit'])
        elif 'credit debit indicator' in df.columns:
            cdi = list(df['credit debit indicator'].str.lower())
            vals = list(df['amount'])
            new_vals = []
            for i in range(len(cdi)):
                if cdi[i] == 'credit':
                    new_vals.append(vals[i])
                else:
                    new_vals.append(-vals[i])
            df['amount'] = new_vals
        elif isinstance(df.loc[0]['amount'], str):
            df['amount'] = [''.join(val.split('$')).replace('(', '-').replace(')', '').replace(',', '') for val in df['amount']]
            df['amount'] = df['amount'].astype(float)

        if 'original description' not in df.columns:
            try:
                df['original description'] = df['description']
            except KeyError:
                return 'Error: Must provide "description" column in the CSV'
        account_labels = True if 'account name' in df.columns else False

        if not account_labels and not account:
            return 'Error: Must provide account name if not given in CSV'
        
        if 'category' not in df.columns or account:
            df['category'] = ''

        # Replace NA with empty string and remove transactions with no date
        df = df.fillna('')
        df = df.dropna(subset='date', axis='index')

        # If only one account for that file, get autocategorization categories from previous data
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
        now = datetime.now()
        for i, row in df.iterrows():
            if account_labels:
                account = row['account name']

            duplicates = self.transactions_table.find({'amount': row['amount'], 'account name': account}).sort({'date': -1})
            if isinstance(duplicates, pd.DataFrame):
                # TODO verify that this works with CSV and BudgieDF
                len_dups = len(duplicates)
                duplicates = duplicates.iterrows()
            else:
                duplicates = list(duplicates)
                len_dups = len(duplicates)

            if len_dups > 0:
                for dup in duplicates:
                    if isinstance(dup, tuple):
                        dup = dup[1]

                    if dup['date'] > row['date']:
                        continue
                    if dup['date'] == row['date']:
                        if dup['original description'] == row['original description']:
                            # It's an exact match for amount, description, and date, so definitely a duplicate
                            break
                        else:
                            matches = get_close_matches(row['original description'], [dup['original description']], cutoff=0.1)
                            if matches:
                                break
                            else:
                                print(f"Did not insert possible duplicate, but check different description: "
                                      f"New: {row['date']}, {row['original description']} / Existing: {dup['date']}, {dup['original description']}, ${dup['amount']:.2f}")
                                break
                    else:
                        # It's a match for amount and description but not date, so check if it updated a pending transaction
                        # If the transaction date is over 7 days from the duplicate, it's probably a recurring and not a duplicate
                        if abs((dup['date'] - row['date'])) > timedelta(days=7):
                            print(f"Inserted possible repeating transaction: New: {row['date']}, {row['original description']} / "
                                  f"Existing: {dup['date']}, {dup['original description']}, ${dup['amount']:.2f}")
                            transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                            if row['date'] - now > timedelta(days=30):
                                print(f"Inserted transaction from over a month ago: {row['date']}, {row['original description']}, ${row['amount']:.2f}")
                            break
                        else:
                            matches = get_close_matches(row['original description'], [dup['original description']], cutoff=0.35)
                            if matches:
                                break
                            else:
                                print(f"Did not insert possible duplicate item: New: {row['date']}, {row['original description']} / "
                                      f"Existing: {dup['date']}, {dup['original description']}, ${dup['amount']:.2f}")
                                break
            else:
                # There's no match, so get the category and add the transaction
                transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                if row['date'] - now > timedelta(days=30):
                    print(f"Inserted transaction from over a month ago: {row['date']}, {row['original description']}, ${row['amount']:.2f}")

        return transaction_list

    def add_one_transaction(self, category, amount, t_date, description, account, note):
        """Add a single manual transaction to the database"""
        transaction = {'date': datetime.strptime(t_date, '%Y-%m-%d'),
                       'category': category,
                       'description': description,
                       'amount': amount,
                       'original description': description,
                       'account name': account,
                       'notes': note}
        return self.transactions_table.insert_one(transaction)

    @staticmethod
    def _make_transaction_dict(td, category, account):
        """Convert transaction dictionary into standard transaction dictionary"""
        default_transaction = {'date': td['date'],
                               'category': category,
                               'description': td['description'],
                               'amount': td['amount'],
                               'original description': td['original description'],
                               'account name': account,
                               'notes': td.get('notes')}
        return default_transaction

    def _get_categories(self, account):
        """Get all the descriptions corresponding categories"""
        k = list(self.transactions_table.aggregate([
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
        """Check with all the known descriptions if there are any close, and if so, use the last known category"""
        try:
            matches = get_close_matches(row['original description'], self.autocategories.keys(), cutoff=0.7)
            matches_data = [self.autocategories[match] for match in matches]
            i_most_recent = np.argmax([cat['date'] for cat in matches_data])
            return matches_data[i_most_recent]['category']
        except (ValueError, AttributeError):
            return row['category'] if row['category'] != '' else 'unknown'

    def query_transactions(self, conf_dict):
        """Query Mongo according to configuration dict parameters

        Args:
             conf_dict:

        Returns: Pandas Dataframe of transactions
        """
        if len(conf_dict['filter_value']) == 0:
            mongo_filter = {}
        else:
            mongo_filter = {conf_dict['field_filter'].lower(): {'$in': conf_dict['filter_value']}}

        transactions = pd.DataFrame(self.transactions_table.find({
            'date': {
                '$gte': datetime.strptime(conf_dict['start_date'], '%Y-%m-%d'),
                '$lte': datetime.strptime(conf_dict['end_date'], '%Y-%m-%d')},
            **mongo_filter}))
        if len(transactions) == 0:
            transactions = EMPTY_TRANSACTION

        return transactions

    def get_oldest_transaction(self):
        return list(self.transactions_table.find().sort({'date': 1}).limit(1))[0]['date'].date()

    def edit_transaction(self, change_dict):
        """Update transaction based on edits in Transaction table"""
        change_dict[0]['data']['date'] = datetime.strptime(change_dict[0]['data']['date'], '%m-%d-%Y')
        new_dict = change_dict[0]['data']
        new_dict.pop('_id')
        old_dict = change_dict[0]['data'].copy()
        old_dict[change_dict[0]['colId']] = change_dict[0]['oldValue']
        return self.transactions_table.update_one(old_dict, {'$set': new_dict})

    def edit_many_transactions(self, transaction_list):
        """Edit data for multiple transactions at one time"""
        for new_trans in transaction_list:
            try:
                new_trans['date'] = datetime.strptime(new_trans['date'], '%Y-%m-%d')
            except ValueError:
                new_trans['date'] = datetime.strptime(new_trans['date'], '%m-%d-%Y')
            tid = new_trans.pop('_id')
            self.transactions_table.update_one({'_id': ObjectId(tid)}, {'$set': new_trans})

    def delete_transaction(self, transaction_dict):
        """Delete a list of transactions from the Transactions table"""
        for trans in transaction_dict:
            trans.pop('_id')
            trans['date'] = datetime.strptime(trans['date'], '%m-%d-%Y')
            self.transactions_table.delete_one(trans)

    """====== Budget ======"""
    def add_budget_item(self, category, value):
        """Add new budget item in database with category and monthly value"""
        existing = list(self.budget_table.find({'category': category}))
        if len(existing) == 1:
            return self.budget_table.update_one({'category': category}, {"$set": {'value': value}})
        else:
            return self.budget_table.insert_one({'category': category, 'value': value})

    def get_budget_dict(self):
        """Get dictionary of all positive and negative budget line items"""
        pos_dict = {}
        neg_dict = {}
        for item in self.budget_table.find():
            if item['value'] > 0:
                pos_dict[item['category']] = item['value']
            else:
                neg_dict[item['category']] = item['value']
        return pos_dict, neg_dict

    def rm_budget_item(self, category, value):
        """Delete budget item in database"""
        return self.budget_table.delete_one({'category': category, 'value': value})

    """====== Account ======"""
    def add_account(self, account_name, status='open', initial_balance=0):
        """Add new account in database with current status and beginning balance for net worth"""
        return self.accounts_table.insert_one({'account name': account_name, 'status': status, 'initial balance': initial_balance})

    def edit_account(self, change_dict):
        """Update accounts based on edits in Accounts table"""
        new_dict = change_dict[0]['data']
        new_dict.pop('_id')
        old_dict = change_dict[0]['data'].copy()
        old_dict[change_dict[0]['colId']] = change_dict[0]['oldValue']
        return self.accounts_table.update_one(old_dict, {'$set': new_dict})

    def delete_account(self, row_data):
        """Delete account in database"""
        return self.accounts_table.delete_one(row_data)

    """====== Category ======"""
    def add_category(self, category_name, category_parent=None):
        """Add new category in database ... """
        return self.categories_table.insert_one({'parent': category_parent, 'category name': category_name, 'hidden': False})

    def edit_category(self, change_dict):
        """Update category data based on edits in Categories table"""
        new_dict = change_dict[0]['data']
        new_dict.pop('_id')
        new_dict.pop('parent')  # TODO this is a quick fix that will need to be updated when it actually uses parents more
        old_dict = change_dict[0]['data'].copy()
        old_dict[change_dict[0]['colId']] = change_dict[0]['oldValue']
        return self.categories_table.update_one(old_dict, {'$set': new_dict})

    def get_hide_from_trends(self):
        """Get list of all categories hidden from trends"""
        return [row['category name'] for row in self.categories_table.find({'hidden': True})]

    def delete_category(self, row_data):
        """Delete category in database"""
        for row in row_data:
            if row['parent'] == '':
                row['parent'] = None
            return self.categories_table.delete_one(row)

    """====== Overall ======"""
    def export_data_to_csv(self, root=None):
        """Save database data to CSV files"""
        load_dotenv()
        root = os.getenv('BACKUP_DIR') if root is None else root
        os.makedirs(root, exist_ok=True)
        for coll in [self.transactions_table, self.budget_table, self.accounts_table, self.categories_table]:
            data = coll.find()
            this_data = pd.DataFrame(data)
            try:
                this_data = this_data.drop(columns=['currency'])
            except KeyError:
                pass
            this_data.to_csv(os.path.join(root, coll.name + '.csv'), index=False)
        return root

    def import_data_from_csv(self):
        """Import CSV data into a new database"""
        for coll in [self.transactions_table, self.budget_table, self.accounts_table, self.categories_table]:
            for file_name in os.listdir():
                if file_name.endswith('.csv'):
                    if file_name[:-4] == coll.name:
                        df = pd.read_csv(file_name)
                        coll.insert_many(df.to_dict('records'))


if __name__ == '__main__':
    md = MaintainDatabase()
    md.export_data_to_csv()
