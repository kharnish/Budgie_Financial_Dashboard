import dash
from dash import callback, dcc, html, Input, Output, no_update
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd

from components.utils import MD


def make_accounts_table(check_update=False):
    """Query account metadata and organize into data and columns

    Returns: Data and Columns dictionary

    """
    # Query and organize account data
    accounts = pd.DataFrame(MD.accounts_table.find())

    if len(accounts) == 0:
        return {'data': [{'Account Name': 'No accounts'}], 'columns': [{"field": 'Account Name'}]}

    accounts.loc[:, '_id'] = [str(tid) for tid in accounts['_id']]
    accounts = accounts.sort_values('account name')
    data = accounts.to_dict('records')
    columns = [{"field": i} for i in accounts.columns]

    # Update the column format for each column
    for col in columns:
        if col['field'] == 'account name':
            col['editable'] = True
        elif col['field'] == 'initial balance':
            col['valueFormatter'] = {"function": "d3.format('($,.2f')(params.value)"}
            col['type'] = 'numericColumn'
            col['filter'] = 'agNumberColumnFilter'
            col['editable'] = True
        elif col['field'] == 'status':
            col['cellStyle'] = {"function": "params.value == 'closed' ? {'color': 'firebrick'} : {'color': 'seagreen'}"}
            col['editable'] = True
            col['cellEditor'] = 'agSelectCellEditor'
            col['cellEditorParams'] = {'values': ['open', 'closed']}
        elif col['field'] == '_id':
            col['hide'] = True

    return {'data': data, 'columns': columns}


def make_categories_table(check_update=False):
    """Query category metadata and organize into data and columns

    Args:
        check_update: Check for updates from the transactions, only necessary every once in a while

    Returns: Data and Columns dictionary
    """
    # Query and organize account data
    categories = pd.DataFrame(MD.categories_table.find())

    if len(categories) == 0:
        return {'data': [{'Category Name': 'No categories'}], 'columns': [{"field": 'Category Name'}]}

    if check_update:
        # If you delete all items from a category, it needs to trigger to delete the name
        current_cats = MD.get_categories_list()
        refresh = False
        for _, grp in categories.iterrows():
            if grp['category name'] not in current_cats:
                for delete_cat in [grp.to_dict()]:
                    MD.delete_category(delete_cat)
                refresh = True
        if refresh:
            categories = pd.DataFrame(MD.categories_table.find())

    categories.loc[:, '_id'] = [str(tid) for tid in categories['_id']]
    categories = categories.sort_values(['parent', 'category name'], key=lambda column: column.str.lower())
    data = categories.to_dict('records')
    columns = [{"field": i} for i in categories.columns]

    # Update the column format for each column
    for col in columns:
        if col['field'] == '_id':
            col['hide'] = True
        elif col['field'] == 'category name':
            col['editable'] = True
        elif col['field'] == 'parent':
            col['hide'] = True
        elif col['field'] == 'hidden':
            col['editable'] = True

    return {'data': data, 'columns': columns}


# Make initial tables
acc_tab = make_accounts_table(True)
cat_tab = make_categories_table(True)

configurations_tab = dcc.Tab(label="Configurations", value='Configurations', children=[
    html.Div(style={'width': '100%', 'padding': '5px', 'align': 'center'}, className='tab-body',
             children=[
                 html.Div(style={'width': '40%', 'display': 'inline-block', 'padding': '5px 15px 5px 5px'},
                          children=[
                              html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                       children=[dbc.Button(children=["Delete Category ", html.I(className="fa-solid fa-trash-can")],
                                                            style={'width': '160px'},
                                                            id="category-delete", disabled=True, color="danger")]),
                              dcc.ConfirmDialog(
                                    id='confirm-category-danger',
                                    message='WARNING! \n\nYou are about to delete a category. All associated transactions will be reverted to "unknown" category. \n\nDo you want to continue?',
                              ),
                              dag.AgGrid(id="categories-table",
                                         style={"height": '600px'},
                                         dashGridOptions={"rowSelection": "multiple"},
                                         rowData=cat_tab['data'],
                                         columnDefs=cat_tab['columns'],
                                         columnSize="autoSize",
                                         defaultColDef={'filter': True, "resizable": True, 'sortable': True},
                                         )]),

                 html.Div(style={'width': '60%', 'display': 'inline-block', 'padding': '5px'},
                          children=[
                              html.Div(style={'padding': '0 5px 0 0', 'float': 'right'}, id='help-configuration',
                                       children=[html.I(className="fa-solid fa-circle-question")]),
                              dbc.Modal(id="configuration-help", is_open=False, children=[
                                  dbc.ModalHeader(dbc.ModalTitle("Configuration Help")),
                                  dbc.ModalBody(children=['The Configurations tab shows all Categories and Accounts.', html.Br(), html.Br(),
                                                          "Categories can be marked as Hidden, which means those transactions won't be displayed on the Trends tab. "
                                                          'This is common for "Transfer" or "Credit Card Payment" categories where money is being moved from an account but not actually spent.',
                                                          html.Br(), html.Br(),
                                                          'As described on the Net Worth tab, the Initial Balance of each account should be set so the calculations match your current assets. '
                                                          'It is equivalent to account balance before the date of the first transaction from that account in Budgie.', html.Br(), html.Br(),
                                                          'Account status can also be changed to Open or Closed for your record.'])]),

                              html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                       children=[dbc.Button(children=["Delete Account ", html.I(className="fa-solid fa-trash-can")],
                                                            style={'width': '150px'},
                                                            id="accounts-delete", disabled=True, color="danger")]),
                              dcc.ConfirmDialog(
                                    id='confirm-account-danger',
                                    message='WARNING! \n\nYou are about to delete an account. All associated transactions will also be deleted. \n\nDo you want to continue?',
                              ),
                              dag.AgGrid(id="accounts-table",
                                         dashGridOptions={"domLayout": "autoHeight", "rowSelection": "multiple"},
                                         rowData=acc_tab['data'],
                                         columnDefs=acc_tab['columns'],
                                         columnSize="autoSize",
                                         defaultColDef={'filter': True, "resizable": True, 'sortable': True},
                                         ),
                          ]),
             ])
])


# @callback(
#     Output('update-tab', 'data', allow_duplicate=True),
#     Input('categories-table', 'cellValueChanged'),
#     prevent_initial_call=True,
# )
# def update_table_data(change_data):
#     update_tab = no_update
#     if change_data:
#         if change_data[0]['colId'] == 'parent':
#             if change_data[0]['data']['parent'] == 'Make parent':
#                 change_data[0]['data']['parent'] = None
#         MD.edit_category(change_data)
#         update_tab = True
#     return update_tab


@callback(Output('confirm-category-danger', 'displayed'),
          Input('category-delete', 'n_clicks'),
          )
def confirm_category_account(value):
    if value:
        return True
    return False


@callback(
    Output('category-delete', 'disabled'),
    Output('update-tab', 'data', allow_duplicate=True),

    Input('confirm-category-danger', 'submit_n_clicks'),
    Input('categories-table', 'selectedRows'),
    Input('categories-table', 'cellValueChanged'),
    prevent_initial_call=True,
)
def update_categories_table(confirm_delete, row_data, cell_data):
    trigger = dash.callback_context.triggered[0]['prop_id']

    disabled = True
    update_tab = no_update

    if trigger == 'categories-table.selectedRows' and (row_data is None or len(row_data) > 0):
        disabled = False

    elif trigger == 'confirm-category-danger.submit_n_clicks' and confirm_delete:
        MD.delete_category(row_data[0])
        print(f"Deleted category: {row_data[0]['category name']}")
        update_tab = True

    elif trigger == 'categories-table.cellValueChanged':
        print(cell_data)
        MD.edit_category(cell_data[0])
        print(f"Updated category name: '{cell_data[0]['oldValue']}' -> '{cell_data[0]['data']['category name']}'")
        update_tab = True

    return disabled, update_tab


@callback(Output('confirm-account-danger', 'displayed'),
          Input('accounts-delete', 'n_clicks'),
          )
def confirm_delete_account(value):
    if value:
        return True
    return False


@callback(
    Output('accounts-delete', 'disabled'),
    Output('update-tab', 'data', allow_duplicate=True),

    Input('confirm-account-danger', 'submit_n_clicks'),
    Input('accounts-table', 'selectedRows'),
    Input('accounts-table', 'cellValueChanged'),
    prevent_initial_call=True,
)
def update_accounts_table(confirm_delete, row_data, cell_data):
    trigger = dash.callback_context.triggered[0]['prop_id']

    disabled = True
    update_tab = no_update

    if trigger == 'accounts-table.selectedRows' and (row_data is None or len(row_data) > 0):
        disabled = False

    elif trigger == 'confirm-account-danger.submit_n_clicks' and confirm_delete:
        MD.delete_account(row_data[0])
        print(f"Deleted account and all associated transactions for: {row_data[0]['account name']}")
        update_tab = True

    elif trigger == 'accounts-table.cellValueChanged':
        MD.edit_account(cell_data[0])
        print(f"Updated account name: '{cell_data[0]['oldValue']}' -> '{cell_data[0]['data']['account name']}'")
        update_tab = True

    return disabled, update_tab


@callback(
    Output('configuration-help', 'is_open'),
    Input('help-configuration', 'n_clicks')
)
def help_modal(clicks):
    isopen = False
    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'help-configuration.n_clicks':
        isopen = True
    return isopen
