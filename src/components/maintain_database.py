from bson.objectid import ObjectId
from datetime import datetime, timedelta
from difflib import get_close_matches
from dotenv import load_dotenv
import numpy as np
import os
import pandas as pd
import pymongo

TRANSACTIONS_CLIENT = 'transactions'
BUDGET_CLIENT = 'budget'
ACCOUNTS_CLIENT = 'accounts'
CATEGORIES_CLIENT = 'categories'

EMPTY_TRANSACTION = pd.DataFrame.from_dict({'_id': ['None'], 'transaction date': [datetime.today()], 'posted date': [datetime.today()], 'category': ['unknown'],
                                            'description': ['No Available Data'], 'amount': [0], 'account name': ['None'], 'notes': ['None']})


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
        debug = False  # Option to print more robust debug statements

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
            df = df.rename(columns={'Datetime': 'posted date', 'Note': 'description', 'Amount (total)': 'amount'})
            df['amount'] = [''.join(val.split(' $')) for val in df['amount']]
            df['amount'] = df['amount'].astype(float)
            df['posted date'] = [val.split('T')[0] for val in df['posted date']]
            # TODO 'replace' is depreciated, so update this
            source = df['Funding Source'].replace({'Venmo balance': np.nan})
            if any(~source.isna()):
                df['notes'] = 'Source: ' + source
            # Add description if it's a transfer out of Venmo
            for i in np.argwhere(df['Type'] == 'Standard Transfer'):
                df.loc[i, 'description'] = f"Transfer to {df.loc[i, 'Destination'].values[0]}"

        # Standardize sheet columns
        df = df.dropna(axis='columns', how='all')
        df.columns = [col.lower().replace('_', ' ') for col in df.columns]

        # Ensure both Transaction and Posted dates
        df = df.rename(columns={'posting date': 'posted date', 'post date': 'posted date',  'booking date': 'posted date'})
        if 'transaction date' in df.columns and 'posted date' not in df.columns:
            df['posted date'] = df['transaction date']
        elif 'posted date' in df.columns and 'transaction date' not in df.columns:
            df['transaction date'] = df['posted date']
        df['posted date'] = pd.to_datetime(df['posted date']).map(lambda x: x.replace(tzinfo=None))
        df['transaction date'] = pd.to_datetime(df['transaction date']).map(lambda x: x.replace(tzinfo=None))

        # Description
        if 'original name' in df.columns:
            df = df.rename(columns={'payee': 'description', 'original name': 'original description'})
        else:
            df = df.rename(columns={'payee': 'description'})
        if 'original description' not in df.columns:
            try:
                df['original description'] = df['description']
            except KeyError:
                return 'Error: Must provide "description" column in the CSV'

        # Amount credit/debit
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

        # Multiple accounts in one CSV
        account_labels = True if 'account name' in df.columns else False
        if not account_labels and not account:
            return 'Error: Must provide account name if not given in CSV'

        # Add blank category column if there is none, but keep it default if loading an exported Budgie CSV
        if account is not None:
            if 'account name' in df.columns:
                pass
            else:
                df['category'] = ''

        # Replace NA with empty string and remove transactions with no date
        df = df.fillna('')
        df = df.dropna(subset='posted date', axis='index')

        # If only one account for that file, get autocategorization categories from previous data
        if account:
            self._get_categories(account)

        # Check to ensure all the necessary columns were converted
        necessary_columns = ['transaction date', 'posted date', 'description', 'amount']
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

            duplicates = self.transactions_table.find({'amount': row['amount'], 'account name': account}).sort({'posted date': -1})
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

                    if dup['posted date'] > row['posted date']:
                        continue

                    # Check various parameters to see if it's a duplicate or not
                    if dup['posted date'] == row['posted date']:
                        # Matching amount, posted date, and account are good enough to declare duplicate
                        if debug:
                            if dup['transaction date'] == row['transaction date']:
                                # but keep extra options if you need to debug
                                if dup['original description'] == row['original description']:
                                    # It's an exact match for amount, description, and date, so definitely a duplicate
                                    break
                                else:
                                    print(f"Did not insert possible duplicate transaction, but check different description: ${dup['amount']:.2f} \n"
                                          f"       New: {row['posted date']}, {row['original description']}\n"
                                          f"  Existing: {dup['posted date']}, {dup['original description']}")
                                    break
                            else:
                                # So far, exact match for posted date and amount, so check transaction date and description
                                print(f"Did not insert possible duplicate transaction, but check different transaction date and description:\n"
                                      f"    Posted: {row['posted date']}, ${dup['amount']:.2f} \n"
                                      f"       New: {row['transaction date']}, {row['original description']}\n"
                                      f"  Existing: {dup['transaction date']}, {dup['original description']}")
                                break
                        break
                    else:
                        if dup['transaction date'] == row['transaction date']:
                            # It's a match for amount and transaction date, but not posted date, so check description
                            matches = get_close_matches(row['original description'], [dup['original description']], cutoff=0.35)
                            if matches:
                                print(f"Did not insert possible duplicate item: ${dup['amount']:.2f}\n"
                                      f"       New: {row['posted date']}, {row['original description']}\n"
                                      f"  Existing: {dup['posted date']}, {dup['original description']}")
                                break
                            else:
                                transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                                if row['posted date'] - now > timedelta(days=30):
                                    print(f"Inserted transaction from over a month ago: {row['posted date']}, {row['original description']}, ${row['amount']:.2f}")
                                print(f"Inserted potential duplicate item: ${dup['amount']:.2f}\n"
                                      f"       New: {row['posted date']}, {row['original description']}\n"
                                      f"  Existing: {dup['posted date']}, {dup['original description']}")
                                break

                        else:
                            # Neither posted nor transaction dates match, so not a duplicate
                            transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                            if row['posted date'] - now > timedelta(days=30):
                                print(f"Inserted transaction from over a month ago: {row['posted date']}, {row['original description']}, ${row['amount']:.2f}")
                            break

            else:
                # There's no match, so get the category and add the transaction
                transaction_list.append(self._make_transaction_dict(row, self._autocategorize(row), account))
                if (row['posted date'] - now) > timedelta(days=30):
                    print(f"Inserted transaction from over a month ago: {row['posted date']}, {row['original description']}, ${row['amount']:.2f}")

        return transaction_list

    def add_one_transaction(self, category, amount, t_date, p_date, description, account, note):
        """Add a single manual transaction to the database"""
        transaction = {'transaction date': datetime.strptime(t_date, '%Y-%m-%d'),
                       'posted date': datetime.strptime(p_date, '%Y-%m-%d'),
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
        default_transaction = {'transaction date': td['transaction date'],
                               'posted date': td['posted date'],
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
                'posted date': {'$last': '$posted date'},
                'cat': {'$last': '$category'}}}
        ]))
        self.autocategories = {}
        for cat in k:
            self.autocategories[cat['_id']] = {'category': cat['cat'], 'posted date': cat['posted date']}

    def _autocategorize(self, row):
        """Check with all the known descriptions if there are any close, and if so, use the last known category"""
        try:
            matches = get_close_matches(row['original description'], self.autocategories.keys(), cutoff=0.7)
            matches_data = [self.autocategories[match] for match in matches]
            i_most_recent = np.argmax([cat['posted date'] for cat in matches_data])
            return matches_data[i_most_recent]['category']
        except (ValueError, AttributeError):
            return row['category'] if row['category'] != '' else 'unknown'

    def query_transactions(self, conf_dict):
        """Query Mongo according to configuration dict parameters

        Args:
            conf_dict: Dictionary of the configuration parameters.

        Returns: Pandas Dataframe of transactions
        """
        if len(conf_dict['filter_value']['Category']) == 0 and len(conf_dict['filter_value']['Account Name']) == 0:
            mongo_filter = {}
        else:
            mongo_filter = {}
            for val in conf_dict['field_filter']:
                if len(conf_dict['filter_value'][val]) > 0:
                    mongo_filter[val.lower()] = {'$in': conf_dict['filter_value'][val]}

        # If filtering by category, include parent as well
        try:
            mongo_filter['category']['$in'].extend(self.get_children_categories_list(conf_dict['filter_value'][val]))
        except KeyError:
            pass

        transactions = pd.DataFrame(self.transactions_table.find({
            'posted date': {
                '$gte': datetime.strptime(conf_dict['start_date'], '%Y-%m-%d'),
                '$lte': datetime.strptime(conf_dict['end_date'], '%Y-%m-%d')},
            **mongo_filter}))
        if len(transactions) == 0:
            transactions = EMPTY_TRANSACTION

        return transactions

    def get_oldest_transaction(self):
        return list(self.transactions_table.find().sort({'posted date': 1}).limit(1))[0]['posted date'].date()

    def edit_transaction(self, change_dict):
        """Update transaction based on edits in Transaction table"""
        change_dict[0]['data']['transaction date'] = datetime.strptime(change_dict[0]['data']['transaction date'], '%m-%d-%Y')
        change_dict[0]['data']['posted date'] = datetime.strptime(change_dict[0]['data']['posted date'], '%m-%d-%Y')
        new_dict = change_dict[0]['data']
        new_dict.pop('_id')
        old_dict = change_dict[0]['data'].copy()
        old_dict[change_dict[0]['colId']] = change_dict[0]['oldValue']
        return self.transactions_table.update_one(old_dict, {'$set': new_dict})

    def edit_many_transactions(self, transaction_list):
        """Edit data for multiple transactions at one time"""
        for new_trans in transaction_list:
            try:
                new_trans['transaction date'] = datetime.strptime(new_trans['transaction date'], '%Y-%m-%d')
                new_trans['posted date'] = datetime.strptime(new_trans['posted date'], '%Y-%m-%d')
            except ValueError:
                new_trans['transaction date'] = datetime.strptime(new_trans['transaction date'], '%m-%d-%Y')
                new_trans['posted date'] = datetime.strptime(new_trans['posted date'], '%m-%d-%Y')
            tid = new_trans.pop('_id')
            self.transactions_table.update_one({'_id': ObjectId(tid)}, {'$set': new_trans})

    def delete_transaction(self, transaction_dict):
        """Delete a list of transactions from the Transactions table"""
        for trans in transaction_dict:
            trans.pop('_id')
            try:
                trans['transaction date'] = datetime.strptime(trans['transaction date'], '%m-%d-%Y')
                trans['posted date'] = datetime.strptime(trans['posted date'], '%m-%d-%Y')
            except TypeError:
                # The date is already a datetime object
                pass
            self.transactions_table.delete_one(trans)

    """====== Budget ======"""
    def add_budget_item(self, category, value):
        """Add new budget item in database with category and monthly value"""
        existing = list(self.budget_table.find({'category': category}))
        if len(existing) == 1:
            self.budget_table.update_one({'category': category}, {"$set": {'value': value}})
        else:
            parent = self.categories_table.find_one({'category name': category})
            self.budget_table.insert_one({'category': category, 'value': value, 'is_parent': True if parent is None else None})
        self.update_parent_budget(category)

    def update_parent_budget(self, category):
        # Check if there's a parent budget, and if so, update it
        try:
            parent = self.categories_table.find_one({'category name': category})['parent']
            if self.get_budget_amount(parent) != 0:
                new_group_value = self.get_budget_amount(self.get_children_categories_list(parent))
                self.budget_table.update_one({'category': parent}, {'$set': {'value': new_group_value}})
        except IndexError:
            pass

    def get_budget_dict(self):
        """Get dictionary of all positive and negative budget line items, along with all grouped budgets"""
        pos_dict = {}
        neg_dict = {}
        grp_dict = {}
        for item in self.budget_table.find():
            try:
                if item['is_parent']:
                    grp_dict[item['category']] = item['value']
                    continue
            except KeyError:
                pass
            if item['value'] > 0:
                pos_dict[item['category']] = item['value']
            else:
                neg_dict[item['category']] = item['value']
        return pos_dict, neg_dict, grp_dict

    def get_budget_amount(self, category):
        if isinstance(category, str):
            try:
                return list(self.budget_table.find({'category': category}))[0]['value']
            except IndexError:
                return 0
        elif isinstance(category, list):
            budget_value = 0
            for child_cat in category:
                # Get the total budgeted amount for all child categories
                budget_value += self.get_budget_amount(child_cat)
            return budget_value

    def rm_budget_item(self, category, value):
        """Delete budget item in database"""
        return self.budget_table.delete_one({'category': category, 'value': value})

    """====== Account ======"""
    def add_account(self, account_name, status='open', initial_balance=0):
        """Add new account in database with current status and beginning balance for net worth"""
        return self.accounts_table.insert_one({'account name': account_name, 'status': status, 'initial balance': initial_balance})

    def edit_account(self, change_dict):
        """Update accounts (and transactions, if applicable) based on edits in Accounts table"""
        new_dict = change_dict['data']
        new_dict.pop('_id')
        old_dict = change_dict['data'].copy()
        old_dict[change_dict['colId']] = change_dict['oldValue']
        if old_dict['account name'] != change_dict['data']['account name']:
            self.transactions_table.update_many({'account name': old_dict['account name']}, {'$set': {'account name': new_dict['account name']}})
        return self.accounts_table.update_one(old_dict, {'$set': new_dict})

    def delete_account(self, row_data):
        """Delete account in database and all associated transactions"""
        rm_t = self.transactions_table.find({'account name': row_data['account name']})
        self.delete_transaction(rm_t)
        row_data.pop('_id')
        return self.accounts_table.delete_one(row_data)

    """====== Category ======"""
    def add_category(self, category_name, category_parent=None):
        """Add new category in database ... """
        return self.categories_table.insert_one({'parent': category_parent, 'category name': category_name, 'hidden': False})

    def edit_category(self, change_dict):
        """Update category data based on edits in Categories table"""
        new_dict = change_dict['data']
        new_dict.pop('_id')
        old_dict = change_dict['data'].copy()
        old_dict[change_dict['colId']] = change_dict['oldValue']
        if old_dict['category name'] != change_dict['data']['category name']:
            self.transactions_table.update_many({'category': old_dict['category name']}, {'$set': {'category': new_dict['category name']}})
        return self.categories_table.update_one(old_dict, {'$set': new_dict})

    def get_categories_list(self, extra=''):
        """Get list of all categories with an associated transaction

        Parameter to add an additional "Add new category..." option
        """
        try:
            cat_list = []
            if extra == 'new':
                cat_list = list(self.transactions_table.find().distinct('category'))
                cat_list.extend(['Add new category...'])
            elif extra == 'parent':
                cat_list = list(self.transactions_table.find().distinct('category'))
                cat_list.extend(list(self.categories_table.find().distinct('parent')))
                # Remove NANs to allow for sorting strings
                try:
                    cat_list.remove(None)
                except ValueError:
                    pass
                cat_list = sorted(cat_list)
            elif extra == 'parent_only':
                cat_list = list(self.categories_table.find().distinct('parent'))
                # Remove NANs to allow for sorting strings
                try:
                    cat_list.remove(None)
                except ValueError:
                    pass
                cat_list = sorted(cat_list)
            else:
                cat_list.extend(self.transactions_table.find().distinct('category'))
        except pymongo.errors.ServerSelectionTimeoutError as e:
            print(f"Pymongo Timeout Error: {e}")
            exit()
        return cat_list

    def get_children_categories_list(self, parent=None):
        if isinstance(parent, list):
            children = []
            for par in parent:
                children.extend([item['category name'] for item in list(self.categories_table.find({'parent': par}))])
            return children
        else:
            return [item['category name'] for item in list(self.categories_table.find({'parent': parent}))]

    def get_hide_from_trends(self):
        """Get list of all categories hidden from trends"""
        return [row['category name'] for row in self.categories_table.find({'hidden': True})]

    def delete_category(self, row_data):
        """Delete category in database"""
        self.transactions_table.update_many({'category': row_data['category name']}, {'$set': {'category': 'unknown'}})
        if row_data['parent'] == '':
            row_data['parent'] = None
        row_data.pop('_id')
        return self.categories_table.delete_one(row_data)

    """====== Overall ======"""
    def export_data_to_csv(self, root=None):
        """Save database data to CSV files"""
        load_dotenv()
        root = os.getenv('BACKUP_DIR') if root is None else root
        os.makedirs(root, exist_ok=True)
        for coll in [self.transactions_table, self.budget_table, self.accounts_table, self.categories_table]:
            data = coll.find()
            this_data = pd.DataFrame(data)
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
