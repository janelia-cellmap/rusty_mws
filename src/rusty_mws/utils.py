import numpy as np
from scipy.ndimage import measurements
from funlib.segment.arrays import replace_values


def filter_fragments(
    affs_data: np.ndarray, fragments_data: np.ndarray, filter_val: float
) -> None:
    """Allows filtering of MWS fragments based on mean value of affinities & fragments. Will filter and update the fragment array in-place.

    Args:
        aff_data (``np.ndarray``):
            An array containing affinity data.

        fragments_data (``np.ndarray``):
            An array containing fragment data.

        filter_val (``float``):
            Threshold to filter if the average value falls below.
    """

    average_affs: float = np.mean(affs_data.data, axis=0)

    filtered_fragments: list = []

    fragment_ids: np.ndarray = np.unique(fragments_data)

    for fragment, mean in zip(
        fragment_ids, measurements.mean(average_affs, fragments_data, fragment_ids)
    ):
        if mean < filter_val:
            filtered_fragments.append(fragment)

    filtered_fragments: np.ndarray = np.array(
        filtered_fragments, dtype=fragments_data.dtype
    )
    replace: np.ndarray = np.zeros_like(filtered_fragments)
    replace_values(fragments_data, filtered_fragments, replace, inplace=True)


# neighborhood offset values
neighborhood: list[list[int]] = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [2, 0, 0],
    [0, 2, 0],
    [0, 0, 2],
    [4, 0, 0],
    [0, 4, 0],
    [0, 0, 4],
    [8, 0, 0],
    [0, 8, 0],
    [0, 0, 8],
    [0, -3, -7],
    [0, -6, -6],
    [0, -7, -3],
    [0, -7, 3],
    [0, -6, 6],
    [0, -3, 7],
    [-3, 0, -7],
    [-6, 0, -6],
    [-7, 0, -3],
    [-7, 0, 3],
    [-6, 0, 6],
    [-3, 0, 7],
    [-3, -7, 0],
    [-6, -6, 0],
    [-7, -3, 0],
    [-7, 3, 0],
    [-6, 6, 0],
    [-3, 7, 0],
]
