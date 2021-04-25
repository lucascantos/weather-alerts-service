from src.configs.config import DYNAMO_TABLE
from src.services.s3 import S3
from src.services.dynamodb import DynamoDB
from src.helpers import timestamp as ts
from src.helpers.data import multi_threading
from src.helpers.data import from_dynamodb_to_json
from src.helpers.validator import MyValidator
from src.schemas.input_schema import new_image_schema



def load_data():

    radar_db = DynamoDB(DYNAMO_TABLE)
    radar_data = radar_db.load_data()
    v = MyValidator()

    def _fix_radar_data(single_data):
        fixed = from_dynamodb_to_json(single_data)
        v_body, v_errors = v.validate(fixed, new_image_schema)
        print(fixed)
        if len(v_errors) > 0:
            return
        if v_body['org'] not in ['redemet', 'sigsc']:
            return 
        # :params bbox: Bounding box around a a polygon. return [west, south, east, north]
        try:
            if v_body['org'] == 'sigsc':
                # E,W,N,S
                bbox = [v_body['bounds'][1] , v_body['bounds'][3], v_body['bounds'][0], v_body['bounds'][2]]
            else:
                # N,S,E,W
                bbox = [v_body['bounds'][3], v_body['bounds'][1], v_body['bounds'][2], v_body['bounds'][0]]
        except IndexError:
            print(m.send_debug(json.dumps({v_body['id']: v_body['bounds'], 'data': single_data})))
            return


        if v_body['last_image'] == 'null':
            return    
        image_timestamp = v_body['last_image'].split('_')[1].split('.')[0]
        recent_time = ts.relative_date(minutes=-40)
        if ts.to_datetime(image_timestamp, '%Y-%m-%d--%H:%M:%S') < recent_time:
            return
        # print(v_body['last_image'])

        filepath = f"{v_body['path']}{v_body['last_image']}"
        radar_bucket = S3(v_body['bucket'])
        radar_image = radar_bucket.load(filepath)

        radar_code=v_body['id']        
        return radar_image, bbox
        
    for single_data in radar_data:
        result = _fix_radar_data(single_data)
        if result is not None:
            yield result
    # for i in multi_threading(_fix_radar_data, radar_data):
    #     if i is not None:
    #         yield i