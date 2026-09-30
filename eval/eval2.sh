# deepseek-v4-pro
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 14
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 14
 
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash
# python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer/subdata --answer-type 'multipleChoice' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash

python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --keywords chain_bandgap
python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --keywords chain_bandgap

python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --keywords ionization_energy
python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --keywords ionization_energy

python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 20 --source ParetoGreedyReaction 
python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 20 --source ParetoGreedyReaction 


python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode llm --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --source OpenMaterials_test_high_impact 
python run_eval.py --data /home/hcao5/workspace/datasets/qwqwq/data/polymer --answer-type 'exactMatch' --mode agent --split all --noasset --agent-llm deepseek-v4-pro --baseline-llm deepseek-v4-pro --judge-model deepseek-flash --n 10 --source OpenMaterials_test_high_impact 
