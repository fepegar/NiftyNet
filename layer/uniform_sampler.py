# -*- coding: utf-8 -*-
import numpy as np

from .base_sampler import BaseSampler
import utilities.misc_io as io


def rand_spatial_coordinates(spatial_rank, img_size, win_size, n_samples):
    assert np.all([d >= win_size for d in img_size[:spatial_rank]])

    # consisting of starting and ending coordinates
    all_coords = np.zeros((n_samples, spatial_rank * 2), dtype=np.int)
    for i in range(0, spatial_rank):
        all_coords[:, i] = np.random.random_integers(
            0, max(img_size[i] - win_size, 1), n_samples)
        all_coords[:, i + spatial_rank] = all_coords[:, i] + win_size
    return all_coords


class UniformSampler(BaseSampler):
    """
    This class generators samples by uniformly sampling each input volume
    currently 4D input is supported, Hight x Width x Depth x Modality
    """

    def __init__(self,
                 patch,
                 volume_loader,
                 patch_per_volume=1,
                 name="uniform_sampler"):

        super(UniformSampler, self).__init__(patch=patch, name=name)
        self.volume_loader = volume_loader
        self.patch_per_volume = patch_per_volume

    def layer_op(self, batch_size=1):
        """
         problems:
            check how many modalities available
            check the colon operator
            automatically handle mutlimodal by matching dims?
        """
        # batch_size is needed here so that it generates total number of
        # N samples where (N % batch_size) == 0

        spatial_rank = self.patch.spatial_rank
        while self.volume_loader.has_next:
            img, seg, weight_map, idx = self.volume_loader()

            # to make sure all volumetric data have the same spatial dims
            assert io.check_spatial_dims(spatial_rank, img, seg)
            assert io.check_spatial_dims(spatial_rank, img, weight_map)
            # match volumetric data shapes to the patch definition
            img = io.match_volume_shape_to_patch_definition(
                    img, self.patch.full_image_shape)
            seg = io.match_volume_shape_to_patch_definition(
                    seg, self.patch.full_label_shape)
            weight_map = io.match_volume_shape_to_patch_definition(
                    weight_map, self.patch.full_weight_map_shape)
            if not (img.ndim == 4):
                # TODO: support other types of image data
                raise NotImplementedError

            # generates random spatial coordinates
            location = rand_spatial_coordinates(spatial_rank,
                                                img.shape,
                                                self.patch.image_size,
                                                self.patch_per_volume)

            for t in range(0, self.patch_per_volume):
                x_, y_, z_, _x, _y, _z = location[t]

                self.patch.image = img[x_:_x, y_:_y, z_:_z, :]
                self.patch.info = np.array([idx, x_, y_, z_, _x, _y, _z],
                                           dtype=np.int64)
                if self.patch.has_labels:
                    border = self.patch.image_size - \
                             self.patch.label_size
                    assert border >= 0 # assumes label_size <= image_size
                    x_b, y_b, z_b = (x_+border), (y_+border), (z_+border)
                    self.patch.label = seg[
                            x_b : (self.patch.label_size + x_b),
                            y_b : (self.patch.label_size + y_b),
                            z_b : (self.patch.label_size + z_b), :]

                if self.patch.has_weight_maps:
                    border = self.patch.image_size - \
                             self.patch.weight_map_size
                    assert border >= 0
                    x_b, y_b, z_b = (x_+border), (y_+border), (z_+border)
                    self.patch.weight_map = weight_map[
                            x_b : (self.patch.weight_map_size + x_b),
                            y_b : (self.patch.weight_map_size + y_b),
                            z_b : (self.patch.weight_map_size + z_b), :]
                yield self.patch
