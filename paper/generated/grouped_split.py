def grouped_split(comp: np.ndarray, seed: int = GROUPED_SEED) -> np.ndarray:
    n = len(comp)
    sizes = np.bincount(comp)
    split = np.full(n, "", dtype=object)
    giant = np.flatnonzero(sizes > GIANT_FRACTION * n)
    order = np.random.default_rng(seed).permutation(np.setdiff1d(np.arange(len(sizes)), giant))
    target = 0.15 * n
    filled = {"test": 0, "validation": 0}
    assign = {}
    for c in order:
        if filled["test"] < target:
            assign[c] = "test"; filled["test"] += sizes[c]
        elif filled["validation"] < target:
            assign[c] = "validation"; filled["validation"] += sizes[c]
        else:
            assign[c] = "train"
    for c in giant:
        assign[c] = "train"
    return np.array([assign[c] for c in comp], dtype=object)
