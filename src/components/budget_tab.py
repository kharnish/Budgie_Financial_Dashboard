import dash
from dash import callback, dcc, html, Input, Output, no_update, dash_table
import dash_bootstrap_components as dbc
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utils import zero_params_dict, MD, update_layout_axes, COLORS


def make_budget_plots(conf_dict):
    """Make bar plot of budget, showing spending and spending limit for each category.

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Plotly figure object

    """
    # Get and alphabetize list of categories
    pos_dict, neg_dict, grp_dict = MD.get_budget_dict()
    pos_dict = dict(sorted(pos_dict.items(), reverse=True))
    neg_dict = dict(sorted(neg_dict.items(), reverse=True))
    grp_dict = dict(sorted(grp_dict.items(), reverse=True))

    transactions = MD.query_transactions(conf_dict)

    # Calculate overall percent of budget for multiple months
    start_date = datetime.strptime(conf_dict['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(conf_dict['end_date'], '%Y-%m-%d').date()
    display_delta = max(end_date - start_date, timedelta(days=1))
    months = np.ceil(display_delta.days / 31)

    fig_income = go.Figure()
    fig_spend = go.Figure()
    fig_group = go.Figure()

    count = 0
    for fig, budget_dict in [[fig_income, pos_dict], [fig_spend, neg_dict], [fig_group, grp_dict]]:
        percent_list = []
        count += 1
        for cat in budget_dict.keys():
            # Get overall spending depending on if it's the normal single categories or a group category
            if count == 3:
                categories = MD.get_children_categories_list(cat)
                spent = float(transactions[transactions['category'].isin(categories)]['amount'].sum())
            else:
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

    # Update axis labels (according to how large the plot is)
    fig_income.update_xaxes(title_text="% Spent")
    fig_spend.update_xaxes(title_text="% Spent")
    if len(grp_dict) >= 4:
        fig_spend.update_yaxes(title_text="Individual Category Budgets")
    elif len(grp_dict) >= 2:
        fig_spend.update_yaxes(title_text="Individual Category<br>Budgets")
    else:
        fig_spend.update_yaxes(title_text="Individual<br>Category<br>Budgets")
    if len(grp_dict) >= 4:
        fig_group.update_yaxes(title_text="Group Category Budgets")
    elif len(grp_dict) >= 2:
        fig_group.update_yaxes(title_text="Group Category<br>Budgets")
    else:
        fig_group.update_yaxes(title_text="Group<br>Category<br>Budgets")

    # Use a quick linear equation to get the height of the plot based on the number of bars
    m = 42.573
    b = 75.297
    income_height = m * len(pos_dict) + b
    income_style = {'height': f"{income_height if len(pos_dict) > 1 else 85}px", 'padding': '0 10px', 'align': 'center'}
    if len(grp_dict) > 0:
        group_height = m * len(grp_dict) + b
        group_style = {'height': f"{group_height if len(grp_dict) > 1 else 85}px", 'padding': '0 10px', 'align': 'center'}
    else:
        group_style = {'display': 'none'}
    spend_height = m * len(neg_dict) + b
    spend_style = {'height': f"{spend_height if len(neg_dict) > 1 else 85}px", 'padding': '0 10px', 'align': 'center'}

    # Moving on to the budget table:
    # Calculate the budget overview table, starting with the sum of the budget
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

    return fig_income, income_style, fig_group, group_style, fig_spend, spend_style, equation


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
                                             'The categories are split into Income and Spending budgets. The table below the budget graphs shows your total budgeted income vs spending.', html.Br(), html.Br(),
                                             'The thick line vertical shows your limit of 100% per category, while the thinner line shows how far through the month you are.', html.Br(), html.Br(),
                                             'Budgie uses a Zero-Based Budget, which means that every dollar you expect to earn should be accounted for in either in expenses or savings. This is '
                                             'reflected in the Actuals/Budget table that shows your total actual and budgeted income and spending over the month.'
                                             ])]),

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
                 dcc.Graph(style=initial_plots[3], id='budget-graph-group', figure=initial_plots[2]),
                 dcc.Graph(style=initial_plots[5], id='budget-graph-spend', figure=initial_plots[4]),

                 html.Div(style={'height': '5px', 'width': '99%', 'float': 'left'}, id='blank-space-4'),

                 dbc.Modal(id="budget-modal", is_open=False, children=[
                     dbc.ModalHeader(dbc.ModalTitle("Add New Budget Item")),
                     dbc.ModalBody(children=[
                         html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '0px 5px 5px 0'},
                                  children=['Select budget category:',
                                            dcc.Dropdown(id='budget-category-dropdown', className='dropdown', clearable=True, placeholder='Select category...',
                                                         style={'display': 'inline-block', 'width': '400px', 'vertical-align': 'middle'},
                                                         options=[''])]),
                         html.Div(style={'display': 'inline-block', 'width': 'auto', 'padding': '5px 0 10px 0'},
                                  children=[html.Div(id='budget-num-text-input', style={'padding': '0'}, children=['Budget amount:']),
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
    Output('budget-value-input', 'disabled'),
    Output('modal-body-text', 'children'),
    Output('modal-body-text', 'style'),
    Output('modal-average-text', 'children'),
    Output('modal-average-text', 'style'),
    Output('modal-delete', 'style'),
    Output('budget-num-text-input', 'children'),
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
    num_text = 'Budget amount:'
    input_disabled = False

    if trigger == 'new-budget-button.n_clicks':
        budget_category = None
        is_open = True
        categories = MD.get_categories_list('parent')
        budget_value = None
        avg_str = None

    elif trigger == 'budget-category-dropdown.value':
        # Query the budget database to see if a budget for those categories
        bv = MD.get_budget_amount(budget_category)

        # If it's a parent category, then give the default budget amount
        if budget_category in MD.get_categories_list('parent_only'):
            budget_value = 0
            transactions = pd.DataFrame()
            for child_cat in MD.get_children_categories_list(budget_category):
                # Get the total budgeted amount for all child categories
                budget_value += MD.get_budget_amount(child_cat)
                # Query all transactions to get the average spent per all child categories
                transactions = pd.concat([transactions, pd.DataFrame(MD.transactions_table.find({
                    'date': {'$gte': datetime.today() - timedelta(days=180),
                             '$lte': datetime.today()},
                    'category': child_cat}))])
            num_text = 'Budget group amount:'
            input_disabled = True

        # But if it's a single category, allow value input
        else:
            if bv != 0:
                budget_value = budget_value if trigger == 'budget-value-input.value' else bv
            else:
                budget_value = None
            # Query all transactions to get the average spent per the categories specified
            transactions = pd.DataFrame(MD.transactions_table.find({
                'date': {'$gte': datetime.today() - timedelta(days=180),
                         '$lte': datetime.today()},
                'category': budget_category}))

        # Check if value exists, if so, give option to delete it
        if bv != 0:
            delete = {'float': 'right'}
            avg_style = {'padding': '10px 0 25px 0'}

        if len(transactions) == 0:
            spent = 0
        else:
            spent = transactions.amount.sum() / 6
        if spent <= 0:
            avg_str = html.P([f"Monthly spending for {budget_category} over the past 6 months: ", html.Br(), f"$ {spent:.2f}"])
        else:
            avg_str = html.P([f"Monthly income for {budget_category} over the past 6 months: ", html.Br(), f"$ {spent:.2f}"])

        is_open = True
        categories = MD.get_categories_list('parent')

    elif trigger == 'budget-value-input.value':
        is_open = True
        categories = MD.get_categories_list('parent')

    elif trigger == 'modal-submit.n_clicks':
        categories = list(MD.transactions_table.find().distinct('category'))
        if budget_category is not None and budget_value is not None and budget_value != 0:
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

    return is_open, categories, budget_category, budget_value, input_disabled, msg_str, msg_style, avg_str, avg_style, delete, num_text, update_tab


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
