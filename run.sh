python3 convert/pareto_reaction.py \
  --raw-dir ./raw/pareto_greedy_reaction \
  --out ./polymer/tasks2.json

python3 convert_datasets.py --holdout-frac 0.01 --property-tasks-per-item 5



    # parser.add_argument("--length",type=int,default=100)
    # args = parser.parse_args()
    
    # tasks = convert_pareto_greedy_reaction(args.raw_dir)
    # import random
    # random.seed(42)
    # random.shuffle(tasks)
    # tasks = tasks[:args.length]

