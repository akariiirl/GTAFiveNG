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
    # GTA blends using b, g and their product. Averaging vertex weights is not
    # the same as integrating that bilinear product over a triangle.
    channels = np.asarray(colour, dtype=float)[triangles]
    if channels.ndim != 3 or channels.shape[2] != 4 or not np.isfinite(channels).all():
        raise ValueError('Invalid GTA terrain vertex colours')
    channels = np.clip(channels / 255, 0, 1)
    b, g = channels[:, :, 2], channels[:, :, 1]
    mean_b, mean_g = b.mean(axis=1), g.mean(axis=1)
    mean_bg = ((b*g).sum(axis=1) + b.sum(axis=1)*g.sum(axis=1)) / 12
    weights = np.stack((1-mean_b-mean_g+mean_bg, mean_b-mean_bg,
                        mean_g-mean_bg, mean_bg), axis=1)
    return np.argmax(weights, axis=1)
