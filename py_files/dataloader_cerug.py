# -*- coding: utf-8 -*-
"""dataloader_CERUG.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tdb9A1vGCVk2MVTQcapJqZXaroSNio_q
"""

import os
import pickle
import numpy as np
from PIL import Image
import torch.utils.data as data
import torch
from torchvision.transforms import Compose, ToTensor
import random

class DatasetFromFolder(data.Dataset):
    def __init__(self, dataset, foldername, labelfolder, imgtype='png', scale_size=(64, 128), is_training=True):
        super(DatasetFromFolder, self).__init__()

        self.is_training = is_training
        self.imgtype = imgtype
        self.scale_size = scale_size
        self.folder = foldername
        self.dataset = dataset

        # Flag to check if dataset is CERUG-EN
        self.cerug = self.dataset == 'CERUG-EN'

        # Load the writer index table or create a new one if it doesn't exist
        self.labelidx_name = labelfolder + dataset + 'writer_index_table.pickle'
        self.imglist = self._get_image_list(self.folder)  # List of image files in the folder
        self.idlist = self._get_all_identity()  # Get all unique writer identities
        self.idx_tab = self._convert_identity2index(self.labelidx_name)  # Map identities to indices
        self.num_writer = len(self.idx_tab)

        print('-' * 10)
        print(f'Loading dataset {dataset} with images: {len(self.imglist)}')
        print(f'Number of writers: {len(self.idx_tab)}')
        print('-*' * 10)

    # Convert identities to indices and save them to a pickle file
    def _convert_identity2index(self, savename):
        if os.path.exists(savename):
            with open(savename, 'rb') as fp:
                identity_idx = pickle.load(fp)
        else:
            identity_idx = {ids: idx for idx, ids in enumerate(self.idlist)}
            with open(savename, 'wb') as fp:
                pickle.dump(identity_idx, fp)
        return identity_idx

    # Extract all unique writer identities from the image list
    def _get_all_identity(self):
        writer_list = [self._get_identity(img) for img in self.imglist]
        return list(set(writer_list))

    # Extract the writer identity from the image filename
    def _get_identity(self, fname):
        if self.cerug:
            return fname.split('_')[0]
        else:
            return fname.split('-')[0]

    # Get the list of image files from the folder
    def _get_image_list(self, folder):
        flist = os.listdir(folder)
        return [img for img in flist if img.endswith(self.imgtype)]

    # Transform the image into a tensor
    def transform(self):
        return Compose([ToTensor(),])

    # Resize the image while maintaining its aspect ratio
    def resize(self, image):
        w, h = image.size[:2]
        ratio_h = float(self.scale_size[0]) / float(h)
        ratio_w = float(self.scale_size[1]) / float(w)
        ratio = ratio_h if ratio_h < ratio_w else ratio_w
        nh = int(ratio * h)
        nw = int(ratio * w)

        imre = image.resize((nw, nh))

        # Invert colors and check for any issues with the image
        im_array = 255 - np.array(imre)
        imre = Image.fromarray(im_array)

        if imre is None:
            raise ValueError("The 'imre' variable is not defined.")
        if not isinstance(imre, Image.Image):
            raise TypeError("The 'imre' variable is not an image.")
        try:
            imre.verify()
        except Exception as e:
            raise ValueError("The image data in 'imre' is corrupted.") from e

        # Create a blank image and place the resized image in the center
        cw, ch = imre.size
        new_img = np.zeros(self.scale_size)
        if self.is_training:
            dy = random.randint(0, int(self.scale_size[0] - ch))
            dx = random.randint(0, int(self.scale_size[1] - cw))
        else:
            dy = int((self.scale_size[0] - ch) / 2.0)
            dx = int((self.scale_size[1] - cw) / 2.0)

        imre = imre.convert('F')
        new_img[dy:dy + ch, dx:dx + cw] = imre

        return new_img, (ratio_h < ratio_w)

    # Load an image and its corresponding writer index
    def __getitem__(self, index):
        imgfile = self.imglist[index]
        writer = self.idx_tab[self._get_identity(imgfile)]

        # Open, resize, and normalize the image
        image = Image.open(self.folder + imgfile).convert('L')
        image, hfirst = self.resize(image)
        image = image / 255.0

        # Transform the image into a tensor
        image = self.transform()(image)
        writer = torch.from_numpy(np.array(writer))

        return image, writer, imgfile

    def __len__(self):
        return len(self.imglist)