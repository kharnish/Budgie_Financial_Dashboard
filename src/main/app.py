"""
Author: Kelly Harnish, Code 8121
Date:  02 May 2021
"""
import os
import dash
import dash_bootstrap_components as dbc
from dash import Dash, callback, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pymongo
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
import dash_ag_grid as dag
import base64
from io import StringIO

from maintain_transactions import MaintainTransactions

load_dotenv()
client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
client = client_mongo[os.getenv("MONGO_DB")]
transactions_table = client[os.getenv("TRANSACTIONS_CLIENT")]
budget_table = client[os.getenv("BUDGET_CLIENT")]

external_stylesheets = ['assets/budgie_light.css', dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

EMPTY_TRANSACTION = pd.DataFrame.from_dict({'_id': [''], 'date': [datetime.today()], 'category': ['unknown'], 'description': ['No Available Data'],
                                            'amount': [0], 'account name': [''], 'notes': ['']})

MT = MaintainTransactions()

EXCLUDE_FROM_BUDGET = ['Transfer', 'Credit Card Payment']
# EXCLUDE_FROM_TABLE = ['original description', 'currency']
EXCLUDE_FROM_TABLE = ['_id', 'original description', 'currency']


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


def make_trends_plot(conf_dict):
    """Make plot object from waveform parameters.

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Plotly figure object.

    """
    def _sort_plot_data():
        def _sort_funct(val):
            return val['values']
        if len(transactions) == 0:
            # TODO Error, no transactions found for the given filters
            lab_val = {'Spending': {'labels': [0], 'values': [0]},
                       'Income': {'labels': [0], 'values': [0]}}
        else:
            lab_val = {'Spending': {'labels': [], 'values': []},
                       'Income': {'labels': [], 'values': []}}
            for cat, grp in transactions.groupby(conf_dict['field_filter'].lower()):
                inc_amount = grp['amount'][grp['amount'] > 0].sum()
                spd_amount = grp['amount'][grp['amount'] < 0].sum()
                if spd_amount:
                    lab_val['Spending']['labels'].append(cat)
                    lab_val['Spending']['values'].append(-spd_amount)
                if inc_amount:
                    lab_val['Income']['labels'].append(cat)
                    lab_val['Income']['values'].append(inc_amount)

        for spin in ['Spending', 'Income']:
            lab_val[spin]['values'], lab_val[spin]['labels'] = zip(*sorted(zip(lab_val[spin]['values'], lab_val[spin]['labels']), key=lambda x: x[0], reverse=True))
        return lab_val

    transactions = get_mongo_transactions(conf_dict)
    transactions = transactions[~transactions['category'].isin(EXCLUDE_FROM_BUDGET)]

    if conf_dict['plot_type'] == 'bar':
        fig_obj = go.Figure()
        lab_val = _sort_plot_data()
        for in_sp in ['Spending', 'Income']:
            for i in range(len(lab_val[in_sp]['values'])):
                fig_obj.add_trace(go.Bar(y=[in_sp], x=[lab_val[in_sp]['values'][i]], name=lab_val[in_sp]['labels'][i], orientation='h',
                                         meta=lab_val[in_sp]['labels'][i],
                                         hovertemplate="%{meta}<br>$%{x:.2f}<extra></extra>"))
        fig_obj.update_yaxes(title_text="Expenditures")

        fig_obj.update_xaxes(title_text="Amount ($)")
        fig_obj.update_layout(barmode='stack')

    elif conf_dict['plot_type'] == 'pie':
        fig_obj = make_subplots(rows=1, cols=2, subplot_titles=['Income', 'Spending'], specs=[[{'type': 'domain'}, {'type': 'domain'}]])
        lab_val = _sort_plot_data()
        # TODO try and figure out a better hover label for the plots
        fig_obj.add_trace(go.Pie(labels=lab_val['Income']['labels'], values=lab_val['Income']['values'], textinfo='percent+label',
                                 meta=lab_val['Income']['values'], hovertemplate="$%{meta:.2f}<extra></extra>"), 1, 1)
        fig_obj.add_trace(go.Pie(labels=lab_val['Spending']['labels'], values=lab_val['Spending']['values'], textinfo='percent+label',
                                 meta=lab_val['Spending']['values'], hovertemplate="$%{meta:.2f}<extra></extra>"), 1, 2)

    fig_obj.update_xaxes(showline=True, mirror=True, linewidth=1, linecolor=colors['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=colors['light'].get('gridgray'))
    fig_obj.update_yaxes(showline=True, mirror=True, linewidth=1, linecolor=colors['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=colors['light'].get('gridgray'))
    fig_obj.update_layout(
        font=dict(family='Arial', size=15),
        # showlegend=False,
        plot_bgcolor=colors['light'].get('background'),
        paper_bgcolor=colors['light'].get('background'),
        font_color=colors['light'].get('text'),
        margin_l=30, margin_r=30, margin_t=20, margin_b=20,
    )
    return fig_obj


def make_table(conf_dict):
    transactions = get_mongo_transactions(conf_dict)
    transactions['_id'] = [str(tid) for tid in transactions['_id']]
    transactions = transactions.sort_values('date', ascending=False)
    transactions['date'] = transactions['date'].dt.strftime('%m-%d-%Y')
    data = transactions.to_dict('records')
    columns = [{"field": i} for i in transactions.columns]

    # Update the column format for each column
    for col in columns:
        if col['field'] in EXCLUDE_FROM_TABLE:
            col['hide'] = True
        elif col['field'] == 'amount':
            col['valueFormatter'] = {"function": "d3.format('($.2f')(params.value)"}
            col['type'] = 'numericColumn'
            col['cellStyle'] = {"function": "params.value < 0 ? {'color': 'firebrick'} : {'color': 'seagreen'}"}
            col['filter'] = 'agNumberColumnFilter'
        elif col['field'] == 'category':
            col['width'] = 150
            col['editable'] = True
            col['cellEditor'] = 'agSelectCellEditor'
            col['cellEditorParams'] = {'values': get_categories_list()}
        elif col['field'] == 'description':
            col['width'] = 400
            col['editable'] = True
        elif col['field'] == 'account name':
            col['width'] = 300
        elif col['field'] == 'date':
            col['checkboxSelection'] = True
            col['headerCheckboxSelection'] = True
            col['headerCheckboxSelectionFilteredOnly'] = True
            col['filter'] = 'agDateColumnFilter'
    return {'data': data, 'columns': columns}


def get_accounts_list(extra=''):
    acc_list = []
    if extra == 'new':
        acc_list = list(transactions_table.find().distinct('account name'))
        acc_list.extend(['Add new account...'])
    else:
        acc_list.extend(transactions_table.find().distinct('account name'))
    return acc_list


def get_categories_list(extra=''):
    cat_list = []
    if extra == 'new':
        cat_list = list(transactions_table.find().distinct('category'))
        cat_list.extend(['Add new category...'])
    else:
        cat_list.extend(transactions_table.find().distinct('category'))
    return cat_list


def make_budget_plot(conf_dict):
    budget_dict = {}
    for item in budget_table.find():
        budget_dict[item['category']] = item['value']

    # TODO Limit the budget plot to only show one month
    #  Or make it show month-to-month for each category
    transactions = get_mongo_transactions(conf_dict)

    fig_obj = go.Figure()
    for cat in budget_dict.keys():
        spent = float(transactions[transactions['category'] == cat]['amount'].sum())
        percent = -100 * spent / budget_dict[cat]
        fig_obj.add_trace(go.Bar(y=[cat], x=[percent], name=cat, orientation='h', text=[f"$ {-spent:.2f}"], textposition="outside",
                                 meta=[f"$ {budget_dict[cat]:.2f}"],
                                 hovertemplate="Spent:       %{text}<br>Budgeted: %{meta}<extra></extra>"))
    fig_obj.update_xaxes(title_text="% Spent")

    fig_obj.add_vline(x=100, line_width=3, line_color=colors['light'].get('gridgray'))
    # TODO make a vertical line on each bar to show how far along you are in the month

    fig_obj.update_xaxes(showline=True, mirror=True, linewidth=1, linecolor=colors['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['light'].get('gridgray'),
                         showgrid=True, gridwidth=1, gridcolor=colors['light'].get('gridgray'))
    fig_obj.update_yaxes(showline=True, mirror=True, linewidth=1, linecolor=colors['light'].get('gridgray'),
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['light'].get('gridgray'),
                         showgrid=False, gridwidth=1, gridcolor=colors['light'].get('gridgray'))
    fig_obj.update_layout(
        font=dict(family='Arial', size=15),
        showlegend=False,
        plot_bgcolor=colors['light'].get('background'),
        paper_bgcolor=colors['light'].get('background'),
        font_color=colors['light'].get('text'),
        margin_l=30, margin_r=30, margin_t=20, margin_b=20,
    )

    return fig_obj


colors = {
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

########################################################################################

# Initialize parameters
current_config_dict = zero_params_dict()

# Make initial plot
fig = make_trends_plot(current_config_dict)

# Make initial table
tab = make_table(current_config_dict)

app.layout = html.Div(
    children=[
        dcc.Store(id='current-config-memory'),

        html.Div(style={'background-color': '#2C4864'},
                 children=[
                     html.Div(style={'width': 'auto', 'display': 'inline-block', 'padding': '25px 40px'},
                              children=[html.Img(id='logo', src="assets/parakeet.png", height="90px")]),
                     html.Div(style={'position': 'absolute', 'left': '145px', 'top': '60px'},
                              children=[html.H1(['Budgie Financial Dashboard'])]),
                 ]),

        html.Div(id="input-params", style={'width': '24%', 'float': 'left'},  # left column of options/inputs
                 children=[
                     dbc.Row([html.H4(style={'width': '100%', 'display': 'inline-block', 'padding': '10px 20px'},
                                      children=["Configurations"]),
                              html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '10px 20px'},
                                       children=["Sort By"]),
                              html.Div(style={'width': '54%', 'display': 'inline-block', 'padding': '0px',
                                              'vertical-align': 'middle'},
                                       children=[dcc.Dropdown(id='field-dropdown', value=current_config_dict['field_filter'],
                                                              clearable=False, searchable=False, className='dropdown',
                                                              options=['Category', 'Account Name'],
                                                              ),
                                                 ]
                                       ),
                              ]),
                     dbc.Row([html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '11px 20px'},
                                       children=['Select Filter']),
                              html.Div(style={'width': '54%', 'display': 'inline-block', 'padding': '0px',
                                              'vertical-align': 'middle'},
                                       children=[dcc.Dropdown(id='filter-dropdown', maxHeight=400, clearable=True,
                                                              searchable=True, className='dropdown', multi=True,
                                                              options=get_categories_list(),
                                                              )
                                                 ],
                                       ),
                              ]),
                     dbc.Row([html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '11px 20px'},
                                       children=['Time Window']),
                              html.Div(style={'width': '54%', 'display': 'inline-block', 'padding': '0px',
                                              'vertical-align': 'middle'},
                                       children=[dcc.Dropdown(id='time-dropdown', value=current_config_dict['time_filter'], maxHeight=400,
                                                              clearable=False, searchable=False, className='dropdown',
                                                              options=['This Month', 'Last Month', 'This Year', 'Last Year',
                                                                       'All Time', 'Custom'],
                                                              )
                                                 ],
                                       ),
                              ]),
                     html.Div(style={'display': 'inline-block'},
                              children=[dcc.DatePickerRange(
                                  id='date-range',
                                  min_date_allowed=date(2000, 1, 1),
                                  max_date_allowed=date.today(),
                                  initial_visible_month=date.today(),
                                  end_date=date.today()
                              )]),

                     html.I(id='config-input-text', style={'padding': '0px 20px 10px 21px'}),

                     html.Div('', style={'padding': '0px 20px 20px 20px'}),  # seems to work better than html.Br()
                     dbc.Row([
                         html.Div(style={'width': '95%', 'display': 'inline-block', 'padding': '11px 20px'},
                                  children=['Select Account to Upload Transactions  ',
                                            html.I(className="fa-solid fa-circle-info", id='help-icon'),
                                            dbc.Tooltip("Select the corresponding account for the transactions CSV file. "
                                                        "If the account doesn't exist in your database yet, select the 'Add New Account...' option at the bottom of the drop down.  "
                                                        "To load a transaction file which contains multiple accounts (i.e. from from Mint), "
                                                        "ensure there is an 'account_name' column and simply leave the 'New account name' blank and upload the file. "
                                                        "You can select multiple files to upload simultaneously for the same account. ",
                                                        target='help-icon',
                                                        placement='right',
                                                        style={'font-size': 14, 'maxWidth': 800, 'width': 800},
                                                        )]),
                         html.Br(),
                         html.Div(style={'width': '94%', 'display': 'inline-block', 'padding': '0 20px',
                                         'vertical-align': 'middle'},
                                  children=[dcc.Dropdown(id='account-dropdown', className='dropdown', placeholder="Select account...",
                                                         clearable=True, options=get_accounts_list('new'))],
                                  ),
                         html.Div(style={'display': 'inline-block', 'width': '90%', 'padding': '10px 20px'},
                                  children=[dcc.Input(id='account-input', type='text', style={'display': 'inline-block'},
                                                      placeholder='New account name')], ),
                         html.Div(style={'display': 'inline-block'},
                                  children=[dcc.Upload(id='upload-data', multiple=True,
                                                       children=[html.Button('Select Transaction CSV')])]),
                         html.I(id='upload-message',
                                style={'display': 'inline-block', 'padding': '0px 20px 10px 20px'}),
                         html.Div(style={'padding': '10px 20px', 'display': 'inline-block', 'float': 'right'},
                                  children=[html.Button(children=["Add Manual Transaction ", html.I(className="fa-solid fa-plus")], id="manual-button")]),
                         dbc.Modal(id="transaction-modal", is_open=False, children=[
                             dbc.ModalHeader(dbc.ModalTitle("Add New Transaction")),
                             dbc.ModalBody(children=[
                                 html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '5px 0'},
                                          children=['Transaction Date:', html.Br(),
                                                    dcc.DatePickerSingle(
                                                        id='transaction-date',
                                                        min_date_allowed=date(2000, 1, 1),
                                                        max_date_allowed=date.today(),
                                                        initial_visible_month=date.today(),
                                                    )]),
                                 html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                                          children=['Select Account:',
                                                    dcc.Dropdown(id='modal-account-dropdown', className='dropdown', clearable=True, placeholder='Select account...',
                                                                 style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                 options=get_accounts_list())]),
                                 html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                          children=['Transaction Amount:', html.Br(),
                                                    dcc.Input(id='transaction-value-input', type='number', placeholder='$ 0', style={'width': '100px'})]),
                                 html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                          children=['Description:', html.Br(),
                                                    dcc.Input(id='description-input', type='text', style={'display': 'inline-block'},
                                                              placeholder='Transaction description')]),
                                 html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                                          children=['Select Category:',
                                                    dcc.Dropdown(id='modal-category-dropdown', className='dropdown', clearable=True, placeholder='unknown',
                                                                 style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                 )]),
                                 html.Div([dcc.Input(id='modal-category-input', type='text', style={'display': 'inline-block'}, placeholder='New category')]),
                                 html.Div(id='modal-transaction-text', style={'display': 'inline-block', 'padding': '15px 0 0 0'}, ),
                             ]),
                             dbc.ModalFooter([
                                 html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="t-modal-cancel", className="ms-auto")]),
                                 dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                                            id="t-modal-submit", className="ms-auto", style={'float': 'left'})]
                             ),
                         ]),
                     ]),
                 ]),

        html.Div(
            id='tab-div', style={'padding': '20px'},  # tabs container
            children=[
                dcc.Tabs(id='selection_tabs', value='Trends', children=[
                    dcc.Tab(label="Trends", value='Trends', children=[
                        html.Div(style={'width': '100%', 'height': '700px', 'padding': '10px 20px', 'align': 'center'}, className='tab-body',
                                 children=[
                                     html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                                              children=[html.Button(style={'width': '75px', 'padding': '0'},
                                                                    children=["Pie ", html.I(className="fas fa-chart-pie")], id="pie-button")]),
                                     html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                                              children=[html.Button(style={'width': '75px', 'padding': '0'},
                                                                    children=["Bar ", html.I(className="fa-solid fa-chart-column")], id="bar-button")]),
                                     html.Div(id="trends-plot", style={'width': '100%', 'float': 'left', 'padding': '10px 0 0 0'},
                                              children=[dcc.Graph(id='trends-graph', style={'height': '600px'}, figure=fig)]),
                                     html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-1')
                                 ]),
                    ]),
                    dcc.Tab(label="Transactions", value='Transactions', children=[
                        html.Div(style={'width': '100%', 'float': 'left'}, className='tab-body',
                                 children=[
                                     html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                              children=[dbc.Button(children=["Edit ", html.I(className="fa-solid fa-pen-to-square")],
                                                                   style={'width': '80px'}, id="transact-edit", disabled=True, color="primary")]),
                                     dbc.Modal(id="edit-modal", is_open=False, children=[
                                         dbc.ModalHeader(dbc.ModalTitle("Edit Transactions")),
                                         dbc.ModalBody(children=[
                                             html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '5px 0'},
                                                      children=['New Transaction Date:', html.Br(),
                                                                dcc.DatePickerSingle(
                                                                    id='new-transaction-date',
                                                                    min_date_allowed=date(2000, 1, 1),
                                                                    max_date_allowed=date.today(),
                                                                    initial_visible_month=date.today(),
                                                                    placeholder='New date...'
                                                                )]),
                                             html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                                                      children=['Select New Account:',
                                                                dcc.Dropdown(id='new-account-dropdown', className='dropdown', clearable=True, placeholder='Select account...',
                                                                             style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                             options=get_accounts_list('new'))]),
                                             html.Div([dcc.Input(id='new-account-input', type='text', style={'display': 'inline-block'}, placeholder='New account name')]),
                                             html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                                      children=['New Transaction Amount:', html.Br(),
                                                                dcc.Input(id='new-transaction-value', type='number', placeholder='$ 0', style={'width': '100px'})]),
                                             html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                                      children=['New Description:', html.Br(),
                                                                dcc.Input(id='new-description-input', type='text', style={'display': 'inline-block', 'width': '400px'},
                                                                          placeholder='New Transaction Description')]),
                                             html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                                                      children=['Select New Category:',
                                                                dcc.Dropdown(id='new-category-dropdown', className='dropdown', clearable=True, placeholder='Select category...',
                                                                             style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                             )]),
                                             html.Div([dcc.Input(id='new-category-input', type='text', style={'display': 'inline-block'}, placeholder='New category')]),
                                             html.Div(id='new-modal-text', style={'display': 'inline-block', 'padding': '15px 0 0 0'}, ),
                                         ]),
                                         dbc.ModalFooter([
                                             html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="n-modal-cancel", className="ms-auto")]),
                                             dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                                                        id="n-modal-submit", className="ms-auto", style={'float': 'left'})]
                                         ),
                                     ]),
                                     html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                              children=[dbc.Button(children=["Delete ", html.I(className="fa-solid fa-trash-can")],
                                                                   style={'width': '100px'}, id="transact-delete", disabled=True, color="danger")]),
                                     html.I(className="fa-solid fa-circle-info", id='help-icon-2'),
                                     dbc.Tooltip("Shift + click to select a range of transactions, or ctrl + click to select multiple individual transactions. "
                                                 "Press the space bar to undo/redo your selection",
                                                 target='help-icon-2',
                                                 placement='right',
                                                 style={'font-size': 14},
                                                 ),

                                     dag.AgGrid(id="transactions-table",
                                                style={"height": '600px'},
                                                rowData=tab.get('data'),
                                                columnDefs=tab.get('columns'),
                                                columnSize="autoSize",
                                                defaultColDef={'filter': True, "resizable": True, 'sortable': True,
                                                               # "checkboxSelection": {"function": 'params.column == date'},
                                                               # "headerCheckboxSelection": {"function": 'params.column == date'},
                                                               # "headerCheckboxSelectionFilteredOnly": True,
                                                               },
                                                dashGridOptions={"rowSelection": "multiple"}  # , "suppressRowClickSelection": True},
                                                ),
                                 ]),
                        html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-2')
                    ]),
                    dcc.Tab(label="Budget", value='Budget', className='tab-body', children=[
                        html.Div(id="budget-plot", style={'width': '100%', 'float': 'left'}, className='tab-body',
                                 children=[
                                     dcc.Graph(style={'width': '95%', 'height': '95%', 'padding': '10px 20px 0 20px', 'align': 'center'},
                                               id='budget-graph', figure=fig),
                                     html.Div(style={'display': 'inline-block', 'padding': '5px 0 20px 20px', 'float': 'left', 'width': '95%'},
                                              children=[html.Button(id='new-budget-button', style={'width': 'auto'},
                                                                    children=['Add Or Update Budget ', html.I(className="fa-solid fa-plus")])]),
                                     dbc.Modal(id="budget-modal", is_open=False, children=[
                                         dbc.ModalHeader(dbc.ModalTitle("Add New Budget Item")),
                                         dbc.ModalBody(children=[
                                             html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '0px 5px 5px 0'},
                                                      children=['Select budget category:',
                                                                dcc.Dropdown(id='budget-category-dropdown', className='dropdown', clearable=True, placeholder='Select category...',
                                                                             style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                             options=[''])]),
                                             html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '5px 0'},
                                                      children=['Define budget amount:', html.Br(),
                                                                dcc.Input(id='budget-value-input', type='number', placeholder='$ 0', style={'width': '100px'})]),
                                             html.Div(style={'display': 'inline-block', 'float': 'right', 'position': 'absolute', 'bottom': 15, 'right': 10},
                                                      children=[dbc.Button(children=["Delete Budget ", html.I(className="fa-solid fa-trash-can")],
                                                                           id="modal-delete", color="danger", style={'float': 'right'})]),
                                             html.Div(id='modal-body-text', style={'display': 'inline-block', 'padding': '5px 0'}),
                                         ]),
                                         dbc.ModalFooter([
                                             html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="modal-cancel", className="ms-auto")]),
                                             dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                                                        id="modal-submit", className="ms-auto", style={'float': 'left'})]
                                         ),
                                     ]),
                                 ]),
                        html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-3')
                    ]),
                ]),
            ]),
    ]
)
# Layout app window


########################################################################################
@app.callback(
    Output('current-config-memory', 'data'),
    Output('field-dropdown', 'value'),
    Output('time-dropdown', 'value'),
    Output('filter-dropdown', 'options'),
    Output('date-range', 'style'),

    Input('field-dropdown', 'value'),
    Input('time-dropdown', 'value'),
    Input('filter-dropdown', 'value'),
    Input('current-config-memory', 'data'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('pie-button', 'n_clicks'),
    Input('bar-button', 'n_clicks'),
)
def update_plot_parameters(field_filter, time_filter, filter_values, curr_params, start_date, end_date, bar_button, pie_button):
    """Update current parameter dictionary and visible parameters based on selected bit or manual changes.

    Args:
        field_filter: Category filter
        time_filter: Time window filter
        filter_values: Filter to apply to transaction categories or accounts
        curr_params: Dictionary of current parameters
        end_date: end date of time window to show
        start_date: start date of time window to show

    Returns: Current parameters for specified bit.

    """
    # Determine what triggered the parameter update
    trigger = dash.callback_context.triggered[0]['prop_id']

    # Initialize params dict
    if curr_params is None:
        curr_params = zero_params_dict()
    new_params = curr_params

    if curr_params['time_filter'] == 'Custom':
        date_range_style = {'display': 'inline-block', 'padding': '15px 20px 15px 20px'}
    else:
        date_range_style = {'display': 'none'}

    # if one of the parameters, change them in the current dict
    if trigger == 'field-dropdown.value':
        new_params['field_filter'] = field_filter
    elif trigger == 'time-dropdown.value':
        new_params['time_filter'] = time_filter
        if time_filter == 'This Month':
            today = date.today()
            new_params['start_date'] = date(today.year, today.month, 1)
            new_params['end_date'] = date.today()
            date_range_style = {'display': 'none'}
        elif time_filter == 'Last Month':
            today = date.today()
            new_params['end_date'] = date(today.year, today.month, 1) - timedelta(days=1)
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'This Year':
            today = date.today()
            new_params['end_date'] = today
            new_params['start_date'] = date(today.year, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'Last Year':
            today = date.today()
            new_params['end_date'] = date(today.year, 1, 1) - timedelta(days=1)
            new_params['start_date'] = date(new_params['end_date'].year, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'All Time':
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(2000, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'Custom':
            date_range_style = {'display': 'inline-block', 'padding': '15px 20px 15px 20px'}
    elif 'date-range' in trigger:
        new_params['start_date'] = start_date
        new_params['end_date'] = end_date

    elif trigger == 'pie-button.n_clicks':
        curr_params['plot_type'] = 'pie'
    elif trigger == 'bar-button.n_clicks':
        curr_params['plot_type'] = 'bar'

    if new_params['field_filter'] == 'Account Name':
        filter_dropdown = get_accounts_list()
    else:
        filter_dropdown = get_categories_list()

    if trigger == 'filter-dropdown.value':
        new_params['filter_value'] = filter_values

    return new_params, new_params['field_filter'], new_params['time_filter'], filter_dropdown, date_range_style


@app.callback(
    Output('trends-graph', 'figure'),
    Output('transactions-table', 'rowData'),
    Output('transactions-table', 'columnDefs'),
    Output('budget-graph', 'figure'),
    Input('current-config-memory', 'data'),
    Input('selection_tabs', 'value')
)
def update_tab_data(current_params, which_tab):
    """Updates the waveform graph given the parameters of the waveform and creates plot.

    Args:
        current_params: Dictionary of original parameters from loaded config file.
        which_tab: The active tab to update the values of

    Returns:
        Figure object of plot
        Table data dictionary

    """
    if which_tab == 'Trends':
        tab_dict = make_table(zero_params_dict())
        return make_trends_plot(current_params), tab_dict['data'], tab_dict['columns'], make_budget_plot(zero_params_dict())
    elif which_tab == 'Transactions':
        tab_dict = make_table(current_params)
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], make_budget_plot(zero_params_dict())
    elif which_tab == 'Budget':
        tab_dict = make_table(zero_params_dict())
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], make_budget_plot(current_params)


@app.callback(
    Output("budget-modal", "is_open"),
    Output('budget-category-dropdown', 'options'),
    Output('budget-category-dropdown', 'value'),
    Output('budget-value-input', 'value'),
    Output('modal-body-text', 'children'),
    Output('modal-delete', 'style'),

    Input("new-budget-button", "n_clicks"),
    Input("modal-cancel", "n_clicks"),
    Input("modal-submit", "n_clicks"),
    Input('budget-category-dropdown', 'value'),
    Input('budget-value-input', 'value'),
    Input('modal-delete', 'n_clicks')
)
def toggle_budget_modal(open_modal, cancel, submit, budget_category, budget_value, delete_button):
    trigger = dash.callback_context.triggered[0]['prop_id']
    delete = {'display': 'none'}
    if trigger in ['new-budget-button.n_clicks', 'budget-category-dropdown.value', 'budget-value-input.value']:
        if budget_category != 'Select category...':
            bv = list(budget_table.find({'category': budget_category}))
            if len(bv) > 0:
                budget_value = budget_value if trigger == 'budget-value-input.value' else bv[0]['value']
                delete = {'float': 'right'}
            elif trigger == 'budget-category-dropdown.value':
                budget_value = '$ 0'
        return True, get_categories_list(), budget_category, budget_value, '', delete
    elif trigger == 'modal-submit.n_clicks':
        cat_list = list(transactions_table.find().distinct('category'))
        if budget_category != 'Select category...' and budget_value != '$ 0':
            MT.add_budget_item(budget_category, budget_value)
            return False, [], 'Select category...', '$ 0', '', delete
        else:
            return True, cat_list, budget_category, budget_value, 'You must specify category and budget amount for that category', delete
    elif trigger == 'modal-delete.n_clicks':
        MT.rm_budget_item(budget_category, budget_value)
        return False, [], 'Select category...', '$ 0', '', delete
    else:
        return False, [], 'Select category...', '$ 0', '', delete


@app.callback(
    Output("transaction-modal", "is_open"),
    Output('modal-category-dropdown', 'value'),
    Output('transaction-value-input', 'value'),
    Output('transaction-date', 'date'),
    Output('description-input', 'value'),
    Output('modal-account-dropdown', 'value'),
    Output('modal-transaction-text', 'children'),
    Output('modal-category-input', 'style'),
    Output('modal-category-dropdown', 'options'),

    Input("manual-button", "n_clicks"),
    Input("t-modal-cancel", "n_clicks"),
    Input("t-modal-submit", "n_clicks"),
    Input('modal-category-dropdown', 'value'),
    Input('transaction-value-input', 'value'),
    Input('transaction-date', 'date'),
    Input('description-input', 'value'),
    Input('modal-account-dropdown', 'value'),
    Input('modal-category-input', 'value')
)
def toggle_transaction_modal(open_modal, cancel, submit, category, amount, t_date, description, account, new_category):
    trigger = dash.callback_context.triggered[0]['prop_id']

    is_open = False
    msg_str = ''
    if category == 'Add new category...':
        cat_input = {'display': 'inline-block'}
    else:
        cat_input = {'display': 'none'}

    if trigger == 'manual-button.n_clicks':
        is_open = True
    elif trigger == 't-modal-submit.n_clicks':
        if amount != '$ 0' and description is not None and account is not None:
            if category == 'Add new category...':
                if new_category == '':
                    is_open = True
                    msg_str = dbc.Alert("You must specify a transaction category.", color="danger")
                else:
                    category = new_category
            MT.add_one_transaction(category, amount, t_date, description, account)
            category = 'unknown'
            amount = '$ 0'
            t_date = date.today()
            description = None
            account = None
        else:
            is_open = True
            msg_str = dbc.Alert("You must specify all values.", color="danger")
    elif trigger in ['modal-category-dropdown.value', 'transaction-value-input.value', 'transaction-date.date', 'description-input.value',
                     'modal-account-dropdown.value', 'modal-category-input.value']:
        is_open = True
    else:
        category = 'unknown'
        amount = '$ 0'
        t_date = date.today()
        description = None
        account = None

    return is_open, category, amount, t_date, description, account, msg_str, cat_input, get_categories_list('new')


@app.callback(
    Output('upload-message', 'children'),
    Output('upload-data', 'style'),
    Output('account-input', 'style'),
    Output('account-dropdown', 'options'),
    Input('account-dropdown', 'value'),
    Input('upload-data', 'contents'),
    Input('account-input', 'value'),
)
def parse_upload_transaction_file(account, loaded_file, new_account):
    """When button is clicked, checks for valid current file then writes new config file with updated parameters.

    Args:
        account: Account name for transactions
        loaded_file: contents of uploaded transactions file

    Returns: String if the file is able to be written or not.

    """
    upload_button = {'display': 'none'}
    msg = ''
    account_input = {'display': 'none'}
    acc_list = get_accounts_list('new')

    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'account-dropdown.value':
        if account == 'Add new account...':
            account_input = {'display': 'inline-block', 'width': '100%'}
        elif account is not None:
            upload_button = {'display': 'inline-block', 'padding': '0px 20px 20px 20px'}
    elif trigger == 'upload-data.contents':
        if account == 'Add new account...':
            account = new_account
        msg = []
        for i, file in enumerate(loaded_file):
            decodedBytes = base64.b64decode(file.split(',')[-1])
            file_text = decodedBytes.decode("utf-8")
            try:
                m = pd.read_csv(StringIO(file_text))
            except:
                msg.append(f"File {i + 1}: File must be in CSV format\n")
                msg.append(html.Br())
                continue

            results = MT.add_transactions(m, account)
            if isinstance(results, int):
                if results == 0:
                    msg.append(f"File {i + 1}: No new transactions to upload")
                    msg.append(html.Br())
                else:
                    msg.append(f"File {i + 1}: Successfully uploaded {results} new transactions\n")
                    msg.append(html.Br())
            else:
                msg.append(f"File {i + 1}: {results}\n")
                msg.append(html.Br())
    elif trigger == 'account-input.value':
        account_input = {'display': 'inline-block', 'width': '100%'}
        upload_button = {'display': 'inline-block', 'padding': '0px 20px 20px 20px'}

    return msg, upload_button, account_input, acc_list


@app.callback(
    Output('blank-space-1', 'children'),
    Input('transactions-table', 'cellValueChanged')
)
def update_table_data(change_data):
    if change_data:
        MT.edit_transaction(change_data)
    return ''


@app.callback(
    Output('transact-delete', 'disabled'),
    Output('transact-edit', 'disabled'),
    Output("edit-modal", "is_open"),
    Output('new-category-dropdown', 'value'),
    Output('new-category-input', 'style'),
    Output('new-category-input', 'value'),
    Output('new-category-dropdown', 'options'),
    Output('new-transaction-value', 'value'),
    Output('new-transaction-date', 'date'),
    Output('new-description-input', 'value'),
    Output('new-account-dropdown', 'value'),
    Output('new-account-input', 'style'),
    Output('new-account-input', 'value'),
    Output('new-modal-text', 'children'),

    Input('transact-edit', 'n_clicks'),
    Input('transact-delete', 'n_clicks'),
    Input('transactions-table', 'selectedRows'),
    Input("n-modal-cancel", "n_clicks"),
    Input("n-modal-submit", "n_clicks"),
    Input('new-category-dropdown', 'value'),
    Input('new-category-input', 'value'),
    Input('new-transaction-value', 'value'),
    Input('new-transaction-date', 'date'),
    Input('new-description-input', 'value'),
    Input('new-account-dropdown', 'value'),
    Input('new-account-input', 'value'),
)
def bulk_update_table(edit_button, delete_button, row_data, cancel, submit, category, new_category, amount, t_date, description, account, new_account):
    trigger = dash.callback_context.triggered[0]['prop_id']

    is_open = False
    msg_str = ''
    enabled = True

    if category == 'Add new category...':
        cat_style = {'display': 'inline-block', 'width': '400px'}
    else:
        cat_style = {'display': 'none'}
    if account == 'Add new account...':
        account_style = {'display': 'inline-block', 'width': '400px'}
    else:
        account_style = {'display': 'none'}

    if trigger == 'transactions-table.selectedRows' and (row_data is None or len(row_data) > 0):
        enabled = False

    elif trigger == 'transact-delete.n_clicks':
        MT.delete_transaction(row_data)

    elif trigger == 'transact-edit.n_clicks':
        is_open = True
    elif trigger == 'n-modal-submit.n_clicks':
        update_dict = {}
        if t_date is not None:
            update_dict['date'] = t_date
        if account is not None:
            if account == 'Add new account...':
                if new_account is None:
                    is_open = True
                    msg_str = dbc.Alert("You must specify a transaction account.", color="danger")
                else:
                    update_dict['account name'] = new_account
            else:
                update_dict['account name'] = account
        if amount is not None:
            update_dict['amount'] = amount
        if description is not None:
            update_dict['description'] = description
        if category is not None:
            if category == 'Add new category...':
                if new_category is None:
                    is_open = True
                    msg_str = dbc.Alert("You must specify a transaction category.", color="danger")
                else:
                    update_dict['category'] = new_category
            else:
                update_dict['category'] = category

        if len(update_dict) != 0:
            for r in row_data:
                for key, val in update_dict.items():
                    r[key] = val
            MT.edit_many_transactions(row_data)
            category = None
            new_category = None
            amount = None
            t_date = None
            description = None
            account = None
            new_account = None
        else:
            is_open = True
            msg_str = dbc.Alert("You must specify at least one value to update.", color="danger") if msg_str == '' else msg_str

    elif trigger in ['new-category-dropdown.value', 'new-transaction-value.value', 'new-transaction-date.date', 'new-description-input.value',
                     'new-account-dropdown.value', 'new-account-input.value', 'new-category-input.value']:
        is_open = True
    else:
        category = None
        new_category = None
        amount = None
        t_date = None
        description = None
        account = None
        new_account = None

    return enabled, enabled, is_open, category, cat_style, new_category, get_categories_list('new'), amount, t_date, description, account, account_style,  new_account, msg_str


if __name__ == '__main__':
    # Use host='0.0.0.0' for running in Docker and host='127.0.0.1' for running in PyCharm
    app.run_server(host='127.0.0.1', port=8050, debug=True)
