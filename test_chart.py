import database, app

df = database.query_weather_by_region('臺中市')
fig = app.render_temperature_chart(df, '臺中市')
assert len(fig.data) == 2, "Should have 2 traces (MaxT + MinT)"
assert fig.layout.plot_bgcolor == '#FFFFFF', "Background should be white"
assert fig.layout.xaxis.gridcolor == '#F1F5F9', "X gridcolor check"
print('[PASS] Chart traces:', len(fig.data))
print('[PASS] Plotly 7 layout OK - no API errors.')
