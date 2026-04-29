import sys
sys.path.insert(0, '.')
from main import app
from api_extensions import get_ai_suggestions, enhanced_query
from calculators import get_team_pivot, get_team_compressed_table
from data_loader import load_product_df, load_team_df

product_df = load_product_df()
team_df = load_team_df()

r1 = get_ai_suggestions(product_df, team_df, 2026, [1,2,3])
r2 = enhanced_query(product_df, team_df, '物业板块结余', 2026, [1,2,3])
r3 = get_team_pivot(team_df, '05.体验中心', 2026, [1,2,3])
r4 = get_team_compressed_table(team_df, '05.体验中心', 2026, [1,2,3])

print('ALL OK')
print('get_ai_suggestions:', len(r1))
print('enhanced_query type:', r2.get('type'))
print('get_team_pivot rows:', len(r3.get('table', [])))
print('get_team_compressed_table rows:', len(r4.get('rows', [])))
