"""Reproduce synthetic cases and the game-data snapshot plan (standard library only)."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from mystia_planner.io import load_dataset, write_json_report, write_csv_report
from mystia_planner.models import Settings
from mystia_planner.planner import plan_dataset

data = load_dataset(root / 'data/demo.json')
cases = {
    'demo-plan': Settings(cookware_count=3),
    'one-cookware': Settings(cookware_count=1),
    'high-demand': Settings(cookware_count=3, orders_per_day=15),
    'trend-hate': Settings(cookware_count=3, trend_hate=frozenset({'下酒'})),
}
for name, settings in cases.items():
    report = plan_dataset(data, settings)
    write_json_report(report, root / f'examples/{name}.json')
    if name == 'demo-plan':
        write_csv_report(report, root / 'examples/demo-plan.csv')
    print(json.dumps({'case': name, 'cookware': report['selected_cookware'],
        'summary': report['summary'], 'plans': [{key: row[key] for key in ('guest', 'status', 'plan')} for row in report['guests']]}, ensure_ascii=False))

game_data = load_dataset(root / 'data/game.json')
game_report = plan_dataset(game_data, Settings(cookware_count=3))
write_json_report(game_report, root / 'examples/game-plan.json')
write_csv_report(game_report, root / 'examples/game-plan.csv')
print(json.dumps({'case': 'game-plan', 'cookware': game_report['selected_cookware'],
    'summary': game_report['summary']}, ensure_ascii=False))
