from dash import dcc, html
from datetime import date, timedelta, datetime
import pandas as pd
import plotly.graph_objects as go


from utils import zero_params_dict, MD, update_layout_axes, get_accounts_list


def make_net_worth_plot(conf_dict):
    """Make a plot of the net worth of each account over the time of the Time Window parameter

    Args:
        conf_dict: Dictionary of the configuration parameters.

    Returns: Plotly figure object

    """
    # Ensure it queries all transactions since the beginning
    all_time_config = zero_params_dict()
    all_time_config['start_date'] = '2000-01-01'
    transactions = MD.query_transactions(all_time_config)

    try:  # Drop Venmo transactions that are actually a transfer from another account
        transactions = transactions.drop(transactions[(transactions['account name'] == 'Venmo') & (transactions.notes.str.contains('Source'))].index)
    except AttributeError:
        pass

    if len(transactions) == 0 or transactions.iloc[0].description == 'No Available Data':
        fig_obj = go.Figure()
        update_layout_axes(fig_obj)
        return fig_obj

    else:

        # Get metadata for each account
        if isinstance(MD.accounts_table, pd.DataFrame):
            accounts = MD.accounts_table.find()
        else:
            accounts = pd.DataFrame(MD.accounts_table.find())

        # Make figure
        fig_obj = go.Figure()

        # Get each date to query data, filtering by day/week/month based on overall length of time window
        start_date = datetime.strptime(conf_dict['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(conf_dict['end_date'], '%Y-%m-%d').date()
        display_delta = end_date - start_date
        days = [end_date]
        if display_delta < timedelta(days=32):
            iter_delta = timedelta(days=1)
        elif display_delta < timedelta(days=365):
            iter_delta = timedelta(days=7)
        else:
            iter_delta = timedelta(days=30)

        while True:
            previous_date = date(days[-1].year, days[-1].month, days[-1].day) - iter_delta
            days.append(previous_date)
            if previous_date <= start_date:
                break

        # Calculate net worth at each date
        net_worth = []
        val_dict = {}
        initial_net_worth = accounts['initial balance'].sum()
        for end_day in days:
            this_month = transactions[transactions['date'].dt.date < end_day]
            net_worth.append(this_month['amount'].sum() + initial_net_worth)
            for acc in get_accounts_list():
                acc_status = accounts[accounts['account name'] == acc]
                grp = this_month[this_month['account name'] == acc]
                current_val = grp['amount'].sum() + float(acc_status['initial balance'].iloc[0])
                if abs(current_val) < 0.001:
                    current_val = 0
                try:
                    val_dict[acc].append(current_val)
                except KeyError:
                    val_dict[acc] = [current_val]

        # Convert account net worth data to dataframe to drop accounts that are closed and sort
        val_df = pd.DataFrame(val_dict)
        val_df = val_df.loc[:, (val_df != 0).any(axis=0)]
        recent_worth = val_df.iloc[0]
        recent_worth = recent_worth.sort_values(ascending=False)

        # Plot the account and overall net worth data
        for acc in recent_worth.index:
            if recent_worth[acc] < 0:
                stackgroup = 'one'
            else:
                stackgroup = 'two'
            fig_obj.add_trace(go.Scatter(x=days, y=val_df[acc], name=acc, mode='none', fill='tonexty', stackgroup=stackgroup))

        fig_obj.add_trace(go.Scatter(x=days, y=net_worth, name='Net Worth', mode='markers+lines',
                                     marker={'color': 'black', 'size': 10}, line={'color': 'black', 'width': 3}))

        # Standard figure layout
        update_layout_axes(fig_obj)
        return fig_obj


net_worth_tab = dcc.Tab(label="Net Worth", value='Net Worth', children=[
    html.Div(style={'width': '100%', 'height': '700px', 'padding': '10px 20px', 'align': 'center'}, className='tab-body',
             children=[
                 html.Div(id="net-worth-plot", style={'width': '100%', 'float': 'left', 'padding': '10px 0 0 0'},
                          children=[dcc.Graph(id='net-worth-graph', style={'height': '600px'}, figure=make_net_worth_plot(zero_params_dict()))])
             ]),
])
