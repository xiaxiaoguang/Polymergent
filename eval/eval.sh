python run_eval.py --list-splits
python run_eval.py --list-sources

# see pool size, no API
python build_hard_split.py --split all --n 0 --model deepseek-flash --answer-type "ranking" --offset 20
python build_hard_split.py --split all --n 0 --model deepseek-flash --answer-type "multipleChoice"
python build_hard_split.py --split all --n 0 --model deepseek-flash --answer-type "exactMatch"
# full filter with Haiku
python build_hard_split.py --split all --n 0 --model claude-haiku-4-5-20251001

# only numeric PropQA, first 50
python build_hard_split.py --split numeric --n 50

# recover after a crash
python build_hard_split.py --split all --resume results/hard_filter/filter_report.json

python filter.py \
  --dataset /home/hcao5/workspace/datasets/polymer/data/polymer/external_tasks.json \
  --reports /home/hcao5/workspace/polymer/eval/results/hard_filter/filter_report.json \
  --only-failed \
  --out /home/hcao5/workspace/datasets/polymer/data/polymer/external_tasks2.json

