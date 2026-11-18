"""Conservative material selection for original GTA layered ground meshes.

CodeWalker's TerrainPS blends four colour maps with Colour1 blue and green.
BeamNG's ordinary Material cannot reproduce that vertex blend; select the
dominant source layer per triangle while retaining original geometry and UVs.
"""
import numpy as np


def is_layered_terrain(shader):
    return shader.startswith('terrain_cb') and '4lyr' in shader


def layer_weights(colour):
    c = np.asarray(colour, dtype=float)
    if c.ndim != 2 or c.shape[1] != 4 or not np.isfinite(c).all():
        raise ValueError('Invalid GTA terrain vertex colours')
    b, g = np.clip(c[:, 2] / 255, 0, 1), np.clip(c[:, 1] / 255, 0, 1)
    return np.stack(((1-b)*(1-g), b*(1-g), (1-b)*g, b*g), axis=1)


def triangle_layers(colour, indices):
    triangles = np.asarray(indices, dtype=int).reshape(-1, 3)
    return np.argmax(layer_weights(colour)[triangles].mean(axis=1), axis=1)
