import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback, ctx
import dash_bootstrap_components as dbc

# ─── Load data ────────────────────────────────────────────────────────────────
slum_data = pd.read_csv('urban-pop-in-out-of-slums.csv')
urban_rural_data = pd.read_csv('urban-and-rural-population.csv')

# ─── Helpers: year handling ───────────────────────────────────────────────────

def get_latest_year_per_country(df):
    """Return the most recent year available for each country."""
    return df.loc[df.groupby('Entity')['Year'].idxmax()].copy()

# All years available in the data
ALL_YEARS = sorted([int(y) for y in slum_data['Year'].dropna().unique()])

# ─── Process data for a given year ────────────────────────────────────────────

def process_year(year):
    """Process slum and urban/rural data for a specific year."""
    slum_year = slum_data[slum_data['Year'] == year].copy()
    slum_year = slum_year[slum_year['Urban population living in slums'] > 0]
    slum_year = slum_year.sort_values('Urban population living in slums', ascending=False)

    urban_year = urban_rural_data[urban_rural_data['Year'] == year].copy()
    urban_year['Total population'] = urban_year['Urban population'] + urban_year['Rural population']
    urban_year['Urban percentage'] = (urban_year['Urban population'] / urban_year['Total population']) * 100

    merged_year = slum_year.merge(
        urban_year[['Entity', 'Urban population', 'Total population', 'Urban percentage']],
        on='Entity', how='inner'
    )
    merged_year['Slum percentage of urban'] = (merged_year['Urban population living in slums'] / merged_year['Urban population']) * 100
    merged_year = merged_year[merged_year['Slum percentage of urban'] <= 100]

    return slum_year, urban_year, merged_year

# Initial processing with default year 2022
DEFAULT_YEAR = 2022 if 2022 in ALL_YEARS else max(ALL_YEARS)
slum_recent, urban_rural_recent, merged = process_year(DEFAULT_YEAR)

# Time series countries
TS_COUNTRIES = ['India', 'Nigeria', 'Brazil', 'Bangladesh', 'China']
slum_ts = slum_data[slum_data['Entity'].isin(TS_COUNTRIES)]
slum_ts = slum_ts[slum_ts['Urban population living in slums'] > 0]

# All countries available for filtering
ALL_COUNTRIES = sorted(merged['Entity'].unique())

# Color palette
PALETTE = {
    'primary': '#636EFA',
    'secondary': '#EF553B',
    'accent': '#00CC96',
    'muted': '#B0B0B0',
    'bg': '#F8F9FA',
    'card': '#FFFFFF'
}

# ─── Helpers ────────────────────────────────────────────────────────────────

def make_bar(df, x, y, title, color_key='primary', selected=None):
    """Build a styled bar chart."""
    colors = [PALETTE['secondary'] if selected and c == selected else PALETTE[color_key] for c in df[x]]
    fig = go.Figure(go.Bar(
        x=df[x], y=df[y],
        marker_color=colors,
        text=df[y].apply(lambda v: f'{v:,.0f}'),
        textposition='outside',
        hovertemplate=f'<b>%{{x}}</b><br>{y}: %{{y:,.0f}}<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=title, font_size=16, x=0.5),
        xaxis_title='', yaxis_title=y,
        yaxis_tickformat=',.0f',
        template='plotly_white',
        margin=dict(l=40, r=20, t=60, b=80),
        paper_bgcolor=PALETTE['card'],
        plot_bgcolor=PALETTE['card'],
        hovermode='closest',
        showlegend=False
    )
    fig.update_xaxes(tickangle=45, tickfont_size=10)
    return fig


def make_scatter(df, selected=None):
    """Build scatter: urbanization % vs slum % of urban."""
    fig = go.Figure()

    if selected:
        other = df[df['Entity'] != selected]
    else:
        other = df

    if len(other) > 0:
        fig.add_trace(go.Scatter(
            x=other['Urban percentage'], y=other['Slum percentage of urban'],
            mode='markers', name='Countries',
            text=other['Entity'],
            marker=dict(size=10, color=PALETTE['primary'], opacity=0.5),
            hovertemplate='<b>%{text}</b><br>Urbanization: %{x:.1f}%<br>Slum %: %{y:.1f}%<extra></extra>'
        ))

    if selected and selected in df['Entity'].values:
        sel = df[df['Entity'] == selected]
        fig.add_trace(go.Scatter(
            x=sel['Urban percentage'], y=sel['Slum percentage of urban'],
            mode='markers', name=f'{selected}',
            text=sel['Entity'],
            marker=dict(size=18, color=PALETTE['secondary'], symbol='diamond',
                        line=dict(width=2, color='black')),
            hovertemplate='<b>%{text}</b><br>Urbanization: %{x:.1f}%<br>Slum %: %{y:.1f}%<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text='Urbanization vs Slum Population Share', font_size=16, x=0.5),
        xaxis_title='Urban population (% of total)',
        yaxis_title='Slum population (% of urban)',
        template='plotly_white',
        paper_bgcolor=PALETTE['card'],
        plot_bgcolor=PALETTE['card'],
        margin=dict(l=40, r=20, t=60, b=40),
        hovermode='closest',
        showlegend=False
    )
    return fig


def make_timeseries(selected=None, filtered_countries=None):
    """Build time-series chart. Respects filtered countries if provided."""
    fig = go.Figure()

    if selected and selected in slum_data['Entity'].values:
        data = slum_data[slum_data['Entity'] == selected]
        data = data[data['Urban population living in slums'] > 0]
        fig.add_trace(go.Scatter(
            x=data['Year'], y=data['Urban population living in slums'],
            mode='lines+markers', name=selected,
            line=dict(color=PALETTE['secondary'], width=3),
            marker=dict(size=8),
            fill='tozeroy', fillcolor='rgba(239, 85, 59, 0.15)',
            hovertemplate='<b>%{x}</b><br>Slum pop: %{y:,.0f}<extra></extra>'
        ))
        title = f'Slum Population Trend: {selected}'
    else:
        countries_to_show = filtered_countries if filtered_countries else TS_COUNTRIES
        colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880']

        for idx, country in enumerate(countries_to_show[:8]):
            cdata = slum_data[slum_data['Entity'] == country]
            cdata = cdata[cdata['Urban population living in slums'] > 0]
            if len(cdata) == 0:
                continue
            fig.add_trace(go.Scatter(
                x=cdata['Year'], y=cdata['Urban population living in slums'],
                mode='lines+markers', name=country,
                line=dict(color=colors[idx % len(colors)], width=2.5),
                marker=dict(size=6),
                hovertemplate=f'<b>{country}</b><br>Year: %{{x}}<br>Slum pop: %{{y:,.0f}}<extra></extra>'
            ))

        if filtered_countries:
            title = f'Slum Population Trends: Filtered Countries'
        else:
            title = 'Slum Population Trends: Top Countries (2000-2022)'

    fig.update_layout(
        title=dict(text=title, font_size=16, x=0.5),
        xaxis_title='Year', yaxis_title='Population in slums',
        yaxis_tickformat=',.0f',
        template='plotly_white',
        paper_bgcolor=PALETTE['card'],
        plot_bgcolor=PALETTE['card'],
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)', font_size=10)
    )
    return fig


# ─── App ────────────────────────────────────────────────────────────────────

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.Div([
        html.H1('Urban Population & Slum Housing Dashboard', className='text-center mt-4 mb-2'),
        html.P('Interactive dashboard exploring global urban population patterns and slum housing conditions.',
               className='text-center text-muted mb-2'),
        html.P('Enter a year and select countries below. Click any chart point to highlight a country across all charts.',
               className='text-center text-muted mb-3', style={'fontSize': '0.9rem'})
    ]),

    # Controls row: Year input + Country filter
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6('Select Year', className='card-title mb-2'),
                    dbc.Input(
                        id='year-input',
                        type='number',
                        value=DEFAULT_YEAR,
                        min=min(ALL_YEARS),
                        max=max(ALL_YEARS),
                        step=1,
                        placeholder='Enter year...'
                    ),
                    html.Div(id='year-display', className='text-center fw-bold mt-2', style={'color': PALETTE['secondary']})
                ])
            ], className='mb-3 shadow-sm')
        ], width=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6('Filter Countries', className='card-title mb-2'),
                    dcc.Dropdown(
                        id='country-filter',
                        options=[{'label': c, 'value': c} for c in ALL_COUNTRIES],
                        multi=True,
                        placeholder='Select countries... (default: all)',
                        style={'fontSize': '0.85rem'}
                    ),
                    dbc.Button('Clear Selection', id='clear-btn', size='sm', color='outline-secondary', className='mt-2')
                ])
            ], className='mb-3 shadow-sm')
        ], width=9)
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id='slum-barchart', config={'displayModeBar': False}, style={'height': '420px'}), width=6),
        dbc.Col(dcc.Graph(id='urban-barchart', config={'displayModeBar': False}, style={'height': '420px'}), width=6),
    ], className='mb-3'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='scatter-plot', config={'displayModeBar': False}, style={'height': '420px'}), width=6),
        dbc.Col(dcc.Graph(id='time-series', config={'displayModeBar': False}, style={'height': '420px'}), width=6),
    ], className='mb-3'),

    html.Div(id='selected-country', className='text-center mb-4 text-muted fw-bold')

], fluid=True, style={'backgroundColor': PALETTE['bg'], 'minHeight': '100vh'})


# ─── Callback ─────────────────────────────────────────────────────────────────

@callback(
    Output('slum-barchart', 'figure'),
    Output('urban-barchart', 'figure'),
    Output('scatter-plot', 'figure'),
    Output('time-series', 'figure'),
    Output('selected-country', 'children'),
    Output('country-filter', 'value'),
    Output('year-display', 'children'),
    Input('year-input', 'value'),
    Input('country-filter', 'value'),
    Input('slum-barchart', 'clickData'),
    Input('urban-barchart', 'clickData'),
    Input('scatter-plot', 'clickData'),
    Input('time-series', 'clickData'),
    Input('clear-btn', 'n_clicks'),
)
def update(year, filtered_countries, slum_click, urban_click, scatter_click, ts_click, clear_clicks):
    triggered = ctx.triggered_id if ctx.triggered_id else ''

    # Handle clear button
    if triggered == 'clear-btn':
        filtered_countries = None

    # ── Validate year ──
    if year is None or year < min(ALL_YEARS) or year > max(ALL_YEARS):
        year = DEFAULT_YEAR
    year = int(year)

    # ── Process data for selected year ──
    slum_year, urban_year, merged_year = process_year(year)

    # Update country filter options if year changed
    available_countries = sorted(merged_year['Entity'].unique())

    # Validate filtered countries against available ones for this year
    if filtered_countries:
        valid_filtered = [c for c in filtered_countries if c in available_countries]
        if len(valid_filtered) != len(filtered_countries):
            filtered_countries = valid_filtered if valid_filtered else None

    # ── Filter datasets ──
    if filtered_countries:
        slum_filtered = slum_year[slum_year['Entity'].isin(filtered_countries)].copy()
        urban_filtered = urban_year[urban_year['Entity'].isin(filtered_countries)].copy()
        merged_filtered = merged_year[merged_year['Entity'].isin(filtered_countries)].copy()
    else:
        slum_filtered = slum_year.copy()
        urban_filtered = urban_year.copy()
        merged_filtered = merged_year.copy()

    # Top 20 from filtered set
    top20_slum = slum_filtered.head(20)
    top20_urban = urban_filtered.nlargest(20, 'Urban population')

    # ── Extract selected country from chart clicks ──
    # Priority: most recent click wins based on which input triggered
    selected = None

    if 'scatter-plot' in triggered and scatter_click and scatter_click.get('points'):
        selected = scatter_click['points'][0].get('text')
    elif 'time-series' in triggered and ts_click and ts_click.get('points'):
        pt = ts_click['points'][0]
        curve = pt.get('curveNumber')
        if curve is not None:
            trace_name = pt.get('data', {}).get('name') if isinstance(pt.get('data'), dict) else None
            if not trace_name and 'fullData' in pt:
                fd = pt['fullData']
                trace_name = fd.get('name') if isinstance(fd, dict) else None
            selected = trace_name
    elif 'urban-barchart' in triggered and urban_click and urban_click.get('points'):
        selected = urban_click['points'][0].get('x')
    elif 'slum-barchart' in triggered and slum_click and slum_click.get('points'):
        selected = slum_click['points'][0].get('x')

    # If nothing triggered specifically but clicks exist, fall back to any available click
    if not selected:
        for click in (scatter_click, ts_click, urban_click, slum_click):
            if click and click.get('points'):
                pt = click['points'][0]
                selected = pt.get('text') or pt.get('x')
                if selected:
                    break

    # ── Build figures ──
    slum_fig = make_bar(top20_slum, 'Entity', 'Urban population living in slums',
                        f'Top 20 Countries by Slum Population ({year})', 'primary', selected)

    urban_fig = make_bar(top20_urban, 'Entity', 'Urban population',
                        f'Top 20 Countries by Urban Population ({year})', 'accent', selected)

    scatter_fig = make_scatter(merged_filtered.head(60), selected)
    ts_fig = make_timeseries(selected, filtered_countries)

    # Status text
    year_text = f'Year: {year}'
    filter_text = f' | Filtered to {len(filtered_countries)} countries' if filtered_countries else ''
    if selected:
        status = f'{year_text}{filter_text} | Viewing: {selected} — click any chart to change.'
    else:
        status = f'{year_text}{filter_text} | Tip: Click any bar or point to highlight a country.'

    return slum_fig, urban_fig, scatter_fig, ts_fig, status, filtered_countries, f'Data for {year}'


server = app.server

if __name__ == '__main__':
    app.run(debug=True, port=8050)