from datetime import date, datetime
from dotenv import load_dotenv
import os
import pandas as pd
import pymongo

from maintain_transactions import MaintainDatabase


load_dotenv()
client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
client = client_mongo[os.getenv("MONGO_DB")]
transactions_table = client[os.getenv("TRANSACTIONS_CLIENT")]
budget_table = client[os.getenv("BUDGET_CLIENT")]
accounts_table = client[os.getenv("ACCOUNTS_CLIENT")]

MT = MaintainDatabase()

EMPTY_TRANSACTION = pd.DataFrame.from_dict({'_id': [''], 'date': [datetime.today()], 'category': ['unknown'], 'description': ['No Available Data'],
                                            'amount': [0], 'account name': [''], 'notes': ['']})
EXCLUDE_FROM_BUDGET = ['Transfer', 'Credit Card Payment']
EXCLUDE_FROM_TABLE = ['_id', 'original description', 'currency']

COLORS = {
    'light': {
        'gridgray': '#646464',
        'yellow': '#faec59',
        'background': 'white',
        'text': '#162432',
    },
    'dark': {
        'background': '#0a1429',
        'linegray': '#7f7f7f',
        'text': '#EAEAEA',
    }
}


def zero_params_dict():
    """Create empty dictionary with parameter keys.

    Returns: Dictionary with all parameters set to 0.

    """
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    return {'field_filter': 'Category', 'time_filter': 'This Month', 'filter_value': [], 'plot_type': 'bar',
            'start_date': datetime.strftime(start_of_month, '%Y-%m-%d'), 'end_date': datetime.strftime(today, '%Y-%m-%d')}


def get_mongo_transactions(conf_dict):
    """Query Mongo according to configuration dict parameters

    Args:
         conf_dict:

    Returns: Pandas Dataframe of transactions
    """
    if len(conf_dict['filter_value']) == 0:
        mongo_filter = {}
    else:
        mongo_filter = {conf_dict['field_filter'].lower(): {'$in': conf_dict['filter_value']}}

    transactions = pd.DataFrame(transactions_table.find({
        'date': {
            '$gte': datetime.strptime(conf_dict['start_date'], '%Y-%m-%d'),
            '$lte': datetime.strptime(conf_dict['end_date'], '%Y-%m-%d')},
        **mongo_filter}))
    if len(transactions) == 0:
        transactions = EMPTY_TRANSACTION

    return transactions


def update_layout_axes(fig_obj):
    fig_obj.update_xaxes(showline=True, mirror=True, linewidth=1, linecolor=COLORS['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=COLORS['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=COLORS['light'].get('gridgray'))
    fig_obj.update_yaxes(showline=True, mirror=True, linewidth=1, linecolor=COLORS['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=COLORS['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=COLORS['light'].get('gridgray'))
    fig_obj.update_layout(
        font=dict(family='Arial', size=15),
        plot_bgcolor=COLORS['light'].get('background'),
        paper_bgcolor=COLORS['light'].get('background'),
        font_color=COLORS['light'].get('text'),
        margin_l=30, margin_r=30, margin_t=20, margin_b=20,
    )


def get_accounts_list(extra=''):
    """Get list of all accounts with an associated transaction

    Parameter to add an additional "Add new account..." option
    """
    acc_list = []
    if extra == 'new':
        acc_list = list(transactions_table.find().distinct('account name'))
        acc_list.extend(['Add new account...'])
    else:
        acc_list.extend(transactions_table.find().distinct('account name'))
    return acc_list


def get_categories_list(extra=''):
    """Get list of all categories with an associated transaction

    Parameter to add an additional "Add new category..." option
    """
    cat_list = []
    if extra == 'new':
        cat_list = list(transactions_table.find().distinct('category'))
        cat_list.extend(['Add new category...'])
    else:
        cat_list.extend(transactions_table.find().distinct('category'))
    return cat_list
