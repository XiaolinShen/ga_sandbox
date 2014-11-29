import numpy as np
import random as rnd
from projects.denoising.imaging.image import Image


def salt_and_pepper(image, probability):
    new_image = Image(image.copy())
    for idx_channel, channel in enumerate(new_image.channels):
        for idx_row, row in enumerate(channel):
            for idx_col, col in enumerate(row):
                if rnd.random() < probability:
                    # Make the noise here
                    # either white or black pixel
                    bit = rnd.randint(0, 1)
                    new_image[idx_row, idx_col, idx_channel] = 255 * bit
    return new_image


def gaussian(image, mu=0.0, sigma=10.0):
    new_image = Image(image.copy())
    for idx_channel, channel in enumerate(new_image.channels):
        for idx_row, row in enumerate(channel):
            for idx_col, point in enumerate(row):
                new_point = point + rnd.gauss(mu, sigma)
                # Pixel value should be in [0; 255] interval
                if new_point > 255:
                    new_point = 255
                elif point < 0:
                    new_point = 0
                new_image[idx_row, idx_col, idx_channel] = new_point

    return new_image
