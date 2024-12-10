import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

from components.configurations_sidebar import configurations_sidebar
from components.trends_tab import trends_tab, make_trends_plot
from components.transaction_tab import transaction_tab, make_table
from components.budget_tab import budget_tab, make_budget_plots
from components.net_worth_tab import net_worth_tab, make_net_worth_plot
from components.configurations_tab import configurations_tab, make_accounts_table, make_categories_table
from components.utils import zero_params_dict

external_stylesheets = ['assets/budgie_light.css', dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Initialize parameters
current_config_dict = zero_params_dict()

# Layout app window
app.layout = html.Div(
    children=[
        dcc.Store(id='current-config-memory'),
        dcc.Store(id='update-tab'),

        html.Div(style={'background-color': '#2C4864'},
                 children=[
                     html.Div(style={'width': 'auto', 'display': 'inline-block', 'padding': '25px 40px'},
                              children=[html.Img(id='logo', src="assets/parakeet.png", height="90px")]),
                     dbc.Tooltip(children=["Tweet tweet!", html.Br(),
                                           "I'd like to thank J for coming up with the name and theme of Budgie, and T for supporting me (and laughing at my antics) while developing this. - K, 2024"],
                                 target='logo',
                                 placement='right',
                                 style={'font-size': 14},
                                 ),

                     html.Div(style={'position': 'absolute', 'left': '145px', 'top': '60px'},
                              children=[html.H1(['Budgie Financial Dashboard'])]),
                 ]),

        configurations_sidebar,

        html.Div(
            id='tab-div', style={'padding': '20px'},  # tabs container
            children=[
                dcc.Tabs(id='selection-tabs', value='Trends', children=[
                    trends_tab,
                    transaction_tab,
                    budget_tab,
                    net_worth_tab,
                    configurations_tab,
                ]),
            ]),
    ]
)


########################################################################################
@app.callback(
    Output('trends-graph', 'figure'),
    Output('transactions-table', 'rowData'),
    Output('transactions-table', 'columnDefs'),
    Output('budget-graph-income', 'figure'),
    Output('budget-graph-income', 'style'),
    Output('budget-graph-spend', 'figure'),
    Output('budget-graph-spend', 'style'),
    Output('budget-equation', 'children'),
    Output('net-worth-graph', 'figure'),
    Output('accounts-table', 'rowData'),
    Output('accounts-table', 'columnDefs'),
    Output('categories-table', 'rowData'),
    Output('categories-table', 'columnDefs'),

    Input('current-config-memory', 'data'),
    Input('selection-tabs', 'value'),
    Input('update-tab', 'data')
)
def update_tab_data(current_params, which_tab, update_tab):
    """Updates the waveform graph given the parameters of the waveform and creates plot.

    Args:
        current_params: Dictionary of original parameters from loaded config file.
        which_tab: The active tab to update the values of

    Returns:
        Figure object of plot
        Table data dictionary

    """
    if which_tab == 'Trends':
        try:
            tab_dict = make_table(zero_params_dict())
        except Exception as e:
            print(e)
            exit()
        acc_dict = make_accounts_table()
        cat_dict = make_categories_table()
        return make_trends_plot(current_params), tab_dict['data'], tab_dict['columns'], *make_budget_plots(zero_params_dict()), make_net_worth_plot(zero_params_dict()), \
            acc_dict['data'], acc_dict['columns'], cat_dict['data'], cat_dict['columns']

    elif which_tab == 'Transactions':
        tab_dict = make_table(current_params)
        acc_dict = make_accounts_table()
        cat_dict = make_categories_table()
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], *make_budget_plots(zero_params_dict()), make_net_worth_plot(zero_params_dict()), \
            acc_dict['data'], acc_dict['columns'], cat_dict['data'], cat_dict['columns']

    elif which_tab == 'Budget':
        tab_dict = make_table(zero_params_dict())
        acc_dict = make_accounts_table()
        cat_dict = make_categories_table()
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], *make_budget_plots(current_params), make_net_worth_plot(zero_params_dict()), \
            acc_dict['data'], acc_dict['columns'], cat_dict['data'], cat_dict['columns']

    elif which_tab == 'Net Worth':
        tab_dict = make_table(zero_params_dict())
        acc_dict = make_accounts_table()
        cat_dict = make_categories_table()
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], *make_budget_plots(zero_params_dict()), make_net_worth_plot(current_params), \
            acc_dict['data'], acc_dict['columns'], cat_dict['data'], cat_dict['columns']

    elif which_tab == 'Configurations':
        tab_dict = make_table(zero_params_dict())
        acc_dict = make_accounts_table(True)
        cat_dict = make_categories_table(True)
        return make_trends_plot(zero_params_dict()), tab_dict['data'], tab_dict['columns'], *make_budget_plots(zero_params_dict()), make_net_worth_plot(zero_params_dict()), \
            acc_dict['data'], acc_dict['columns'], cat_dict['data'], cat_dict['columns']


if __name__ == '__main__':
    # Use host='0.0.0.0' for running in Docker and host='127.0.0.1' for running in PyCharm
    app.run_server(host='127.0.0.1', port=8050, debug=True)
