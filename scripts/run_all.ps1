$env:PYTHONPATH = "src"
python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
python -m uavtre.make_review_pack --mode anonymous
python -m uavtre.make_review_pack --mode camera_ready
