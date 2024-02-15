import dash
from dash import Dash, callback, dcc, html, Input, Output, no_update
import dash_bootstrap_components as dbc
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

from utils import zero_params_dict, get_mongo_transactions, MT, update_layout_axes, COLORS, transactions_table, budget_table, get_categories_list


def make_budget_plot(conf_dict):
    """Make bar plot of budget, showing spending and spending limit for each category.

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Plotly figure object

    """
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

    fig_obj.add_vline(x=100, line_width=3, line_color=COLORS['light'].get('gridgray'))

    # Make a vertical line to show progress through the month
    start_date = datetime.strptime(conf_dict['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(conf_dict['end_date'], '%Y-%m-%d').date()
    today = date.today()
    if start_date <= today <= end_date:
        progress = (today - date(today.year, today.month, 1)).days
        progress = 100 * progress / 31
        fig_obj.add_vline(x=progress, line_width=1, line_color=COLORS['light'].get('gridgray'))

    # Standard figure layout, but don't show horizontal lines
    update_layout_axes(fig_obj)
    fig_obj.update_xaxes(showgrid=False)
    fig_obj.update_yaxes(showgrid=False)
    fig_obj.update_layout(showlegend=False)

    return fig_obj


budget_tab = dcc.Tab(label="Budget", value='Budget', className='tab-body', children=[
                        html.Div(id="budget-plot", style={'width': '100%', 'float': 'left'}, className='tab-body',
                                 children=[
                                     dcc.Graph(style={'width': '95%', 'height': '95%', 'padding': '10px 20px 0 20px', 'align': 'center'},
                                               id='budget-graph', figure=make_budget_plot(zero_params_dict())),
                                     html.Div(style={'display': 'inline-block', 'padding': '5px 0 20px 20px', 'float': 'left', 'width': '95%'},
                                              children=[html.Button(id='new-budget-button', style={'width': 'auto'},
                                                                    children=['Add Or Update Budget ', html.I(className="fa-solid fa-pen-to-square")])]),
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
                                             html.Div(id='modal-average-text', style={'padding': '5px 0 10px 0'}),
                                             html.Div(style={'float': 'right', 'position': 'absolute', 'bottom': 10, 'right': 10},
                                                      children=[dbc.Button(children=["Delete Budget ", html.I(className="fa-solid fa-trash-can")],
                                                                           id="modal-delete", color="danger", style={'float': 'right'})]),
                                             html.Div(id='modal-body-text'),
                                         ]),
                                         dbc.ModalFooter([
                                             html.Div(style={'float': 'left'}, children=[dbc.Button("Cancel", id="modal-cancel", className="ms-auto")]),
                                             dbc.Button(children=["Submit ", html.I(className="fa-solid fa-right-to-bracket")],
                                                        id="modal-submit", className="ms-auto", style={'float': 'left'})]
                                         ),
                                     ]),
                                 ]),
                        html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-3')
                    ])


@callback(
    Output("budget-modal", "is_open"),
    Output('budget-category-dropdown', 'options'),
    Output('budget-category-dropdown', 'value'),
    Output('budget-value-input', 'value'),
    Output('modal-body-text', 'children'),
    Output('modal-body-text', 'style'),
    Output('modal-average-text', 'children'),
    Output('modal-average-text', 'style'),
    Output('modal-delete', 'style'),
    Output('update-tab', 'data', allow_duplicate=True),

    Input("new-budget-button", "n_clicks"),
    Input("modal-cancel", "n_clicks"),
    Input("modal-submit", "n_clicks"),
    Input('budget-category-dropdown', 'value'),
    Input('budget-value-input', 'value'),
    Input('modal-delete', 'n_clicks'),
    Input('modal-average-text', 'children'),
    prevent_initial_call=True,
)
def toggle_budget_modal(open_modal, cancel, submit, budget_category, budget_value, delete_button, avg_str):
    trigger = dash.callback_context.triggered[0]['prop_id']

    is_open = False
    categories = []
    msg_str = ''
    msg_style = {'display': 'none'}
    avg_style = {'padding': '0'}
    update_tab = no_update
    delete = {'display': 'none'}

    if trigger in ['new-budget-button.n_clicks', 'budget-category-dropdown.value', 'budget-value-input.value']:
        if budget_category is not None:
            bv = list(budget_table.find({'category': budget_category}))
            if len(bv) > 0:
                budget_value = budget_value if trigger == 'budget-value-input.value' else bv[0]['value']
                delete = {'float': 'right'}
                avg_style = {'padding': '0 0 25px 0'}
            else:
                budget_value = None

            transactions = pd.DataFrame(transactions_table.find({
                'date': {'$gte': datetime.today() - timedelta(days=180),
                         '$lte': datetime.today()},
                'category': budget_category}))
            if len(transactions) == 0:
                spent = 0
            else:
                spent = transactions.amount.sum() / 6
            avg_str = html.P([f"Monthly spending for '{budget_category}' over the past 6 months: ", html.Br(), f"$ {-spent:.2f}"])
        is_open = True
        categories = get_categories_list()

    elif trigger == 'modal-submit.n_clicks':
        categories = list(transactions_table.find().distinct('category'))
        if budget_category is not None and budget_value is not None:
            MT.add_budget_item(budget_category, budget_value)
            update_tab = True
            budget_category = None
            budget_value = None
            avg_str = None
        else:
            if budget_category is None:
                msg_str = 'You must specify a category'
            else:
                msg_str = 'You must specify a budget amount'
            msg_style = {'padding': '5px 0'}
            is_open = True

    elif trigger == 'modal-delete.n_clicks':
        MT.rm_budget_item(budget_category, budget_value)
        update_tab = True
        budget_category = None
        budget_value = None
        avg_str = None

    elif trigger == 'modal-cancel.n_clicks':
        budget_category = None
        budget_value = None
        avg_str = None

    return is_open, categories, budget_category, budget_value, msg_str, msg_style, avg_str, avg_style, delete, update_tab
