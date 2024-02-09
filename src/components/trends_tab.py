from dash import Dash, callback, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import zero_params_dict, update_layout_axes, get_mongo_transactions, EXCLUDE_FROM_BUDGET


def make_trends_plot(conf_dict):
    """Make plot object from transactions broken into income and spending.

    Args:
        conf_dict: Dictionary of the configuration parameters

    Returns: Plotly figure object

    """
    def _sort_plot_data():
        if len(transactions) == 0 or transactions.iloc[0].description == 'No Available Data':
            # TODO Error, no transactions found for the given filters
            l_v = {'Spending': {'labels': [0], 'values': [0]},
                   'Income': {'labels': [0], 'values': [0]}}
        else:
            l_v = {'Spending': {'labels': [], 'values': []},
                   'Income': {'labels': [], 'values': []}}
            for cat, grp in transactions.groupby(conf_dict['field_filter'].lower()):
                inc_amount = grp['amount'][grp['amount'] > 0].sum()
                spd_amount = grp['amount'][grp['amount'] < 0].sum()
                if spd_amount:
                    l_v['Spending']['labels'].append(cat)
                    l_v['Spending']['values'].append(-spd_amount)
                if inc_amount:
                    l_v['Income']['labels'].append(cat)
                    l_v['Income']['values'].append(inc_amount)

        for spin in ['Spending', 'Income']:
            if len(l_v[spin]['values']) > 0:
                l_v[spin]['values'], l_v[spin]['labels'] = zip(*sorted(zip(l_v[spin]['values'], l_v[spin]['labels']), key=lambda x: x[0], reverse=True))
            else:
                l_v[spin]['values'], l_v[spin]['labels'] = [0], [0]
        return l_v

    # Get transactions
    transactions = get_mongo_transactions(conf_dict)
    transactions = transactions[~transactions['category'].isin(EXCLUDE_FROM_BUDGET)]

    # Make bar plot
    if conf_dict['plot_type'] == 'bar':
        fig_obj = go.Figure()
        lab_val = _sort_plot_data()
        for in_sp in ['Spending', 'Income']:
            for i in range(len(lab_val[in_sp]['values'])):
                fig_obj.add_trace(go.Bar(y=[in_sp], x=[lab_val[in_sp]['values'][i]], name=lab_val[in_sp]['labels'][i], orientation='h',
                                         meta=lab_val[in_sp]['labels'][i],
                                         hovertemplate="%{meta}<br>$%{x:.2f}<extra></extra>"))
        fig_obj.update_yaxes(title_text="Expenditures")

        fig_obj.update_xaxes(title_text="Amount ($)")
        fig_obj.update_layout(barmode='stack')

    # Or make pie plot
    elif conf_dict['plot_type'] == 'pie':
        fig_obj = make_subplots(rows=1, cols=2, subplot_titles=['Income', 'Spending'], specs=[[{'type': 'domain'}, {'type': 'domain'}]])
        lab_val = _sort_plot_data()
        # TODO try and figure out a better hover label for the plots
        fig_obj.add_trace(go.Pie(labels=lab_val['Income']['labels'], values=lab_val['Income']['values'], textinfo='percent+label',
                                 meta=lab_val['Income']['values'], hovertemplate="$%{meta:.2f}<extra></extra>"), 1, 1)
        fig_obj.add_trace(go.Pie(labels=lab_val['Spending']['labels'], values=lab_val['Spending']['values'], textinfo='percent+label',
                                 meta=lab_val['Spending']['values'], hovertemplate="$%{meta:.2f}<extra></extra>"), 1, 2)

    # Standard figure layout
    update_layout_axes(fig_obj)
    return fig_obj


trends_tab = dcc.Tab(label="Trends", value='Trends', children=[
                        html.Div(style={'width': '100%', 'height': '700px', 'padding': '10px 20px', 'align': 'center'}, className='tab-body',
                                 children=[
                                     html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                                              children=[html.Button(style={'width': '75px', 'padding': '0'},
                                                                    children=["Pie ", html.I(className="fas fa-chart-pie")], id="pie-button")]),
                                     html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                                              children=[html.Button(style={'width': '75px', 'padding': '0'},
                                                                    children=["Bar ", html.I(className="fa-solid fa-chart-column")], id="bar-button")]),
                                     html.Div(id="trends-plot", style={'width': '100%', 'float': 'left', 'padding': '10px 0 0 0'},
                                              children=[dcc.Graph(id='trends-graph', style={'height': '600px'}, figure=make_trends_plot(zero_params_dict()))]),
                                     html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-1')
                                 ]),
                    ])
