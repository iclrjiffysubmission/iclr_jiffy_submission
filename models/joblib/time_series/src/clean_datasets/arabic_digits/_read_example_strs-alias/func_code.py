# first line: 37
@_memory.cache
def _read_example_strs(path):
    with open(path, 'r') as f:
        examples_strs = f.read().split('\n\n')
    return examples_strs
