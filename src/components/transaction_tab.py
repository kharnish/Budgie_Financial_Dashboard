import dash
from dash import Dash, callback, dcc, html, Input, Output, no_update
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from datetime import date

from utils import zero_params_dict, MD, EXCLUDE_FROM_TABLE, get_accounts_list


def make_table(conf_dict):
    """Query the transactions and organize the data into a table, giving the correct parameters to each column

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Data and Columns dictionary
    """
    transactions = MD.query_transactions(conf_dict)
    transactions.loc[:, '_id'] = [str(tid) for tid in transactions['_id']]
    transactions = transactions.sort_values('date', ascending=False)
    transactions['date'] = transactions['date'].dt.strftime('%m-%d-%Y')
    data = transactions.to_dict('records')
    columns = [{"field": i} for i in transactions.columns]

    # Update the column format for each column
    for col in columns:
        if col['field'] in EXCLUDE_FROM_TABLE:
            col['hide'] = True
        elif col['field'] == 'amount':
            col['valueFormatter'] = {"function": "d3.format('($,.2f')(params.value)"}
            col['type'] = 'numericColumn'
            col['cellStyle'] = {"function": "params.value < 0 ? {'color': 'firebrick'} : {'color': 'seagreen'}"}
            col['filter'] = 'agNumberColumnFilter'
            col['editable'] = True
        elif col['field'] == 'category':
            col['width'] = 150
            col['editable'] = True
            col['cellEditor'] = 'agSelectCellEditor'
            col['cellEditorParams'] = {'values': MD.get_categories_list()}
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
        elif col['field'] == 'notes':
            col['editable'] = True
    return {'data': data, 'columns': columns}


# Make initial table
tab = make_table(zero_params_dict())

transaction_tab = dcc.Tab(label="Transactions", value='Transactions', children=[
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
                             html.Div(style={'display': 'inline-block', 'width': '100%', 'padding': '5px 0'},
                                      children=['New Note:', html.Br(),
                                                dcc.Input(id='new-note-input', type='text', style={'display': 'inline-block', 'width': '400px'},
                                                          placeholder='New Note')]),
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

                     html.Div(style={'padding': '10px 15px 0 0', 'float': 'right'}, id='help-transactions',
                              children=[html.I(className="fa-solid fa-circle-question")]),
                     dbc.Modal(id="transactions-help", is_open=False, children=[
                         dbc.ModalHeader(dbc.ModalTitle("Transactions Help")),
                         dbc.ModalBody(children=['The Transactions tab allows you to see and edit your individual transactions.', html.Br(), html.Br(),
                                                 'Add new transactions either by uploading a CSV file or inputting a manual transaction from the menu on the left.', html.Br(), html.Br(),
                                                 'Quick edit a single transaction by double clicking the value to modify, or select row(s) and use the Edit button for more detailed edits.', html.Br(), html.Br(),
                                                 'Shift + click to select a range of transactions, or ctrl + click to select multiple individual transactions. '
                                                 'Press the space bar to undo/redo your selection.'
                                                 ])]),

                     dag.AgGrid(id="transactions-table",
                                style={"height": '600px'},
                                rowData=tab.get('data'),
                                columnDefs=tab.get('columns'),
                                columnSize="autoSize",
                                defaultColDef={'filter': True, "resizable": True, 'sortable': True},
                                dashGridOptions={"rowSelection": "multiple"}
                                ),
                 ]),
        html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-2')
    ])


@callback(
    Output('blank-space-1', 'children'),
    Input('transactions-table', 'cellValueChanged')
)
def update_table_data(change_data):
    if change_data:
        MD.edit_transaction(change_data)
    return ''


@callback(
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
    Output('new-note-input', 'value'),
    Output('update-tab', 'data', allow_duplicate=True),

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
    Input('new-note-input', 'value'),
    prevent_initial_call=True,
)
def bulk_update_table(edit_button, delete_button, row_data, cancel, submit, category, new_category, amount, t_date, description, account, new_account, new_note):
    trigger = dash.callback_context.triggered[0]['prop_id']

    is_open = False
    msg_str = ''
    enabled = True
    update_tab = no_update

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
        MD.delete_transaction(row_data)
        update_tab = True

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
        if new_note is not None:
            update_dict['notes'] = new_note

        if len(update_dict) != 0:
            for r in row_data:
                for key, val in update_dict.items():
                    r[key] = val
            MD.edit_many_transactions(row_data)

            if new_account:
                MD.add_account(new_account)
            if new_category:
                MD.add_category(new_category)
            MD.export_data_to_csv()

            category = None
            new_category = None
            amount = None
            t_date = None
            description = None
            account = None
            new_account = None
            new_note = None
            update_tab = True
        else:
            is_open = True
            msg_str = dbc.Alert("You must specify at least one value to update.", color="danger") if msg_str == '' else msg_str

    elif trigger in ['new-category-dropdown.value', 'new-transaction-value.value', 'new-transaction-date.date', 'new-description-input.value',
                     'new-account-dropdown.value', 'new-account-input.value', 'new-category-input.value', 'new-note-input.value']:
        is_open = True
    else:
        category = None
        new_category = None
        amount = None
        t_date = None
        description = None
        account = None
        new_account = None
        new_note = None

    return enabled, enabled, is_open, category, cat_style, new_category, MD.get_categories_list('new'), amount, t_date, description, account, \
        account_style, new_account, msg_str, new_note, update_tab


@callback(
    Output('transactions-help', 'is_open'),
    Input('help-transactions', 'n_clicks')
)
def help_modal(clicks):
    isopen = False
    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'help-transactions.n_clicks':
        isopen = True
    return isopen