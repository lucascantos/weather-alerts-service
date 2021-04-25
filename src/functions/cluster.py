# RAIOS
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
import numpy as np
from shapely.geometry import shape, Polygon, box
from shapely.ops import unary_union
from src.helpers.decorators import timeit
class Cluster(object):
    def __init__(self, data_points):
        '''
        Cluster objects made from a list of coords
        :params data_points: List of coords (lat,lon)
        '''

        if len(data_points) == 0:
            raise ValueError('Empty Array')
        self.data_points = np.array(data_points, dtype=float)

    def dataTrim(self, bbox):
        '''
        Trim data around a rectangle.
        :params bbox: Bounding box around a a polygon. [west, south, east, north]
        '''
        ll = np.array([bbox[1], bbox[0]]) #ll: LowerLeft
        ur = np.array([bbox[3], bbox[2]]) #ur: UpperRight
        inidx = np.all(np.logical_and(ll <= self.data_points, self.data_points <= ur), axis=1)
        self.data_points = self.data_points[inidx]
        
    def make_clusters(self, ignore_points=False, trim_bbox=None):
        '''
        Group points based on DBSCAN making a polygon with ConvexHull. 
        :params ignore_points: The rogue points without grouping are ignored. Default = false
        :params trim_bbox: Bounding box for trimming data. If not given, will use all data. Deafult = None
        '''
        if trim_bbox is not None:
            self.dataTrim(trim_bbox)

        if self.data_points.size==0:
            # print('No points to work with')
            self.clusters = None
            return self.clusters
        
        self.clusters = {
            'type': 'Feature',
            'properties': {},
            'geometry': {
                'type': 'GeometryCollection',
                'geometries': [
                    {
                        'type': 'MultiPolygon',
                        'coordinates': []
                    },
                    {
                        'type': 'MultiPoint',
                        'coordinates': []
                    }
                ]
            }
        }
        # eps = Distance Between points, Minsample = Minimum points to be a cluster. Should be at least 3 for polygon
        db = DBSCAN(eps=0.09, min_samples=7).fit(self.data_points)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_
        unique_labels = set(labels)
        
        for k in unique_labels:
            class_member_mask = (labels == k) #k: Numero do cluster
            if k != -1:
                # ----Aki sao os clusters. Usa um centroid como base e faz o buffer que cobre uma area. Removi Core_sample pq nem sempre da certo
                xy = self.data_points[class_member_mask]
                try:
                    hull = ConvexHull(xy) #Convexhul cria um contorno usando os pontos externos
                except:
                    # print("Skipping weird shape. Propably a line and radar echo")
                    continue
                
                # Add new cluster, make a 3-tier list...polygon stuff, you wouldn't get it.
                cluster_points = self.clusters['geometry']['geometries'][0]['coordinates']
                vertices = xy[hull.vertices].tolist()
                vertices.append(vertices[0])
                mini_cluster = [list(vertices)]
                cluster_points.append(mini_cluster)

            elif not ignore_points:
                # ----Aki sao os pontos isolados. E ha um array de pontos aki. Por isso o do loop interno.
                xy = self.data_points[class_member_mask & ~core_samples_mask]
                self.clusters['geometry']['geometries'][1]['coordinates'] = [coords.tolist() for coords in xy]
        # print(self.clusters)
        return self.clusters

    def hitcheck(self, geometry, buffer=None):
        '''
        Checks if clusters intersect with some other geometry
        :params geometry: Geojson with the target geometry
        :params buffer: Range around geometry. Required for non Polygon geometries.
        '''
        buffer_features = ['Point', 'LineString', 'MultiPoint', 'MultiLineString']      
        polygon = shape(geometry)
        if geometry['type'] in buffer_features:
            if not buffer:
                raise ValueError(f'buffer can not be None with type {geometry["type"]}')
            polygon = polygon.buffer(buffer)

        dist = 999
        hit_status=False
        for cluster in self.clusters['geometry']['geometries']:
            if len(cluster['coordinates']) < 1:
                continue
            mega_cluster = shape(cluster)
            if not mega_cluster.is_valid:
                # merge polygons into a single entity if they touch or overlap
                mega_cluster = unary_union(mega_cluster)
            if dist > polygon.centroid.distance(mega_cluster):
                dist = polygon.centroid.distance(mega_cluster)
                try:
                    hit_status = polygon.intersects(mega_cluster)
                except Exception as e:
                    # print(f"WARNING: {e} {geometry}")
                    for part in cluster['coordinates']:
                        try:
                            hit_status = polygon.intersects(Polygon(part[0]))
                        except:
                            print(f"Error: {part}")
        if hit_status:
            return dist
        # print(self.clusters['geometry']['geometries'][0])
    @staticmethod
    def insersection(focus, target):
        '''
        Checks intersection between the shape and a target
        :params shape: Geojson of the focus shape
        :params target: Geojson of target shape
        '''
        return shape(focus).intersects(shape(target))
    
    @staticmethod
    def make_shape(data, geometry):
        '''
        Makes a geometry object out of data
        :params data: Information of geometry. Should be formated based on geometry type
        :params geometry: Type of Geometry to make out of
        '''
        geometries = {
            'polygon': Polygon,
            'shape': shape,
            'box': box,
        }
        if geometry == 'box':
            return geometries.get(geometry)(*data)
        return geometries.get(geometry)(data)

if __name__ == "__main__":
    pass