# first line: 44
@_memory.cache
def _read_examples(path, expected_count=None):
    examples_strs = _read_example_strs(path)
    if expected_count:
        assert len(examples_strs) == expected_count
    return [np.fromstring(s, sep=' ').reshape(-1, 13) for s in examples_strs]
