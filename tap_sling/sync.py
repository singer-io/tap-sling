import requests
import singer


LOGGER = singer.get_logger()


def sync(config, state, catalog):
    '''
    Run sync mode
    '''
    # Loop over streams in catalog
    for stream in catalog.get_selected_streams(state):
        stream_id = stream.tap_stream_id
        LOGGER.info("Syncing stream:" + stream_id)

        singer.write_schema(
            stream_name=stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties
        )

        sync_func = SYNC_FUNCTIONS[stream_id]
        ret_state = sync_func(
            config,
            state
        )

        if ret_state:
            state = ret_state
    return


class SlingClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def make_request(self, endpoint, querystring='', method='GET', state=None, **request_kwargs):
        headers = {
            'Authorization': self.api_key
        }
        url = 'https://api.sling.is/v1/%s%s' % (endpoint, querystring)
        LOGGER.info('URL=%s', endpoint)
        resp = requests.request(method, url, headers=headers, **request_kwargs)
        
        if resp.status_code == 200:
            return resp.json()

        return resp


def sync_leave_types(config, state):
    return


def sync_leaves(config, state):
    return


def sync_no_shows(config, state):
    return


def sync_shifts(config, state):
    return


def sync_users(config, state):
    stream_id = 'users'
    api_key = config['api_key']
    sc = SlingClient(api_key)
    
    raw_users = sc.make_request('users', state=state)
    if not raw_users:
        raise Exception("Resource not found")
    
    user_records = []
    for user in raw_users:
        record = {
            'id': str(user.get('id')) if user.get('id') else None,
            'type': user.get('type'),
            'name': user.get('name'),
            'last_name': user.get('lastname'),
            'avatar': user.get('avatar'),
            'email': user.get('email'),
            'timezone': user.get('timezone'),
            'hours_cap': user.get('hoursCap'),
            'active': user.get('active'),
            'deactivated_at': user.get('deactivatedAt'),
        }
        user_records.append(record)

    singer.write_records(stream_id, user_records)

    return state


SYNC_FUNCTIONS = {
    'leave_types': sync_leave_types,
    'leaves': sync_leaves,
    'no_shows': sync_no_shows,
    'shifts': sync_shifts,
    'users': sync_users
}