# ============================================
# 📄 FILE: C:/Users/Jared/Desktop/John Kelly Dashboard/dashboard.py
# ============================================
# 📊 Executive Weekly Trend Dashboard
# - Smooth lines with missing weeks filled
# - Polished layout and color palette
# - Data labels on points
# ============================================

import pandas as pd
import dash
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
import os

# Load data
incident_df = pd.read_csv('incident.csv', encoding='latin1')
task_df = pd.read_csv('sc_task.csv', encoding='latin1')

# Normalize columns
incident_df.columns = incident_df.columns.str.strip().str.lower()
task_df.columns = task_df.columns.str.strip().str.lower()

# Use only needed columns
incident_df = incident_df[['assigned_to', 'assignment_group', 'opened_at']]
task_df = task_df[['assigned_to', 'assignment_group', 'opened_at']]

# Add source label
incident_df['source'] = 'Incident'
task_df['source'] = 'Task'

# Combine data
combined_df = pd.concat([incident_df, task_df], ignore_index=True)
combined_df['assigned_to'] = combined_df['assigned_to'].fillna('Unassigned')
combined_df['assignment_group'] = combined_df['assignment_group'].fillna('Unknown')
combined_df['opened_at'] = pd.to_datetime(combined_df['opened_at'], errors='coerce')
combined_df = combined_df.dropna(subset=['opened_at'])

# Extract week and year
combined_df['year'] = combined_df['opened_at'].dt.isocalendar().year
combined_df['week'] = combined_df['opened_at'].dt.isocalendar().week
combined_df['week_label'] = combined_df['year'].astype(str) + '-W' + combined_df['week'].astype(str).str.zfill(2)

# Unique values
assignment_groups = sorted(combined_df['assignment_group'].unique())
all_weeks = pd.date_range(start=combined_df['opened_at'].min(), end=combined_df['opened_at'].max(), freq='W-MON')
all_week_labels = all_weeks.isocalendar().year.astype(str) + '-W' + all_weeks.isocalendar().week.astype(str).str.zfill(2)
unique_weeks = sorted(all_week_labels.unique())
unique_people = sorted(combined_df['assigned_to'].unique())

# Init app
app = dash.Dash(__name__)
server = app.server  # Expose server for gunicorn
app.title = "John Kelly Weekly Dashboard"

# Layout
app.layout = html.Div([
    html.H1("\ud83d\udcc8 John Kelly - Weekly Assigned Ticket Trends", style={
        'textAlign': 'center',
        'fontSize': '30px',
        'marginBottom': '10px'
    }),

    html.Div([
        html.Label("Filter by Assignment Group:"),
        dcc.Dropdown(
            id='group-filter',
            options=[{'label': g, 'value': g} for g in assignment_groups],
            placeholder='Select assignment group (optional)',
            clearable=True,
        )
    ], style={'width': '50%', 'margin': '0 auto 25px'}),

    dcc.Graph(id='line-chart'),

    html.Footer("Dashboard by Jared", style={
        'textAlign': 'center',
        'marginTop': '40px',
        'color': '#888',
        'fontSize': '14px'
    })
])

# Callback
@app.callback(
    Output('line-chart', 'figure'),
    Input('group-filter', 'value')
)
def update_chart(selected_group):
    df = combined_df.copy()
    if selected_group:
        df = df[df['assignment_group'] == selected_group]

    grouped = (
        df.groupby(['week_label', 'assigned_to'])
        .size()
        .reset_index(name='count')
    )

    full_index = pd.MultiIndex.from_product([unique_weeks, unique_people], names=['week_label', 'assigned_to'])
    filled = grouped.set_index(['week_label', 'assigned_to']).reindex(full_index, fill_value=0).reset_index()

    week_to_date = {
        label: pd.to_datetime(f"{label}-1", format="%G-W%V-%u") for label in unique_weeks
    }
    filled['week_sort'] = filled['week_label'].map(week_to_date)
    filled = filled.sort_values(by=['week_sort', 'assigned_to'])

    fig = go.Figure()
    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]

    # Sort assigned_to by total volume for consistent hover tooltip order
    totals = (
        filled.groupby('assigned_to')['count']
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    for i, person in enumerate(totals):
        person_df = filled[filled['assigned_to'] == person]

        fig.add_trace(go.Scatter(
            x=person_df['week_label'],
            y=person_df['count'],
            mode='lines+markers+text',
            name=person,
            text=[str(v) if v > 0 else '' for v in person_df['count']],
            textposition='top center',
            textfont=dict(size=11),
            line=dict(color=palette[i % len(palette)], width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>{person}</b><br>Week: %{{x}}<br>Assigned: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        title="\ud83d\udcc5 Weekly Ticket Ownership Trends",
        xaxis_title="Week",
        yaxis_title="Tickets Assigned",
        xaxis=dict(
            tickangle=-45,
            tickmode='linear',
            dtick=2,
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#f0f0f0',
            zeroline=False,
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Segoe UI', size=14),
        margin=dict(l=60, r=30, t=60, b=80),
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            borderwidth=0,
            font=dict(size=13)
        )
    )

    return fig

# Run
if __name__ == '__main__':
    app.run_server(debug=True) 