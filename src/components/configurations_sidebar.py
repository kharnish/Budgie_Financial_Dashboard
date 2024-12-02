import base64
import dash
from dash import callback, dcc, html, Input, Output, no_update
import dash_bootstrap_components as dbc
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from io import StringIO
import os
import pandas as pd

<<<<<<< Updated upstream
from utils import zero_params_dict, get_accounts_list, get_categories_list, MD
=======
from components.utils import zero_params_dict, get_accounts_list, MD
>>>>>>> Stashed changes

configurations_sidebar = html.Div(
    id="input-params", style={'width': '24%', 'float': 'left'},  # left column of options/inputs
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
                 html.Div(style={'width': '54%', 'display': 'inline-block', 'padding': '0 0 1px 0',
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
                                                 options=['This Month', 'Last Month', 'Last 3 Months', 'Last 6 Months', 'This Year', 'Last Year',
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
                               dbc.Tooltip(children=["Select the corresponding account for the transactions CSV file. ", html.Br(),
                                                     "If the account doesn't exist in your database yet, select the 'Add New Account...' option at the bottom of the drop down. ",
                                                     html.Br(),
                                                     "To load a transaction file which contains multiple accounts (i.e. from from Mint), "
                                                     "ensure there is an 'account_name' column and simply leave the 'New account name' blank and upload the file. ",
                                                     html.Br(),
                                                     "You can select multiple files to upload simultaneously for the same account. "],
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
            html.Div(style={'display': 'inline-block', 'padding': '5px 20px 0 20px'},
                     children=[dcc.Input(id='account-input', type='text', style={'display': 'inline-block'},
                                         placeholder='New account name...')], ),
            html.Div(style={'display': 'inline-block', 'padding': '5px 20px 20px 20px'},
                     children=[dcc.Upload(id='upload-data', multiple=True, style={'display': 'inline-block'},
                                          children=[html.Button('Select Transaction CSV')])]),
            html.I(id='upload-message',
                   style={'display': 'inline-block', 'padding': '0px 20px 10px 22px'}),
            html.Div(style={'padding': '10px 20px', 'display': 'inline-block', 'float': 'right'},
                     children=[html.Button(children=["Add Manual Transaction ", html.I(className="fa-solid fa-plus")], id="manual-button")]),

            dbc.Modal(id="transaction-modal", is_open=False, children=[
                dbc.ModalHeader(dbc.ModalTitle("Add New Transaction")),
                dbc.ModalBody(children=[
                    html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '0 5px 0 0'},
                             children=['Transaction Date', html.Span(" *", style={"color": "red"}), html.Br(),
                                       dcc.DatePickerSingle(
                                           id='transaction-date',
                                           min_date_allowed=date(2000, 1, 1),
                                           max_date_allowed=date.today(),
                                           initial_visible_month=date.today(),
                                       )]),
                    html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                             children=['Select Account', html.Span(" *", style={"color": "red"}),
                                       dcc.Dropdown(id='modal-account-dropdown', className='dropdown', clearable=True, placeholder='Select account...',
                                                    style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                    options=get_accounts_list('new'))]),
                    html.Div([dcc.Input(id='modal-account-input', type='text', style={'display': 'inline-block'}, placeholder='New account...')]),
                    html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                             children=['Transaction Amount', html.Span(" *", style={"color": "red"}), html.Br(),
                                       dcc.Input(id='transaction-value-input', type='number', placeholder='$ 0', style={'width': '100px'})]),
                    html.Div(style={'display': 'inline-block', 'width': '400px', 'padding': '5px 0'},
                             children=['Transaction Description', html.Span(" *", style={"color": "red"}), html.Br(),
                                       dcc.Input(id='description-input', type='text', style={'display': 'inline-block', 'width': '100%'},
                                                 placeholder='Description...')]),
                    html.Div(style={'display': 'inline-block', 'padding': '5px 0'},
                             children=['Select Category',
                                       dcc.Dropdown(id='modal-category-dropdown', className='dropdown', clearable=True, placeholder='unknown',
                                                    style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                    )]),
                    html.Div([dcc.Input(id='modal-category-input', type='text', style={'display': 'inline-block'}, placeholder='New category...')]),
                    html.Div(style={'display': 'inline-block', 'width': '400px', 'padding': '5px 0'},
                             children=['Transaction Note', html.Br(),
                                       dcc.Input(id='note-input', type='text', style={'display': 'inline-block', 'width': '100%'},
                                                 placeholder='Optional')]),
                    html.Div(id='modal-transaction-text', style={'display': 'inline-block', 'padding': '15px 0 0 0'}, ),
                ]),
                dbc.ModalFooter([
                    html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="t-modal-cancel", className="ms-auto")]),
                    dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                               id="t-modal-submit", className="ms-auto", style={'float': 'left'})]
                ),
            ]),

            # Overwrite the data files if it's being pulled from CSV
            html.Div(id='export-container', style={'padding': '10px 20px', 'display': 'inline-block', 'float': 'right'},
                     children=[html.Button(children=["Export Data ", html.I(className="fa-solid fa-download")],
                                           id="export-button"),
                               html.Div(style={'display': 'inline-block', 'padding': '0 0 0 10px'},
                                        children=[html.I(className="fa-solid fa-circle-info", id='help-icon-3', style={'display': 'inline-block'})]),
                               ]),
            dbc.Tooltip(id='export-tooltip',
                        target='help-icon-3',
                        placement='right',
                        style={'font-size': 14}),
            html.I(id='export-message', style={'display': 'inline-block', 'padding': '0px 20px 10px 20px'}),
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
    Input('time-button', 'n_clicks'),
)
def update_parameters(field_filter, time_filter, filter_values, curr_params, start_date, end_date, bar_button, pie_button, time_button):
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
        elif time_filter == 'Last 6 Months':
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1) - relativedelta(months=6)
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
            new_params['start_date'] = MD.get_oldest_transaction()
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
    elif trigger == 'time-button.n_clicks':
        curr_params['plot_type'] = 'time'

    if new_params['field_filter'] == 'Account Name':
        filter_dropdown = get_accounts_list()
    else:
        filter_dropdown = get_categories_list()

    if trigger == 'filter-dropdown.value':
        new_params['filter_value'] = filter_values

    return new_params, new_params['field_filter'], new_params['time_filter'], filter_dropdown, date_range_style


@callback(
    Output("transaction-modal", "is_open"),
    Output('modal-category-dropdown', 'value'),
    Output('transaction-value-input', 'value'),
    Output('transaction-date', 'date'),
    Output('description-input', 'value'),
    Output('modal-account-dropdown', 'value'),
    Output('modal-account-input', 'value'),
    Output('modal-account-input', 'style'),
    Output('modal-account-dropdown', 'options'),
    Output('modal-transaction-text', 'children'),
    Output('modal-category-input', 'value'),
    Output('modal-category-input', 'style'),
    Output('modal-category-dropdown', 'options'),
    Output('note-input', 'value'),
    Output('update-tab', 'data', allow_duplicate=True),

    Input("manual-button", "n_clicks"),
    Input("t-modal-cancel", "n_clicks"),
    Input("t-modal-submit", "n_clicks"),
    Input('modal-category-dropdown', 'value'),
    Input('transaction-value-input', 'value'),
    Input('transaction-date', 'date'),
    Input('description-input', 'value'),
    Input('modal-account-dropdown', 'value'),
    Input('modal-account-input', 'value'),
    Input('modal-category-input', 'value'),
    Input('note-input', 'value'),
    prevent_initial_call=True,
)
def new_transaction_modal(open_modal, cancel, submit, category, amount, t_date, description, account, new_account, new_category, note):
    trigger = dash.callback_context.triggered[0]['prop_id']

    update_tab = no_update
    is_open = False
    msg_str = ''
    category = 'unknown' if category is None else category
    t_date = date.today() if t_date is None else t_date

    if category == 'Add new category...':
        cat_style = {'display': 'inline-block', 'width': '400px'}
    else:
        cat_style = {'display': 'none'}

    if account == 'Add new account...':
        acc_style = {'display': 'inline-block', 'width': '400px'}
    else:
        acc_style = {'display': 'none'}

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

            if account == 'Add new account...':
                if new_account == '':
                    is_open = True
                    msg_str = dbc.Alert("You must specify an account.", color="danger")
                else:
                    account = new_account
            MD.add_one_transaction(category, amount, t_date, description, account, note)
            if new_account:
                MD.add_account(new_account)
            if new_category:
                MD.add_category(new_category)
            MD.export_data_to_csv()
            category = 'unknown'
            new_category = None
            amount = '$ 0'
            t_date = date.today()
            description = None
            account = None
            new_account = None
            note = None
            update_tab = True
        else:
            is_open = True
            msg_str = dbc.Alert("You must specify all values.", color="danger")
    elif trigger in ['modal-category-dropdown.value', 'transaction-value-input.value', 'transaction-date.date', 'description-input.value',
                     'modal-account-dropdown.value', 'modal-account-input.value', 'modal-category-input.value', 'note-input.value']:
        is_open = True
    else:
        category = 'unknown'
        new_category = None
        amount = '$ 0'
        t_date = date.today()
        description = None
        account = None
        new_account = None
        note = None

    return is_open, category, amount, t_date, description, account, new_account, acc_style, get_accounts_list('new'), msg_str, new_category, cat_style, get_categories_list('new'), note, update_tab


@callback(
    Output('upload-message', 'children'),
    Output('upload-data', 'disabled'),
    Output('account-input', 'style'),
    Output('account-input', 'value'),
    Output('account-dropdown', 'options'),
    Output('account-dropdown', 'value'),
    Output('update-tab', 'data'),

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
    upload_button = True
    msg = ''
    account_input = {'display': 'none'}
    update_tab = no_update
    account_dropdown_value = account

    trigger = dash.callback_context.triggered[0]['prop_id']

    # First, trigger the new account text input and/or upload button to activate
    if trigger == 'account-dropdown.value':
        if account == 'Add new account...':
            account_input = {'display': 'inline-block', 'width': '100%'}
        elif account is not None:
            upload_button = False

    # Once data is uploaded, process it
    elif trigger == 'upload-data.contents':

        # If it's a new account name, note that
        if account == 'Add new account...':
            account = new_account

        # Parse the data
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

            try:
                results = MD.load_transactions(m, account)

                # If the results were successful, reset the upload center and update the tab
                if isinstance(results, int):
                    if results == 0:
                        msg.append(f"File {i + 1}: No new transactions to upload")
                        msg.append(html.Br())
                    else:
                        msg.append(f"File {i + 1}: Successfully uploaded {results} new transactions\n")
                        msg.append(html.Br())
                        update_tab = True
                        if new_account:
                            MD.add_account(new_account)
                            MD.export_data_to_csv()
                            new_account = None
                    account_dropdown_value = None
                else:
                    # Give a second chance to upload the file
                    msg.append(f"File {i + 1}: {results}\n")
                    msg.append(html.Br())
                    if account_dropdown_value == 'Add new account...':
                        account_input = {'display': 'inline-block', 'width': '100%'}
                    upload_button = False

            except Exception as e:
                # Give a second chance to upload the file
                msg.append(f"File {i + 1} Error: Could not parse transactions")
                msg.append(html.Br())
                if account_dropdown_value == 'Add new account...':
                    account_input = {'display': 'inline-block', 'width': '100%'}
                upload_button = False

    elif trigger == 'account-input.value':
        account_input = {'display': 'inline-block', 'width': '100%'}
        upload_button = False

    return msg, upload_button, account_input, new_account, get_accounts_list('new'), account_dropdown_value, update_tab


@callback(
    Output('export-message', 'children'),
    Output('export-tooltip', 'children'),
    Input('export-button', 'n_clicks'),
)
def export_data(export):
    """If pulling data from CSV, export the files to the CSV where they're currently located"""
    msg = None
    if isinstance(MD.transactions_table, pd.DataFrame):
        tooltip = f"Export data (transactions, budget, accounts, categories) as CSV files to overwrite current files in:  {os.getenv('DATA_DIR')}."
    else:
        tooltip = 'Export data (transactions, budget, accounts, categories) as CSV files to the root directory, or specified in ' \
                  'the .env file BACKUP_DIR.'

    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'export-button.n_clicks':
        save_dir = MD.export_data_to_csv()
        msg = f"Saved files to {save_dir}"

    return msg, tooltip
