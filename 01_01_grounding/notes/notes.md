# Understanding Large Language Models

Large language models like GPT-4 and Claude are trained using a technique called next-token prediction. The model learns to predict the most likely next word given all previous words in a sequence. This simple objective, when scaled to billions of parameters and trillions of tokens, produces emergent capabilities.

## The Transformer Architecture

The transformer was introduced by Google researchers in 2017. Unlike RNNs which process tokens sequentially, transformers use self-attention to process all tokens in parallel. This parallelization enabled training on much larger datasets using GPU clusters.

The key innovation is the attention mechanism, which allows each token to "attend" to every other token in the context window. Modern models like GPT-4 have context windows of 128k tokens, while Claude can handle up to 200k tokens.

## Reinforcement Learning from Human Feedback

After pre-training, models are fine-tuned using RLHF. Human raters compare model outputs and rank them by quality. This feedback trains a reward model, which then guides the language model toward more helpful and harmless responses.

Constitutional AI, developed by Anthropic, is an alternative approach where the model critiques and revises its own outputs based on a set of principles, reducing the need for human feedback.

## Scaling Laws

OpenAI's scaling laws research showed that model performance improves predictably with more compute, data, and parameters. The Chinchilla paper from DeepMind later refined this, showing that many models were undertrained relative to their size.
