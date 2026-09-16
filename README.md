# Polymer

Agent architecture

                    User Query
                         │
              ┌──────────┴──────────┐
              ↓                     ↓
       Tool/Resource           Know-How Retrieval
         Retrieval                    │
              │                       │
              ↓                       ↓
       tools / data /             procedures /
       software                   best practices
              │                       │
              └──────────┬────────────┘
                         ↓
                    A1 / Core LLM
                         ↓
                    Plan / Reason
                         ↓
                  Generate Code
                         ↓
                   Execute Code
                         ↓
                    Observation
                         │
                         └──────→ A1

# How to transplant that to Polymer Agent

                         Polymer literature
                                │
                                ▼
                       Task Extraction LLM
                                │
                                ▼
                         Task Clustering
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
          Tool Generator   Resource Finder   Know-How Miner
                │               │                │
                ▼               ▼                ▼
          Python tools      candidate URLs    paper evidence
                │               │                │
                ▼               ▼                ▼
          Tool Validator    Resource Validator  Synthesis
                │               │                │
                ▼               ▼                ▼
          tool pool          data lake         know-how
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                         Polymer Polymer


# What about automatical tool generation

                    AUTOMATE
                        │
Literature ──→ tasks ──→ tools ──→ descriptions
                        │
                        └──→ candidate resources
                                      │
                                      ▼
                               HUMAN REVIEW
                                      │
                              approved resources
                                      │
                                      ▼
                                  data lake

# Generate code 

AI scientist

                        research idea
                        ↓
                        generate hypothesis
                        ↓
                        write code
                        ↓
                        run experiment
                        ↓
                        analyze results
                        ↓
                        revise
                        ↓
                        write paper
                        ↓
                        automated review

MLE-bench: resource + execution + grading

                        task
                        ↓
                        dataset
                        ↓
                        agent writes code
                        ↓
                        run code
                        ↓
                        generate submission
                        ↓
                        grader
                        ↓
                        score

# For “paper → working code”: Paper2Code

Paper2Code

                        paper
                        ↓
                        planning
                        ↓
                        architecture/dependency analysis
                        ↓
                        code generation
                        ↓
                        repository

ScienceAgentBench

                    scientific task
                        ↓
                    LLM agent
                        ↓
                    Python program
                        ↓
                    execute
                        ↓
                    evaluate result

Agent Laboratory

                    literature review
                        ↓
                    extract procedures
                        ↓
                    experimentation
                        ↓
                    discover what actually works
                        ↓
                    summarize into know-how

