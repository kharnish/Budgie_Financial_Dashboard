from dash import dcc, html
import dash_ag_grid as dag

import pandas as pd


from utils import zero_params_dict, accounts_table


def make_accounts_table(conf_dict):
    """Query account metadata and organize into data and columns

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Data and Columns dictionary

    """
    # Query and organize account data
    accounts = pd.DataFrame(accounts_table.find())
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
        elif col['field'] == 'status':
            col['cellStyle'] = {"function": "params.value == 'closed' ? {'color': 'firebrick'} : {'color': 'seagreen'}"}

    return {'data': data, 'columns': columns}


# Account table
acc_tab = make_accounts_table(zero_params_dict())

accounts_tab = dcc.Tab(label="Accounts", value='Accounts', children=[
    html.Div(style={'width': '100%', 'height': '700px', 'padding': '10px 20px', 'align': 'center'}, className='tab-body',
             children=[dag.AgGrid(id="accounts-table",
                                  dashGridOptions={"domLayout": "autoHeight"},
                                  # style={"height": '600px'},
                                  rowData=acc_tab['data'],
                                  columnDefs=acc_tab['columns'],
                                  columnSize="autoSize",
                                  defaultColDef={'filter': True, "resizable": True, 'sortable': True},
                                  )
                       ],
             )])
