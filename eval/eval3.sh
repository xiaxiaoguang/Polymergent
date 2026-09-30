# claude-sonnet-5
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'ranking' --mode llm --split all --noasset
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'ranking' --mode agent --split all --noasset

# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode llm --split all --noasset
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode agent --split all --noasset

# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --keywords dielectric_constant
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --keywords dielectric_constant

# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --keywords electron_affinity
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --keywords electron_affinity

python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --keywords bulk_bandgap
python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --keywords bulk_bandgap

