# -*- coding: utf-8 -*-

# from models.helpers import image_base64, signed_s3_file

from datetime import datetime
import json
import requests
import base64
import cv2
import numpy as np
from src.functions.cluster import Cluster
class RadarImage(Cluster):
    def __init__(self, image_data=None, format='unicode'):
        '''
        Radar image object spliting different levels of itensity
        :param image_data: loaded image data
        :param format: Image data format. Default = unicode. Can be base64
        '''

        if format == 'unicode':
            dec = np.frombuffer(image_data, dtype=np.uint8)
        elif format == 'base64':
            dec = np.frombuffer(base64.b64decode(image_data), np.uint8)        
        self.image = cv2.imdecode(dec, cv2.IMREAD_COLOR)

    def __add__(self, new_data_points):
        if len(new_data_points) > 0:
            return np.append(self.data_points, new_data_points,axis=0)
        else:
            return self.data_points

    def __sub__(self, new_data_points):
        if len(new_data_points) > 0:
            a1_rows = set(map(tuple, self.data_points))
            a2_rows = set(map(tuple, new_data_points))
            diff_set = list(a1_rows.difference(a2_rows))
            return np.array(diff_set)
        else:
            return self.data_points

    def image_filter (self, bbox, limit=None):
        '''
        Filter image based on color HSV ranges
        :params bbox: Bounding box around a a polygon. [west, south, east, north]
        :params limit: dictionary with the limit ranges of image (rgb, hsv and others )
        '''
        from time import time
        if limit is None:
            limit = dict(tipo="legenda",
                        levels=[{
                            "intensity": "Todas",
                            "range_mmh": [0,200],
                            "range_dbz": [0,75],
                            "range_rgb": [[0, 0, 1], [255, 255, 255]],
                            "range_hsv": [[0, 0, 1], [255, 255, 255]]
                        }
                        ])
        hsv = cv2.cvtColor (self.image, cv2.COLOR_BGR2HSV)
        mask = self._image_mask(limit, hsv)
        self.res = cv2.bitwise_and(self.image, self.image, mask=mask) 
        self.data_points = np.array(list(self._image2data(self.res, bbox)), dtype=float)

    def _image_mask(self, level, hsv):
        '''
        Make mask filter for image
        :params level: Disctionary with filter data
        :params hsv: HSV formated image
        '''

        hsv_range = level['range_hsv']
        h_lower = hsv_range[0]
        h_upper = hsv_range[1]
        h = np.array([h_lower, h_upper])
        mask = cv2.inRange(hsv, h[0], h[1])
        return mask
    
    def _transparency_mask(self, bgr_matrix):
        '''
        Adds transperency channel to BGR image
        :params bgr_matrix: Matrix to convert from a BlueGreenRed image 
        '''
        bgra = cv2.cvtColor (bgr_matrix, cv2.COLOR_BGR2BGRA)
        bgra[:,:,3][(bgra[:,:,0]==0) & (bgra[:,:,1]==0) & (bgra[:,:,2]==0)]=0
        return bgra

    def _encode_image(self, img):
        '''
        Encodes image to base64 format
        :params img: cv2 image
        '''
        retval, buffer = cv2.imencode('.png', img)
        return buffer
    
    def _image2data(self, img, bbox):
        '''
        Convert Image to data matrix
        :params bbox: Bounding box around a a polygon. [west, south, east, north]
        '''
        # From north to south or it'll flip vertical
        lats = np.linspace(bbox[3], bbox[1], img.shape[0])
        lons = np.linspace(bbox[0], bbox[2], img.shape[1])
        color_pixels = np.where(np.any(img>0, axis=2))
        for y, x in zip(color_pixels[0], color_pixels[1]):
            if np.all(img[y][x]==img[y][x][0]):
                continue
            yield lons[x], lats[y]

    def save_image(self, filename='test.jpg', file=None):
        if file is None:
            file = self.res
        cv2.imwrite(filename, file)

    @staticmethod
    def huevalue(x):
        '''
        Simple helper to make a 0~360 HUE value fit on a 0~255
        '''
        y = x / (360/255)
        return y

    @staticmethod
    def RGB2BGR(arrays):
        '''
        Converts RGB image to BGR (OpenCV Standard)
        :params arrays: Arrays of RGB image
        '''
        for array in arrays:
            array[0], array[2] = array[2], array[0]
        nparray = np.uint8([arrays])
        arrayHSV = cv2.cvtColor(nparray, cv2.COLOR_BGR2HSV)[0]
        return arrayHSV


if __name__ == "__main__":
    pass

'''
https://stackoverflow.com/questions/26240681/how-can-i-retrieve-a-javascript-variable-using-python
<div id='div_radar'><script>carrega_radar(400, 'sr', 'url',...)
'''