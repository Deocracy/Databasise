# Recommended prompt: D1 one-shot (spike 008)

Winner on the pre-registered bar and the only winner that keeps the
one-pass property (single decode under the v0.2 grammar). Numbers on
the 16-doc scored set, Qwen3-4B Q8, raw completion, temp 0, seed 1234,
cap 1024 (results.json): routing_exact 0.500 vs D0 0.375 (+0.125),
Proof-pass 0.780 vs 0.360 (+0.420), evidence failures 22 vs 54,
tokens/para 523.9 vs 353.6. On MiniCPM5-2B: routing 0.562 vs 0.500
(+0.062, below the 0.10 bar but +3 on the 13 run-stable docs),
Proof-pass 0.830 vs 0.754.

Construction (prompts.py build_prompt('D1', ...)): 003 INSTRUCTION, then
the block below (teacher ops for held-out example doc shirley_temple),
then the target section. D3 two-step scores higher on qwen4b (route
0.562, proof 0.936) but needs two decodes and breaks the one-pass
design; adopt only if accuracy outweighs the extra pass.

## Prompt template

<INSTRUCTION = spike-003 INSTRUCTION, byte-identical>

Example:
<example block below>

Section:
<section content>

JSON:

## Example block (held-out doc: shirley_temple)

Section:
Shirley Temple

Shirley Temple Black (April 23, 1928 – February 10, 2014) was an American actress, singer, dancer, businesswoman, and diplomat who was Hollywood's number one box-office draw as a child actress from 1935 to 1938. As an adult, she was named United States ambassador to Ghana and to Czechoslovakia and also served as Chief of Protocol of the United States.

JSON:
{"ops": [{"target": "graph", "s": "Shirley Temple Black", "p": "date of birth", "o": "1928-04-23", "quote": "Shirley Temple Black (April 23, 1928"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "nationality", "value": "American", "value_type": "text", "quote": "was an American actress"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "actress", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "singer", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "dancer", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "businesswoman", "value_type": "text", "quote": "singer, dancer, businesswoman, and diplomat"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "diplomat", "value_type": "text", "quote": "businesswoman, and diplomat who was"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "role", "value": "United States ambassador to Ghana", "value_type": "text", "quote": "named United States ambassador to Ghana"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "role", "value": "Chief of Protocol of the United States", "value_type": "text", "quote": "served as Chief of Protocol of the United States"}]}
