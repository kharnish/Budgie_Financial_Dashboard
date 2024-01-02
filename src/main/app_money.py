"""
Author: Kelly Harnish, Code 8121
Date:  02 May 2021
"""
import os
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy import signal
import pymongo
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
import dash_ag_grid as dag


load_dotenv()
client_mongo = pymongo.MongoClient(os.getenv("MONGO_HOST"))
client = client_mongo[os.getenv("MONGO_DB")]
table = client[os.getenv("MONGO_CLIENT")]

external_stylesheets = ['assets/spearmint.css']  # 'https://codepen.io/chriddyp/pen/bWLwgP.css'
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


def zero_params_dict():
    """Create empty dictionary with parameter keys.

    Returns: Dictionary with all parameters set to 0.

    """
    params = ['field_filter', 'time_filter', 'phase', 'start_date', 'end_date']
    params_dict = dict.fromkeys(params, 0)
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    params_dict['end_date'] = datetime.strftime(today, '%Y-%m-%d')
    params_dict['start_date'] = datetime.strftime(start_of_month, '%Y-%m-%d')

    return params_dict


def make_plot_object(conf_dict):
    """Make plot object from waveform parameters.

    Args:
        conf_dict: Dictionary of the configuration parameters.
        time_window: Window of data to display on plot.

    Returns: Plotly figure object.

    """
    # Generate figure
    fig_obj = go.Figure()

    if conf_dict['start_date'] != 0:
        transactions = pd.DataFrame(table.find({'date': {
            '$gte': datetime.strptime(conf_dict['start_date'], '%Y-%m-%d'),
            '$lte': datetime.strptime(conf_dict['end_date'], '%Y-%m-%d')}}))
    else:
        transactions = pd.DataFrame(table.find())

    if len(transactions) == 0:
        # TODO Error, no transactions found for the given filters
        fig_obj.add_trace(go.Bar(x=[0], y=[0]))
    elif conf_dict['field_filter'] == 0:
        for cat, grp in transactions.groupby('category'):
            fig_obj.add_trace(go.Bar(x=[cat], y=[grp['amount'].sum()], name=cat))
        fig_obj.update_xaxes(title_text="Category")
    elif conf_dict['field_filter'] == 1:
        for cat, grp in transactions.groupby('account_name'):
            fig_obj.add_trace(go.Bar(x=[cat], y=[grp['amount'].sum()], name=cat))
        fig_obj.update_xaxes(title_text="Account")

    fig_obj.update_xaxes(showline=True, mirror=True, linewidth=1, linecolor=colors['linegray'],
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['gridgray'],
                         showgrid=True, gridwidth=1, gridcolor=colors['gridgray'])
    fig_obj.update_yaxes(title_text="Amount ($)",
                         showline=True, mirror=True, linewidth=1, linecolor=colors['linegray'],
                         zeroline=True, zerolinewidth=1, zerolinecolor=colors['gridgray'],
                         showgrid=True, gridwidth=1, gridcolor=colors['gridgray'])
    fig_obj.update_layout(
        font=dict(family='Times New Roman', size=15),
        # showlegend=False,
        plot_bgcolor=colors['back2'],
        paper_bgcolor=colors['back2'],
        font_color=colors['text'],
        margin_l=30, margin_r=30, margin_t=20, margin_b=20,
    )
    return fig_obj


def make_table(conf_dict):
    if conf_dict['start_date'] != 0:
        transactions = pd.DataFrame(table.find({'date': {
            '$gte': datetime.strptime(conf_dict['start_date'], '%Y-%m-%d'),
            '$lte': datetime.strptime(conf_dict['end_date'], '%Y-%m-%d')}}))
    else:
        transactions = pd.DataFrame([table.find_one()])
    if len(transactions) == 0:
        return {'data': [{'date': 'Na', 'category': 'unknown', 'description': 'No Available Data', 'amount': 0,
                          'currency': 'USD', 'original_description': 'No Available Data', 'account': 'Na', 'notes': ''}],
                'columns': [{'field': 'date'}, {'field': 'category'}, {'field': 'description'}, {'field': 'amount'}, {'field': 'currency'},
                            {'field': 'original_description'}, {'field': 'account'}, {'field': 'notes'}]
                }
    transactions = transactions.drop(columns=['_id'])
    transactions['date'] = transactions['date'].dt.strftime('%m-%d-%Y')
    data = transactions.to_dict('records')
    columns = [{"field": i, 'filter': True} for i in transactions.columns]
    # TODO Make table columns be hidden
    hidden_columns = ['original_name', 'transaction_id', 'currency']
    return {'data': data, 'columns': columns, 'hidden_columns': hidden_columns}


colors = {
    'navy': '#162956',
    'blue': '#2E5590',
    'lightblue': '#6DA9CF',
    'gray': '#4C4F59',
    'linegray': '#7f7f7f',  # 127
    'gridgray': '#646464',  # 100
    'yellow': '#FAB208',
    'back0': '#020409',
    'back1': '#060c19',
    'back2': '#0a1429',
    'back3': '#0e1b39',
    'back4': '#112348',
    'text': '#EAEAEA',
}

# Initialize parameters
current_config_dict = zero_params_dict()

# Make initial plot
fig = make_plot_object(current_config_dict)

# Make initial table
tab = make_table(current_config_dict)

# Layout app window
app.layout = html.Div(
    children=[
        dcc.Store(id='original-config-memory'),
        dcc.Store(id='current-config-memory'),
        html.Div(
            style={'background-color': 'grey'},  # colors['navy'], },
            children=[
                html.Div(style={'width': '90px', 'display': 'inline-block', 'padding': '25px'},
                         children=[html.Img(id='aloha_logo', src="assets/spearmint_tilted_mirror.png", height="90px")]),
                html.H1(style={'width': '70%', 'color': 'white', 'display': 'inline-block'},
                        children=['Spearmint Personal Finance Management']),
            ]
        ),
        html.Div(id="input-params", style={'width': '24%', 'float': 'left'},
                 children=[
                     dbc.Row([html.Div(style={'width': '95%', 'display': 'inline-block', 'padding': '20px 20px 25px 20px'},
                                       children=["Filter Configurations"]),
                              html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '20px 20px 25px 20px'},
                                       children=["Sort By"]),
                              html.Div(style={'width': '50%', 'display': 'inline-block', 'padding': '0px',
                                              'vertical-align': 'middle'},
                                       children=[dcc.Dropdown(id='field-dropdown', value=current_config_dict['field_filter'],
                                                              clearable=False, searchable=False, className='dropdown',
                                                              style={'background-color': '#8A94AA'},
                                                              options=[
                                                                  {'label': 'Category', 'value': '0'},
                                                                  {'label': 'Account', 'value': '1'},
                                                              ], ),
                                                 ]
                                       ),
                              ]),
                     dbc.Row([html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '11px 20px'},
                                       children=['Time Window']),
                              html.Div(style={'width': '50%', 'display': 'inline-block', 'padding': '0px',
                                              'vertical-align': 'middle'},
                                       children=[dcc.Dropdown(id='time-dropdown', value=current_config_dict['time_filter'],  # maxHeight=400,
                                                              clearable=False, searchable=False, className='dropdown',
                                                              style={'background-color': '#8A94AA'},
                                                              options=[
                                                                  {'label': 'This Month', 'value': '0'},
                                                                  {'label': 'Last Month', 'value': '1'},
                                                                  {'label': 'This Year', 'value': '2'},
                                                                  {'label': 'Last Year', 'value': '3'},
                                                                  {'label': 'All Time', 'value': '4'},
                                                                  {'label': 'Custom', 'value': '5'},
                                                              ], )
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

                     dbc.Row([html.Div(style={'width': '35%', 'display': 'inline-block', 'padding': '10px 20px'},
                                       children=["Phase (deg)"]),
                              html.Div(style={'width': '50%', 'display': 'inline-block'},
                                       children=[dcc.Input(
                                           style={'width': 150},
                                           id='phi-input',
                                           type='number',
                                           value=current_config_dict['phase'], min=0, max=360, )
                                       ]),
                              ]),
                     html.Div(style={'display': 'inline-block', 'width': '90%', 'padding': '5px 20px'},
                              children=[dcc.Input(id='config-input', type='text', style={'width': '100%'},
                                                  placeholder='Path to config file')], ),
                     html.I(id='config-input-text', style={'padding': '0px 20px 10px 21px', 'color': '#969696'}, ),

                     html.Div('', style={'padding': '0px 20px 20px 20px'}, ),  # seems to work better than html.Br()
                     html.Div(style={'display': 'inline-block', 'padding': '0px 20px 20px 20px'},
                              children=[html.Button(id='write-button', n_clicks=0, children=['Write New Config File'])]),
                     html.I(id='output-write-button',
                            style={'display': 'inline-block', 'padding': '0px 20px 20px 21px', 'color': '#969696'}, ),
                     html.Div('', style={'padding': '0px 20px 10px 20px'}, ),
                 ]),

        dcc.Tabs(id='selection_tabs', value='Trends', children=[
                dcc.Tab(label="Trends", value='Trends', children=[
                    html.Div(id="trends-plot", style={'width': '99%', 'height': '600px', 'float': 'left'},
                             children=[
                                 dcc.Graph(style={'width': '95%', 'height': '95%', 'padding': '10px 20px', 'align': 'center'},
                                           id='money-graph', figure=fig),
                             ]),
                ]),
                dcc.Tab(label="Transactions", value='Transactions', children=[
                    html.Div(style={'width': '99%', 'height': '600px', 'float': 'left', 'background-color': colors.get('blue')},
                             children=[dag.AgGrid(id="transactions-table",
                                                  rowData=tab.get('data'),
                                                  columnDefs=tab.get('columns'),
                                                  ),
                                       html.Div(style={'height': '10px'}, id='blank-space')])
                ]),
                dcc.Tab(label="Budget", value='Budget', children=[
                    'TODO: Budget']),
            ]),
    ]
)


@app.callback(
    Output('config-input-text', 'children'),
    Output('original-config-memory', 'data'),
    Input('config-input', 'value'),
)
def parse_config_path(path):
    return '', zero_params_dict()


@app.callback(
    Output('current-config-memory', 'data'),
    Output('field-dropdown', 'value'),
    Output('time-dropdown', 'value'),
    Output('date-range', 'style'),

    Input('field-dropdown', 'value'),
    Input('time-dropdown', 'value'),
    Input('original-config-memory', 'data'),
    Input('current-config-memory', 'data'),
    Input('phi-input', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
)
def update_plot_parameters(field_filter, time_filter, og_params, curr_params, phase, start_date, end_date):
    """Update current parameter dictionary and visible parameters based on selected bit or manual changes.

    Args:
        field_filter: Category filter
        time_filter: Time window filter
        og_params: Dictionary of original parameters from loaded config file.
        curr_params: Dictionary of current parameters.
        phase: Phase of the waveform (deg).

    Returns: Current parameters for specified bit.

    """
    # Determine what triggered the parameter update
    trigger = dash.callback_context.triggered[0]['prop_id']

    # if original parameter dict, update current dict to og
    if trigger == 'original-config-memory.data' or curr_params is None:
        curr_params = og_params
    new_params = curr_params

    if curr_params['time_filter'] == '5':
        date_range_style = {'display': 'inline-block', 'padding': '15px 20px 15px 20px'}
    else:
        date_range_style = {'display': 'none'}

    # if one of the parameters, change them in the current dict
    if 'input' in trigger:
        if phase is not None:
            new_params['phase'] = phase
    elif trigger == 'field-dropdown.value':
        new_params['field_filter'] = int(field_filter) if field_filter else 0
    elif trigger == 'time-dropdown.value':
        new_params['time_filter'] = time_filter
        if time_filter == '0':  # This Month
            today = date.today()
            new_params['start_date'] = date(today.year, today.month, 1)
            new_params['end_date'] = date.today()
            date_range_style = {'display': 'none'}
        elif time_filter == '1':  # Last Month
            today = date.today()
            new_params['end_date'] = date(today.year, today.month, 1) - timedelta(days=1)
            new_params['start_date'] = date(new_params['end_date'].year, new_params['end_date'].month, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == '2':  # This Year
            today = date.today()
            new_params['end_date'] = today
            new_params['start_date'] = date(today.year, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == '3':  # Last Year
            today = date.today()
            new_params['end_date'] = date(today.year, 1, 1) - timedelta(days=1)
            new_params['start_date'] = date(new_params['end_date'].year, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == '4':  # All Time
            new_params['end_date'] = date.today()
            new_params['start_date'] = date(2000, 1, 1)
            date_range_style = {'display': 'none'}
        elif time_filter == '5':
            date_range_style = {'display': 'inline-block', 'padding': '15px 20px 15px 20px'}
    elif 'date-range' in trigger:
        new_params['start_date'] = start_date
        new_params['end_date'] = end_date

    return new_params, new_params['field_filter'], new_params['time_filter'], date_range_style


@app.callback(
    Output('money-graph', 'figure'),
    Output('transactions-table', 'rowData'),
    Output('transactions-table', 'columnDefs'),
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
        return make_plot_object(current_params), tab_dict['data'], tab_dict['columns']
    elif which_tab == 'Transactions':
        tab_dict = make_table(current_params)
        return make_plot_object(zero_params_dict()), tab_dict['data'], tab_dict['columns']
    elif which_tab == 'Budget':
        tab_dict = make_table(zero_params_dict())
        return make_plot_object(zero_params_dict()), tab_dict['data'], tab_dict['columns']


@app.callback(
    Output('output-write-button', 'children'),
    Input('write-button', 'n_clicks'),
    Input('current-config-memory', 'data'),
    Input('config-input', 'value'),
)
def write_new_config(clicks, current_dict, og_path):
    """When button is clicked, checks for valid current file then writes new config file with updated parameters.

    Args:
        clicks: Number of times the write file button has been clicked.
        current_dict: Original config file.
        og_path: Path to original config file.

    Returns: String if the file is able to be written or not.

    """
    if 'write-button' in dash.callback_context.triggered[0]['prop_id']:
        if og_path is not None:
            if os.path.isfile(og_path):
                og_file_name = os.path.basename(og_path)
                file_name = og_file_name[:-4] + '_v' + str(clicks) + '.txt'
                new_path = og_path[:-len(og_file_name)]
                write_file = open(os.path.join(new_path, file_name), 'w')
                for key in current_dict:
                    if key == 'version':
                        if current_dict[key] != 0:
                            write_file.write(key + ' = ' + current_dict[key] + '_v' + str(clicks) + '\n')
                        else:
                            return 'Ensure config file has all required parameters.'
                    else:
                        write_file.write(key + ' = ' + str(current_dict[key]) + '\n')
                return 'Wrote new config file: ' + file_name
            else:
                return 'Enter valid file path before writing new config file.'
        else:
            return 'Enter a file path before writing new config file.'
    else:
        return ''


if __name__ == '__main__':
    # Use host='0.0.0.0' for running in Docker and host='127.0.0.1' for running in PyCharm
    app.run_server(host='127.0.0.1', port=8050, debug=True)
