import dash
from dash import callback, dcc, html, Input, Output, no_update, dash_table
import dash_bootstrap_components as dbc
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utils import zero_params_dict, MD, update_layout_axes, COLORS, get_categories_list


def make_budget_plots(conf_dict):
    """Make bar plot of budget, showing spending and spending limit for each category.

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Plotly figure object

    """
    # Get and alphabetize list of categories
    pos_dict, neg_dict = MD.get_budget_dict()
    pos_dict = dict(sorted(pos_dict.items(), reverse=True))
    neg_dict = dict(sorted(neg_dict.items(), reverse=True))

    transactions = MD.query_transactions(conf_dict)

    # Calculate overall percent of budget for multiple months
    start_date = datetime.strptime(conf_dict['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(conf_dict['end_date'], '%Y-%m-%d').date()
    display_delta = max(end_date - start_date, timedelta(days=1))
    months = np.ceil(display_delta.days / 31)

    fig_income = go.Figure()
    fig_spend = go.Figure()

    percent_list = []
    for fig, budget_dict in [[fig_income, pos_dict], [fig_spend, neg_dict]]:
        for cat in budget_dict.keys():
            spent = float(transactions[transactions['category'] == cat]['amount'].sum())
            budgeted = budget_dict[cat] * months
            percent = 100 * spent / budgeted
            percent_list.append(percent)
            diff = spent - budgeted

            if budgeted >= 0:
                # Income Budget
                hovertemplate = "Income:     %{meta[1]}<br>Budgeted: %{meta[0]}<extra></extra>"
                if diff < 0:
                    m = f"Expected: $ {-diff:,.2f}"
                else:
                    m = f"Extra: $ {diff:,.2f}"
                meta = [f"$ {budgeted:,.2f}", f"$ {spent:,.2f}"]
            else:
                # Spending Budget
                hovertemplate = "Spent:       %{meta[1]}<br>Budgeted: %{meta[0]}<extra></extra>"
                if diff > 0:
                    m = f"Remaining: $ {diff:.2f}"
                else:
                    m = f"Over: $ {-diff:.2f}"
                meta = [f"$ {-budgeted:,.2f}", f"$ {-spent:,.2f}"]

            fig.add_trace(go.Bar(y=[cat], x=[percent], name=cat, orientation='h', text=m, textposition="outside",
                                 meta=meta, hovertemplate=hovertemplate))

        max_x = max(percent_list) if percent_list else 0
        min_x = min(percent_list) if percent_list and min(percent_list) < 0 else 0
        fig.update_layout(xaxis_range=[min_x * 1.15, max_x * 1.15])

        # Make a vertical line to limit and progress through the month
        today = date.today()
        if start_date <= today <= end_date:
            progress = (today - start_date).days
            progress = 100 * progress / (31 * months)
            fig.add_vline(x=progress, line_width=1, line_color=COLORS['light'].get('gridgray'))
        fig.add_vline(x=100, line_width=3, line_color=COLORS['light'].get('gridgray'))

        # Standard figure layout, but don't show horizontal lines
        update_layout_axes(fig)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        fig.update_layout(showlegend=False)

    fig_spend.update_xaxes(title_text="% Spent")

    # Use a quick linear equation to get the height of the plot based on the number of bars
    m = 42.573
    b = 75.297
    income_height = m * len(pos_dict) + b
    income_style = {'height': f"{income_height if len(pos_dict) > 1 else 85}px", 'padding': '0 10px', 'align': 'center'}
    spend_height = m * len(neg_dict) + b
    spend_style = {'height': f"{spend_height if len(neg_dict) > 1 else 85}px", 'padding': '0 10px', 'align': 'center'}

    # Calculate the budget overview table, starting with the sum of the budget
    pos_dict, neg_dict = MD.get_budget_dict()
    est_income = sum([v for k, v in pos_dict.items()])
    est_spend = sum([v for k, v in neg_dict.items()])
    est_delta = est_income + est_spend
    if est_delta < 0:
        est_color = 'firebrick'
    else:
        est_color = '#162432'

    # Now get the actual current status
    transactions = transactions[~transactions['category'].isin(MD.get_hide_from_trends())]
    act_income = transactions['amount'][transactions['amount'] > 0].sum()
    act_spend = transactions['amount'][transactions['amount'] < 0].sum()
    act_delta = act_income + act_spend
    if act_delta < 0:
        act_color = 'firebrick'
    else:
        act_color = '#162432'

    # Lastly, write out the actual table
    equation = [html.Table([
        html.Tr(style={'textAlign': 'center', 'fontWeight': 'bold', 'text-decoration': 'underline', 'padding-bottom': '5px'},
                children=[html.Td(''), html.Td('Actual'), html.Td('Budgeted')]),
        html.Tr([html.Td('Income'),
                 html.Td(style={'textAlign': 'right', 'fontWeight': 'bold'}, children=[f"$ {act_income:,.2f}"]),
                 html.Td(style={'textAlign': 'right'}, children=[f"$ {est_income:,.2f}"])]),
        html.Tr(style={'border-bottom': '1pt solid black'},
                children=[html.Td('Spending'),
                          html.Td(style={'textAlign': 'right', 'fontWeight': 'bold'}, children=[f"$ {act_spend:,.2f}"]),
                          html.Td(style={'textAlign': 'right'}, children=[f"$ {est_spend:,.2f}"])]),
        html.Tr([html.Td('Remaining'),
                 html.Td(style={'textAlign': 'right', 'fontWeight': 'bold', 'color': act_color}, children=[f"$ {act_delta:,.2f}"]),
                 html.Td(style={'textAlign': 'right', 'color': est_color}, children=[f"$ {est_delta:,.2f}"])])
    ])]

    return fig_income, income_style, fig_spend, spend_style, equation


initial_plots = make_budget_plots(zero_params_dict())

budget_tab = dcc.Tab(label="Budget", value='Budget', className='tab-body', children=[
    html.Div(id="budget-plot", style={'width': '100%', 'float': 'left'}, className='tab-body',
             children=[
                 html.Div(style={'padding': '10px 15px 0 0', 'float': 'right'}, id='help-budget',
                          children=[html.I(className="fa-solid fa-circle-question")]),
                 dbc.Modal(id="budget-help", is_open=False, children=[
                     dbc.ModalHeader(dbc.ModalTitle("Budget Help")),
                     dbc.ModalBody(children=['The Budget tab allows you to set budgets for each category and see your progress.', html.Br(), html.Br(),
                                             'Set a new category budget or update an exising budget with the Add or Update Budget button.', html.Br(), html.Br(),
                                             'The categories are split into Income and Spending budgets. The table below the budget graphs shows your total budgeted income vs spending.', html.Br(),
                                             html.Br(),
                                             'The thick line vertical shows your limit of 100% per category, while the thinner line shows how far through the month you are.'])]),

                 html.Div(style={'display': 'inline-block', 'padding': '10px', 'float': 'left'},
                          children=[dbc.Button(id='new-budget-button', style={'width': '200px'},
                                               children=['Add Or Update Budget ', html.I(className="fa-solid fa-pen-to-square")])]),

                 html.Div(style={'display': 'inline-block', 'padding': '10px'}, children=[
                     html.Div(id='budget-equation', style={'display': 'inline-block', 'padding': '5px 10px', 'background-color': '#dfe3ea'},
                              children=[html.Table([html.Table([
                                  html.Tr(style={'textAlign': 'center', 'fontWeight': 'bold', 'text-decoration': 'underline', 'padding-bottom': '5px'},
                                          children=[html.Td(''), html.Td('Actual'), html.Td('Budgeted')]),
                                  html.Tr([html.Td('Income'),
                                           html.Td(style={'textAlign': 'right', 'fontWeight': 'bold'}, children=[f"$ {1234:,.2f}"]),
                                           html.Td(style={'textAlign': 'right'}, children=[f"$ {1234:,.2f}"])]),
                                  html.Tr(style={'border-bottom': '1pt solid black'},
                                          children=[html.Td('Spending'),
                                                    html.Td(style={'textAlign': 'right', 'fontWeight': 'bold'}, children=[f"$ {-1234:,.2f}"]),
                                                    html.Td(style={'textAlign': 'right'}, children=[f"$ {-1234:,.2f}"])]),
                                  html.Tr([html.Td('Remaining'),
                                           html.Td(style={'textAlign': 'right', 'fontWeight': 'bold'}, children=[f"$ {0:,.2f}"]),
                                           html.Td(style={'textAlign': 'right'}, children=[f"$ {0:,.2f}"])])
                              ])])])
                 ]),

                 html.Div(style={'padding': '0 0 0 40px'}, children=[html.H4(['Income'])]),
                 dcc.Graph(style=initial_plots[1], id='budget-graph-income', figure=initial_plots[0]),
                 html.Div(style={'padding': '10px 0 0 40px'}, children=[html.H4(['Spending'])]),
                 dcc.Graph(style=initial_plots[3], id='budget-graph-spend', figure=initial_plots[2]),

                 html.Div(style={'height': '5px', 'width': '99%', 'float': 'left'}, id='blank-space-4'),

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

                 html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='bottom-space-1')
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

    if trigger in ['new-budget-button.n_clicks', 'budget-category-dropdown.value']:
        if budget_category is not None:
            if isinstance(MD.budget_table, pd.DataFrame):
                bv = MD.budget_table.find({'category': budget_category})
            else:
                bv = list(MD.budget_table.find({'category': budget_category}))
            if len(bv) > 0:
                try:
                    budget_value = budget_value if trigger == 'budget-value-input.value' else bv[0]['value']
                except KeyError:
                    budget_value = budget_value if trigger == 'budget-value-input.value' else bv.iloc[0]['value']
                delete = {'float': 'right'}
                avg_style = {'padding': '0 0 25px 0'}
            else:
                budget_value = None

            transactions = pd.DataFrame(MD.transactions_table.find({
                'date': {'$gte': datetime.today() - timedelta(days=180),
                         '$lte': datetime.today()},
                'category': budget_category}))
            if len(transactions) == 0:
                spent = 0
            else:
                spent = transactions.amount.sum() / 6
            if spent <= 0:
                avg_str = html.P([f"Monthly spending for '{budget_category}' over the past 6 months: ", html.Br(), f"$ {spent:.2f}"])
            else:
                avg_str = html.P([f"Monthly income for '{budget_category}' over the past 6 months: ", html.Br(), f"$ {spent:.2f}"])
        is_open = True
        categories = get_categories_list()

    elif trigger == 'budget-value-input.value':
        is_open = True
        categories = get_categories_list()

    elif trigger == 'modal-submit.n_clicks':
        categories = list(MD.transactions_table.find().distinct('category'))
        if budget_category is not None and budget_value is not None:
            MD.add_budget_item(budget_category, budget_value)
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
        MD.rm_budget_item(budget_category, budget_value)
        update_tab = True
        budget_category = None
        budget_value = None
        avg_str = None

    elif trigger == 'modal-cancel.n_clicks':
        budget_category = None
        budget_value = None
        avg_str = None

    return is_open, categories, budget_category, budget_value, msg_str, msg_style, avg_str, avg_style, delete, update_tab


@callback(
    Output('budget-help', 'is_open'),
    Input('help-budget', 'n_clicks')
)
def help_modal(clicks):
    isopen = False
    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'help-budget.n_clicks':
        isopen = True
    return isopen
