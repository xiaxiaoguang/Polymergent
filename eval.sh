# 1. lab inspection / safety (hardest text+image items first)
python run_eval.py --mode llm --split protocol --n 5 --judge --judge-model gpt-5.6-luna
python run_eval.py --mode agent --split protocol --n 5 --judge --judge-model gpt-5.6-luna

# 2. property rankings  (gold looks like ['b','d','a','c'])
python run_eval.py --mode llm --split rank --n 10 --judge --judge-model gpt-5.6-luna
python run_eval.py --mode agent --split rank --n 10 --no-judge

# 3. numeric property prediction
python run_eval.py --mode llm --split numeric --n 10
python run_eval.py --mode agent --split numeric --n 5

# 4. mixed hard pool
python run_eval.py --mode llm --split hard --n 15 --judge --judge-model gpt-5.6-luna
python run_eval.py --mode agent --split hard --n 15 --judge --judge-model gpt-5.6-luna