import base64
import dash
from dash import callback, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from io import StringIO

import pandas as pd

from utils import zero_params_dict, get_accounts_list, get_categories_list, MT

configurations_sidebar = html.Div(id="input-params", style={'width': '24%', 'float': 'left'},  # left column of options/inputs
                                  children=[
                                      dbc.Row([html.H4(style={'width': '100%', 'display': 'inline-block', 'padding': '10px 20px'},
                                                       children=["Configurations"]),
                                               html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '10px 20px'},
                                                        children=["Sort By"]),
                                               html.Div(style={'width': '54%', 'display': 'inline-block', 'padding': '0px',
                                                               'vertical-align': 'middle'},
                                                        children=[dcc.Dropdown(id='field-dropdown', value=zero_params_dict()['field_filter'],
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
                                                        children=[dcc.Dropdown(id='time-dropdown', value=zero_params_dict()['time_filter'], maxHeight=400,
                                                                               clearable=False, searchable=False, className='dropdown',
                                                                               options=['This Month', 'Last Month', 'Last 3 Months', 'This Year', 'Last Year',
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
                                                           children=['Select Account*',
                                                                     dcc.Dropdown(id='modal-account-dropdown', className='dropdown', clearable=True, placeholder='Select account...',
                                                                                  style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                                  options=get_accounts_list())]),
                                                  html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                                           children=['Transaction Amount*', html.Br(),
                                                                     dcc.Input(id='transaction-value-input', type='number', placeholder='$ 0', style={'width': '100px'})]),
                                                  html.Div(style={'display': 'inline-block', 'width': '400px', 'padding': '5px 0'},
                                                           children=['Description*', html.Br(),
                                                                     dcc.Input(id='description-input', type='text', style={'display': 'inline-block', 'width': '100%'},
                                                                               placeholder='Transaction description')]),
                                                  html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                                                           children=['Select Category',
                                                                     dcc.Dropdown(id='modal-category-dropdown', className='dropdown', clearable=True, placeholder='unknown',
                                                                                  style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                                                  )]),
                                                  html.Div([dcc.Input(id='modal-category-input', type='text', style={'display': 'inline-block'}, placeholder='New category')]),
                                                  html.Div(style={'display': 'inline-block', 'width': '400px', 'padding': '5px 0'},
                                                           children=['Note', html.Br(),
                                                                     dcc.Input(id='note-input', type='text', style={'display': 'inline-block', 'width': '100%'},
                                                                               placeholder='Transaction note')]),
                                                  html.Div(id='modal-transaction-text', style={'display': 'inline-block', 'padding': '15px 0 0 0'}, ),
                                              ]),
                                              dbc.ModalFooter([
                                                  html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="t-modal-cancel", className="ms-auto")]),
                                                  dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                                                             id="t-modal-submit", className="ms-auto", style={'float': 'left'})]
                                              ),
                                          ]),
                                      ]),
                                  ])


@callback(
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
def update_parameters(field_filter, time_filter, filter_values, curr_params, start_date, end_date, bar_button, pie_button):
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
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'Last Month':
            today = date.today()
            new_params['end_date'] = date(today.year, today.month, 1) - timedelta(days=1)
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'Last 3 Months':
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1) - relativedelta(months=3)
            date_range_style = {'display': 'none'}
        elif time_filter == 'This Year':
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(new_params['end_date'].year, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == 'Last Year':
            new_params['end_date'] = date(date.today().year, 1, 1) - timedelta(days=1)
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


@callback(
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
        loaded_file: Contents of uploaded transactions file
        new_account: New account name text input

    Returns: String with message about if the transactions were uploaded

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
            if new_account:
                MT.add_account(new_account)
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