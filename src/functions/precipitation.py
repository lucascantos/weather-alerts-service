
import json
from src.configs.radars.info import info
from src.functions.radar import RadarImage
from src.helpers.data import multi_threading
from src.helpers.decorators import timeit
def get_alert(distance, thresholds, lower):
    if lower:
        check = lambda x, y: True if x <= y else False
    else:
        check = lambda x, y: True if x >= y else False

    for index, level in enumerate(sorted(thresholds, reverse=not lower)):
        if check(distance, level):
            break   
    return len(thresholds) - index

def make_clusters(radar_image, radar_code=None, bbox=None, source='redemet', filter_level=2):
    radar_info = info(source)
    if type(radar_image) is list:
        if not(len(radar_image) == len(bbox)):
            print('Images and bbox must have same length')
            return
        level_filter = list(filter(lambda i: i[0] > filter_level, enumerate(radar_info['properties']['levels'])))
        
        def _filter_levels(single_level, bbox, info):
            single_level.image_filter(bbox, info)
            return single_level.data_points

        args = []
        for single_image, single_bb in zip(radar_image, bbox):
            new_args = [{'single_level': RadarImage(single_image),'bbox':single_bb,'info':i[1]} for i in level_filter]
            args.extend(new_args)
        
        radar = RadarImage(single_image)
        flag = False
        for arg in args:
            i = _filter_levels(**arg)
            if len(i) > 0:
                if flag:
                    radar.data_points = radar + i
                else:
                    radar.data_points = i  
                    flag = True              
    else:    
        if bbox is None:
            if radar_code not in radar_info['bounds']:
                print(f"A NEW RADAR HAS BEEN FOUND: {radar_code}")
                print(f"Please, find the coords of it and update the file")
                return
            bbox = radar_info['bounds'][radar_code]
            bbox = [bbox[3],bbox[1],bbox[2],bbox[0]] 

        radar = RadarImage(radar_image)
        radar.image_filter(bbox, radar_info['properties']['levels'][0])
        single_radar = RadarImage(radar_image)  

        def _filter_levels(level_data):
            level_index, level = level_data
            if level_index > 2 or level_index == 0:
                return
            else:
                single_radar.image_filter(bbox, level)
                single_radar.save_image()
                radar.data_points = radar - single_radar.data_points
        multi_threading(_filter_levels, enumerate(radar_info['properties']['levels']))

    radar.make_clusters(True)
    if radar.clusters is None:
        return
    return radar

def update_alerts (locations, radar_image, radar_code=None, bbox=None, source='redemet'):
    '''
    update the status on the lightning alerts
    :params locations: dict with locations in geojson 
    :params radar_image: loaded data with list of imagens in Unicode
    :params radar_code: Code of radar. eg: 'sr' for redemet's SãoPaulo radar
    :params bbox: list of bounding boxes of images
    :params source: source of radar. Default = redemet
    '''
    from src.functions import radar
    VARIABLE = 'precipitation'
    
    radar_cluster = make_clusters(radar_image, radar_code, bbox, source)
    '''
    Filter locations based on bboxes
    '''
    bbox_polygons = [radar.RadarImage.make_shape(bb,'box') for bb in bbox]
    def _filter_locations(location):
        _, location = location
        geometry = location['geojsonFeature'].get('geometry')
        if not location['active']:
            return False
        if geometry is None:
            return False
        location_polygon = radar.RadarImage.make_shape(location['geojsonFeature']['geometry'], 'shape')
        in_area = any([bb.contains(location_polygon) for bb in bbox_polygons])
        return in_area
        
    filtered_locations = filter(_filter_locations, locations['locations'].items())
    for location_id, location in filtered_locations:
        if VARIABLE.lower() in location['variables'] and location['active']:
            alert = {
                    VARIABLE: {
                        "alerts": 0,
                        "values": -1
                    }
                }
            thresholds = location['variables'][VARIABLE]['distance']
            lower = True
            distance = radar_cluster.hitcheck(location['geojsonFeature']['geometry'])
            if distance is not None:
                alert[VARIABLE]['alerts'] = get_alert(distance*111, thresholds, lower)
                alert[VARIABLE]['values'] = round(distance * 111,2)
            if isinstance(alert[VARIABLE]['alerts'], list):
                print(distance, thresholds, lower)
            yield location_id,  {"variables": alert}
