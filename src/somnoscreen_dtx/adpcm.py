"""IMA/DVI ADPCM as used in DTX files: 4-bit sign-magnitude codes, standard step tables."""
import numpy as np

STEP = np.array([
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230,
    253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
    3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487,
    12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
], dtype=np.int64)

INDEX_ADJUST = np.array([-1, -1, -1, -1, 2, 4, 6, 8] * 2, dtype=np.int64)

INT16 = (-32768, 32767)
UINT8 = (0, 255)


def step(pred, index, code, limits=INT16):
    """Apply one code. Works on scalars and on numpy arrays (one state per element)."""
    size = STEP[index]
    diff = (size >> 3) + np.where(code & 4, size, 0) + np.where(code & 2, size >> 1, 0) \
        + np.where(code & 1, size >> 2, 0)
    pred = np.clip(np.where(code & 8, pred - diff, pred + diff), *limits)
    index = np.clip(index + INDEX_ADJUST[code], 0, 88)
    return pred, index


def encode_sample(sample, pred, index, limits=INT16):
    """Encode one sample against a scalar state; returns (code, new pred, new index)."""
    diff = int(sample) - int(pred)
    code = 8 if diff < 0 else 0
    diff = abs(diff)
    size = int(STEP[index])
    for bit in (4, 2, 1):
        if diff >= size:
            code |= bit
            diff -= size
        size >>= 1
    new_pred, new_index = step(np.int64(pred), np.int64(index), np.int64(code), limits)
    return code, int(new_pred), int(new_index)
