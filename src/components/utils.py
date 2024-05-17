from datetime import date, datetime
from dotenv import load_dotenv
import os
import sys

from maintain_transactions import MaintainDatabase
from maintain_transactions_csv import MaintainCSV

EXCLUDE_FROM_TABLE = ['_id', 'original description', 'currency']

PLOTLY_COLORS = [
    '#636EFA',
    '#EF553B',
    '#00CC96',
    '#AB63FA',
    '#FFA15A',
    '#19D3F3',
    '#FF6692',
    '#B6E880',
    '#FF97FF',
    '#FECB52',
]


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

# Instantiate data interface
print('Welcome to Budgie! \n\n'
      'To get started, open a web browser and go to http://127.0.0.1:8050/ \n\n')
load_dotenv()
if os.getenv("MONGO_HOST") is not None:
    MD = MaintainDatabase()
    print(f"Using Mongo data from {os.getenv('MONGO_HOST')}")
elif os.getenv("DATA_DIR") is not None:
    MD = MaintainCSV()
    print(f"Using CSV data from {os.getenv('DATA_DIR')}")
elif getattr(sys, 'frozen', False):
    MD = MaintainCSV()
    print(f"Using CSV data from default directory: {os.getcwd()}")
else:
    print("You must specify either MONGO_HOST or DATA_DIR in the .env file")
    quit()


def zero_params_dict():
    """Create empty dictionary with parameter keys.

    Returns: Dictionary with all parameters set to 0.

    """
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    return {'field_filter': 'Category', 'time_filter': 'This Month', 'filter_value': [], 'plot_type': 'bar',
            'start_date': datetime.strftime(start_of_month, '%Y-%m-%d'), 'end_date': datetime.strftime(today, '%Y-%m-%d')}


def update_layout_axes(fig_obj, showlegend=True):
    fig_obj.update_xaxes(showline=True, mirror=True, linewidth=1, linecolor=COLORS['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=COLORS['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=COLORS['light'].get('gridgray'))
    fig_obj.update_yaxes(showline=True, mirror=True, linewidth=1, linecolor=COLORS['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=COLORS['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=COLORS['light'].get('gridgray'))
    fig_obj.update_layout(
        font=dict(family='Arial', size=15),
        showlegend=showlegend,
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
        acc_list = list(MD.transactions_table.find().distinct('account name'))
        acc_list.extend(['Add new account...'])
    else:
        acc_list.extend(MD.transactions_table.find().distinct('account name'))

    try:  # Quick check for when there's actually no accounts available
        acc_list.remove('None')
    except ValueError:
        pass
    return acc_list


def get_color(i):
    """Get color for plotting from list of colors"""
    return PLOTLY_COLORS[i % len(PLOTLY_COLORS)]
