import dash
from dash import Dash, callback, dcc, html, Input, Output, no_update
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd

from utils import zero_params_dict, MD


def make_accounts_table(conf_dict):
    """Query account metadata and organize into data and columns

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Data and Columns dictionary

    """
    # Query and organize account data
    accounts = pd.DataFrame(MD.accounts_table.find())

    if len(accounts) == 0:
        return {'data': [{'Account Name': 'No accounts'}], 'columns': [{"field": 'Account Name'}]}

    accounts = accounts.drop(columns=['_id'])
    accounts = accounts.sort_values('account name')
    data = accounts.to_dict('records')
    columns = [{"field": i} for i in accounts.columns]

    # Update the column format for each column
    for col in columns:
        if col['field'] == 'initial balance':
            col['valueFormatter'] = {"function": "d3.format('($.2f')(params.value)"}
            col['type'] = 'numericColumn'
            col['filter'] = 'agNumberColumnFilter'
            col['editable'] = True
        elif col['field'] == 'status':
            col['cellStyle'] = {"function": "params.value == 'closed' ? {'color': 'firebrick'} : {'color': 'seagreen'}"}
            col['editable'] = True
            col['cellEditor'] = 'agSelectCellEditor'
            col['cellEditorParams'] = {'values': ['open', 'closed']}

    return {'data': data, 'columns': columns}


def make_categories_table(conf_dict):
    """Query category metadata and organize into data and columns

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Data and Columns dictionary

    """
    # Query and organize account data
    cats = pd.DataFrame(MD.categories_table.find())

    if len(cats) == 0:
        return {'data': [{'Category Name': 'No categories', 'Parent': 'NA'}], 'columns': [{"field": 'Category Name'}, {"field": 'Parent'}]}

    categories = cats.drop(columns=['_id'])
    childless = categories[categories['parent'].isnull()]
    parent = categories[~categories['parent'].isnull()]
    parents_list = list(childless['category name']) + list(parent['parent'].unique())
    parents_list = sorted(parents_list) + ['Make parent']
    categories = categories.sort_values(['parent', 'category name'])
    data = categories.to_dict('records')
    columns = [{"field": i} for i in categories.columns]

    return {'data': data, 'columns': columns}


# Make initial tables
acc_tab = make_accounts_table(zero_params_dict())
cat_tab = make_categories_table(zero_params_dict())

configurations_tab = dcc.Tab(label="Configurations", value='Configurations', children=[
    html.Div(style={'width': '100%', 'height': '700px', 'padding': '5px', 'align': 'center'}, className='tab-body',
             children=[
                 html.Div(style={'width': '50%', 'display': 'inline-block', 'padding': '5px'},
                          children=[
                              html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                       children=[dbc.Button(children=["Delete ", html.I(className="fa-solid fa-trash-can")],
                                                            style={'width': '100px'}, id="categories-delete", disabled=True, color="danger")]),
                              dag.AgGrid(id="categories-table",
                                         style={"height": '600px'},
                                         dashGridOptions={"rowSelection": "multiple"},
                                         rowData=cat_tab['data'],
                                         columnDefs=cat_tab['columns'],
                                         columnSize="autoSize",
                                         defaultColDef={'filter': True, "resizable": True, 'sortable': True},
                                         )]),
                 html.Div(style={'width': '50%', 'display': 'inline-block', 'padding': '5px'},
                          children=[
                              html.Div(style={'padding': '10px', 'display': 'inline-block'},
                                       children=[dbc.Button(children=["Delete ", html.I(className="fa-solid fa-trash-can")],
                                                            style={'width': '100px'}, id="accounts-delete", disabled=True, color="danger")]),
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


@callback(
    Output('update-tab', 'data', allow_duplicate=True),
    Input('categories-table', 'cellValueChanged'),
    prevent_initial_call=True,
)
def update_table_data(change_data):
    update_tab = no_update
    if change_data:
        if change_data[0]['colId'] == 'parent':
            if change_data[0]['data']['parent'] == 'Make parent':
                change_data[0]['data']['parent'] = None
        MD.edit_category(change_data)
        update_tab = True
    return update_tab


@callback(
    Output('categories-delete', 'disabled'),
    Output('update-tab', 'data', allow_duplicate=True),

    Input('categories-delete', 'n_clicks'),
    Input('categories-table', 'selectedRows'),
    prevent_initial_call=True,
)
def update_categories_table(delete, row_data):
    trigger = dash.callback_context.triggered[0]['prop_id']

    enabled = True
    update_tab = no_update

    if trigger == 'categories-table.selectedRows' and (row_data is None or len(row_data) > 0):
        enabled = False

    elif trigger == 'categories-delete.n_clicks':
        MD.delete_category(row_data)
        update_tab = True

    return enabled, update_tab
