import dash
from dash.dependencies import Input, Output, State
from dash import dash_table
from dash import dcc
from dash import html

import pandas as pd
import plotly.express as px
import plotly.io as pio
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# app requires "pip install psycopg2" as well

server = Flask(__name__)
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# for your home PostgreSQL test table
#app.server.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:teja@123@localhost/sohail"

# for your live Heroku PostgreSQL database
app.server.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://wlgosfslhcwnyl:8d62c472c3b2898579cecaff5fd7847d5256e60a3a5d68710834cf34c72f2eeb@ec2-18-235-114-62.compute-1.amazonaws.com:5432/d61rl9rlkb3nef"

db = SQLAlchemy(app.server)


class Product(db.Model):
    __tablename__ = 'Customerlist'

    CustomerName = db.Column(db.String(50), nullable=False, primary_key=True)
    CustomerJob = db.Column(db.String(50), nullable=False)
    CustomerIncome = db.Column(db.Integer, nullable=False)
    CustomerExpenditure = db.Column(db.Integer, nullable=False)

    def __init__(self, CustomerName, CustomerJob, CustomerIncome, CustomerExpenditure):
        self.CustomerName = CustomerName
        self.CustomerJob = CustomerJob
        self.CustomerIncome = CustomerIncome
        self.CustomerExpenditure = CustomerExpenditure


# ------------------------------------------------------------------------------------------------

app.layout = html.Div([
    html.Div([
        html.Label('CUSTOMER DATA DASHBOARD', id='heading')
    ], style={'font-size': '30px', 'font-family': 'monospace', 'text-align': 'center',
              'margin-bottom': '30px', 'color': 'white'}),

    dcc.Interval(id='interval_pg', interval=86400000*7, n_intervals=0),  # activated once/week or when page refreshed
    html.Div(id='postgres_datatable'),

    html.Button('Add Row', id='editing-rows-button', n_clicks=0, style=
    {'background-color': 'blue', 'opacity': '80%', 'height': '40px', 'width': '150px', 'text-align': 'center',
     'color': 'white', 'border-radius': '15px', 'margin-bottom': '25px',
     'margin-left': '10px', 'box-shadow': 'none', 'border-style': 'groove'}),
    html.Button('Save to PostgreSQL', id='save_to_postgres', n_clicks=0, style=
    {'background-color': '#00D100', 'height': '40px', 'width': '150px', 'text-align': 'center',
     'color': 'white', 'margin-left': '25px', 'border-radius': '15px',
    'margin-bottom': '25px', 'border-style': 'groove'}),

    # Create notification when saving to excel
    html.Div(id='placeholder', children=[]),
    dcc.Store(id='store', data=0),
    dcc.Interval(id='interval', interval=5000),

    dcc.Graph(id='my_graph')

], style={'background-color': '#00003f'})


# ------------------------------------------------------------------------------------------------


@app.callback(Output('postgres_datatable', 'children'),
              [Input('interval_pg', 'n_intervals')])
def populate_datatable(n_intervals):
    df = pd.read_sql_table('Customerlist', con=db.engine)
    return [
        dash_table.DataTable(
            id='our-table',
            columns=[{
                         'name': str(x),
                         'id': str(x),
                         'deletable': False,
                     } if x == 'CustomerName' or x == 'CustomerExpenditure'
                     else {
                'name': str(x),
                'id': str(x),
                'deletable': True,
            }
                     for x in df.columns],
            data=df.to_dict('records'),
            editable=True,
            row_deletable=True,
            filter_action="native",
            sort_action="native",  # give user capability to sort columns
            sort_mode="single",  # sort across 'multi' or 'single' columns
            page_action='none',  # render all of the data at once. No paging.
            style_table={'height': '250px', 'overflowY': 'auto'},
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '100px', 'maxWidth': '100px'},
            style_cell_conditional=[
                {
                    'if': {'column_id': c},
                    'textAlign': 'right'
                } for c in ['CustomerIncome', 'CustomerExpenditure']
            ]
        ),
    ]


@app.callback(
    Output('our-table', 'data'),
    [Input('editing-rows-button', 'n_clicks')],
    [State('our-table', 'data'),
     State('our-table', 'columns')],
    prevent_initial_call=True)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows


@app.callback(
    Output('my_graph', 'figure'),
    [Input('our-table', 'data')],
    prevent_initial_call=True)
def display_graph(data):
    df_fig = pd.DataFrame(data)
    df_fig = df_fig.sort_values(by='CustomerIncome')
    fig = px.bar(df_fig, x=df_fig['CustomerName'], y=df_fig['CustomerIncome'], width=1000, height=400, barmode="group",
                 title="Customers info", hover_data=['CustomerExpenditure', 'CustomerJob'],
                 color_discrete_sequence=['#C1C1C1']*len(df_fig))
    fig.layout.plot_bgcolor = '#3D3D3D'
    fig.layout.paper_bgcolor= '#00003f'
    fig.layout.autosize=False
    return fig


@app.callback(
    [Output('placeholder', 'children'),
     Output('store', 'data')],
    [Input('save_to_postgres', 'n_clicks'),
     Input("interval", "n_intervals")],
    [State('our-table', 'data'),
     State('store', 'data')],
    prevent_initial_call=True)
def df_to_postgres(n_clicks, n_intervals, dataset, s):
    output = html.Plaintext("The data has been saved to your PostgreSQL database.",
                            style={'color': 'green', 'font-weight': 'bold', 'font-size': 'large'})
    no_output = html.Plaintext("", style={'margin': "0px"})

    input_triggered = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if input_triggered == "save_to_postgres":
        s = 6
        pg = pd.DataFrame(dataset)
        pg.to_sql('Customerlist', con=db.engine, if_exists='replace', index=False)
        return output, s
    elif input_triggered == 'interval' and s > 0:
        s = s - 1
        if s > 0:
            return output, s
        else:
            return no_output, s
    elif s == 0:
        return no_output, s


if __name__ == '__main__':
    app.run_server(debug=True)
