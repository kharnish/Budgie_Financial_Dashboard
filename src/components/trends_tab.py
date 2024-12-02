import dash
from dash import Dash, callback, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import components.utils as utils
from components.utils import zero_params_dict, MD, update_layout_axes


def make_trends_plot(conf_dict):
    """Make plot object from transactions broken into income and spending.

    Args:
        conf_dict: Dictionary of the configuration parameters

    Returns: Plotly figure object

    """

    def _sort_plot_data():
        if len(transactions) == 0 or transactions.iloc[0].description == 'No Available Data':
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
    transactions = MD.query_transactions(conf_dict)

    # Check if any transaction data, and if not, annotate the plot to let user know it's not broken
    plot_type = conf_dict['plot_type']
    if len(transactions) == 1 and transactions.loc[0]['description'] == 'No Available Data':
        text = 'No data found for these filters. Try selecting a different filter.'
        all_data = MD.transactions_table.find()
        try:
            len(all_data)
            desc = all_data.loc[0]['description']
        except TypeError:
            all_data = list(all_data)
            desc = all_data[0]['description'] == 'No Available Data'
        if len(all_data) == 1 and desc == 'No Available Data':
            text = 'No data found. Start by adding a transaction CSV file or individual transaction on the right.'
        plot_type = 'text_only'

    # Filter transactions to display
    transactions = transactions[~transactions['category'].isin(MD.get_hide_from_trends())]

    # Make bar plot
    if plot_type == 'bar':
        fig_obj = go.Figure()
        lab_val = _sort_plot_data()
        trace_count = 0
        trace_dict = {}
        for in_sp in ['Spending', 'Income']:
            for i in range(len(lab_val[in_sp]['values'])):
                show_trace = True  # If category has both spending and income, hide the second trace so it only shows up once in the legend
                name = lab_val[in_sp]['labels'][i]
                trace_color = trace_dict.get(name)
                if trace_color is None:
                    trace_color = trace_count
                    trace_dict[name] = trace_count
                    trace_count += 1
                else:
                    show_trace = False

                fig_obj.add_trace(go.Bar(y=[in_sp], x=[lab_val[in_sp]['values'][i]], name=name, legendgroup=name,
                                         marker_color=utils.get_color(trace_color), showlegend=show_trace,
                                         orientation='h', meta=lab_val[in_sp]['labels'][i],
                                         hovertemplate="%{meta}<br>$%{x:,.2f}<extra></extra>"))
        fig_obj.update_yaxes(title_text="Expenditures")

        fig_obj.update_xaxes(title_text="Amount ($)")
        fig_obj.update_layout(barmode='stack')

    # Or make pie plot
    elif plot_type == 'pie':
        fig_obj = make_subplots(rows=1, cols=2, subplot_titles=['Income', 'Spending'], specs=[[{'type': 'domain'}, {'type': 'domain'}]])
        lab_val = _sort_plot_data()
        # TODO try and figure out a better hover label for the plots
        fig_obj.add_trace(go.Pie(labels=lab_val['Income']['labels'], values=lab_val['Income']['values'],
                                 meta=lab_val['Income']['values'], hovertemplate="%{label}<br>$%{meta:,.2f}<extra></extra>"), 1, 1)
        fig_obj.add_trace(go.Pie(labels=lab_val['Spending']['labels'], values=lab_val['Spending']['values'],
                                 meta=lab_val['Spending']['values'], hovertemplate="%{label}<br>$%{meta:,.2f}<extra></extra>"), 1, 2)

    # Or plot over time
    elif plot_type == 'time':
        fig_obj = go.Figure()

        # Get each date to query data, filtering by day/week/month based on overall length of time window
        start_date = datetime.strptime(conf_dict['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(conf_dict['end_date'], '%Y-%m-%d').date()
        display_delta = end_date - start_date
        days = [end_date]
        if display_delta < timedelta(days=32):
            iter_delta = relativedelta(weeks=1)
        elif display_delta < timedelta(days=365):
            iter_delta = relativedelta(months=1)
            days.append(date(end_date.year, end_date.month, 1))
        else:
            iter_delta = relativedelta(years=1)
            days.append(date(end_date.year, 1, 1))
        while True:
            previous_date = date(days[-1].year, days[-1].month, days[-1].day) - iter_delta
            days.append(previous_date)
            if previous_date <= start_date:
                break

        # Calculate spending at each date
        val_dict = {}
        net = []
        for i in range(len(days) - 1):
            this_month = transactions[(transactions['date'].dt.date < days[i]) & (transactions['date'].dt.date >= days[i + 1])]
            net.append(this_month['amount'].sum())
            for cat, grp in this_month.groupby('category'):
                try:
                    val_dict[cat]['date'].append(days[i + 1])
                    val_dict[cat]['amount'].append(grp['amount'].sum())
                except KeyError:
                    val_dict[cat] = {'date': [days[i + 1]], 'amount': [grp['amount'].sum()]}

        # Alphabetize list of categories
        val_dict = dict(sorted(val_dict.items()))

        # Add lines and bars
        fig_obj.add_trace(go.Scatter(x=days[1:], y=net, name='Net Transactions', mode='markers+lines',
                                     marker={'color': 'black', 'size': 10}, line={'color': 'black', 'width': 3},
                                     hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>"))
        for key, val in val_dict.items():
            fig_obj.add_trace(go.Bar(x=val['date'], y=val['amount'], name=key, legendgroup=key,
                                     meta=key, hovertemplate="%{meta}<br>$%{y:,.2f}<extra></extra>"))

        fig_obj.update_xaxes(title_text="Date")
        fig_obj.update_yaxes(title_text="Amount ($)")
        fig_obj.update_layout(barmode='relative')

    elif plot_type == 'text_only':
        fig_obj = go.Figure()
        fig_obj.add_annotation(text=text, xref="paper", yref="paper", x=0.5, y=0.75, showarrow=False,
                               bordercolor="#162432", borderwidth=2, borderpad=5, bgcolor="#AFBDCB",
                               font=dict(size=20))
    update_layout_axes(fig_obj)
    return fig_obj


trends_tab = dcc.Tab(label="Trends", value='Trends', children=[
    html.Div(style={'width': '100%', 'height': '700px', 'padding': '10px 20px', 'align': 'center'}, className='tab-body',
             children=[
                 html.Div(style={'padding': '15px 7px', 'float': 'right'}, id='help-trends',
                          children=[html.I(className="fa-solid fa-circle-question")]),
                 dbc.Modal(id="trends-help", is_open=False, children=[
                     dbc.ModalHeader(dbc.ModalTitle("Trends Help")),
                     dbc.ModalBody(children=['The Trends tab helps you visualize overall trends in your money flow.', html.Br(), html.Br(),
                                             'There are three types of plots: ',
                                             html.Li('Bar: To compare income vs spending'),
                                             html.Li('Pie: To compare percent of spending per category'),
                                             html.Li('Over time: To compare spending and income over time'), html.Br(),
                                             "The graphs with auto-populate according to the filters given on the left. "
                                             "If you don't see any data, try changing a filter (most likely the time window).", html.Br(), html.Br(),
                                             'To interact with the plot, you can click and double click the legend items to hide them, and click and drag to zoom in and move around.'
                                             ])]),
                 html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                          children=[html.Button(style={'width': '120px', 'padding': '0'},
                                                children=["Over Time ", html.I(className="fa-solid fa-arrow-trend-up")], id="time-button")]),
                 html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                          children=[html.Button(style={'width': '75px', 'padding': '0'},
                                                children=["Pie ", html.I(className="fas fa-chart-pie")], id="pie-button")]),
                 html.Div(style={'padding': '10px 5px', 'display': 'inline-block', 'float': 'right'},
                          children=[html.Button(style={'width': '85px', 'padding': '0'},
                                                children=["Bar ", html.I(className="fa-solid fa-chart-column")], id="bar-button")]),
                 html.Div(id="trends-plot", style={'width': '100%', 'float': 'left', 'padding': '10px 0 0 0'},
                          children=[dcc.Graph(id='trends-graph', style={'height': '600px'}, figure=make_trends_plot(zero_params_dict()))]),
                 html.Div(style={'height': '8px', 'width': '75%', 'float': 'left'}, id='blank-space-1')
             ]),
])


@callback(
    Output('trends-help', 'is_open'),
    Input('help-trends', 'n_clicks')
)
def help_modal(clicks):
    isopen = False
    trigger = dash.callback_context.triggered[0]['prop_id']
    if trigger == 'help-trends.n_clicks':
        isopen = True
    return isopen
