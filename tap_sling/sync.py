import datetime
import time
import requests
import singer

DATETIME_PARSE = "%Y-%m-%dT%H:%M:%SZ"
DATETIME_FMT = "%04Y-%m-%dT%H:%M:%S.%fZ"
DATETIME_FMT_MAC = "%Y-%m-%dT%H:%M:%S.%fZ"
SLING_DATE_FMT = '%Y-%m-%d'
LOGGER = singer.get_logger()


def sync(config, state, catalog):
    '''
    Run sync mode
    '''
    # Loop over streams in catalog
    for stream in catalog.get_selected_streams(state):
        stream_id = stream.tap_stream_id
        LOGGER.info("Syncing stream: %s", stream_id)

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

    def make_request(self, endpoint, querystring='', method='GET', **request_kwargs):
        headers = {
            'Authorization': self.api_key
        }
        url = 'https://api.sling.is/v1/%s%s' % (endpoint, querystring)
        LOGGER.info('URL=%s', url)
        resp = requests.request(method, url, headers=headers, **request_kwargs)

        if not resp.status_code == 200:
            raise Exception(
                "Request returned status code %d\nResponse text: %s"
                % (resp.status_code, resp.text)
            )

        return resp.json()


def safe_cast(value, to_type):
    if value:
        return to_type(value)
    return value


def strptime(dtime):
    try:
        return datetime.datetime.strptime(dtime, DATETIME_FMT)
    except Exception:
        try:
            return datetime.datetime.strptime(dtime, DATETIME_FMT_MAC)
        except Exception:
            return datetime.datetime.strptime(dtime, DATETIME_PARSE)


def sync_leave_types(config, state):
    stream_id = 'leave_types'
    api_key = config['api_key']
    sc = SlingClient(api_key)

    raw_leave_types = sc.make_request('leave/types')

    leave_type_records = []
    for leave_type in raw_leave_types:
        record = {
            'id': safe_cast(leave_type.get('id'), str),
            'type': leave_type.get('type'),
            'name': leave_type.get('name'),
            'paid': leave_type.get('paid'),
            'enabled': leave_type.get('enabled'),
            'cap': leave_type.get('cap'),
            'available': leave_type.get('available'),
        }
        leave_type_records.append(record)

    singer.write_records(stream_id, leave_type_records)

    return state


def sync_leaves(config, state):
    stream_id = 'leaves'
    api_key = config['api_key']
    sc = SlingClient(api_key)

    start_date = strptime(
        state['bookmarks'].get(stream_id, {}).get('start_date', config['start_date'])
    ).date()
    end_date = (  # yesterday
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).date()
    if start_date > end_date:
        LOGGER.info('Start date %s after yesterday; will try again later.', start_date)
        return state  # only run once per day

    query_start_date = start_date + datetime.timedelta(days=0)
    while query_start_date <= end_date:
        query_end_date = min(
            # must do single-day increment b/c endpoint doesn't return date
            query_start_date + datetime.timedelta(days=0),
            end_date
        )
        params = {
            'dates' : '%s/%s' % (query_start_date.strftime(SLING_DATE_FMT),
                                 query_end_date.strftime(SLING_DATE_FMT))
        }
        raw_leaves = sc.make_request('reports/leave', params=params)
        LOGGER.info('query_start_date: %s, query_end_date: %s', query_start_date, query_end_date)

        leave_records = []
        for user_id, user_leave in raw_leaves.items():
            for leave_type_id, leave_detail in user_leave.items():
                record = {
                    "date": query_start_date.strftime(DATETIME_PARSE),
                    "user_id": safe_cast(user_id, str),
                    "leave_type_id": safe_cast(leave_type_id, str),
                    "approved": leave_detail.get("approved"),
                    "approved_minutes": leave_detail.get("approvedMinutes"),
                    "pending": leave_detail.get("pending"),
                    "pending_minutes": leave_detail.get("pendingMinutes"),
                    "unpaid": leave_detail.get("unpaid"),
                    "unpaid_minutes": leave_detail.get("unpaidMinutes"),
                }
                leave_records.append(record)

        singer.write_records(stream_id, leave_records)

        query_start_date = query_end_date + datetime.timedelta(days=1)
        time.sleep(1)  # avoid 70 rpm rate limit

    state['bookmarks'][stream_id] = (
        {}
        if not state['bookmarks'].get(stream_id)
        else state['bookmarks'][stream_id]
    )
    state['bookmarks'][stream_id]['start_date'] = (
        end_date + datetime.timedelta(days=1)  # today
    ).strftime(DATETIME_PARSE)
    singer.write_state(state)

    return state


def sync_no_shows(config, state):
    stream_id = 'no_shows'
    api_key = config['api_key']
    sc = SlingClient(api_key)

    start_date = strptime(
        state['bookmarks'].get(stream_id, {}).get('start_date', config['start_date'])
    ).date()
    end_date = (  # yesterday
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).date()
    if start_date > end_date:
        LOGGER.info('Start date %s after yesterday; will try again later.', start_date)
        return state  # only run once per day

    query_start_date = start_date + datetime.timedelta(days=0)
    while query_start_date <= end_date:
        query_end_date = min(
            # must do single-day increment b/c endpoint doesn't return date
            query_start_date + datetime.timedelta(days=0),
            end_date
        )
        params = {
            'dates' : '%s/%s' % (query_start_date.strftime(SLING_DATE_FMT),
                                 query_end_date.strftime(SLING_DATE_FMT))
        }
        raw_no_shows = sc.make_request('reports/noshows', params=params)
        LOGGER.info('query_start_date: %s, query_end_date: %s', query_start_date, query_end_date)

        no_show_records = []
        for idx, details in raw_no_shows.items():
            idx_split = idx.split('/')

            record = {
                "date": query_start_date.strftime(DATETIME_PARSE),
                "user_id": idx_split[0],
                "location_id": idx_split[1],
                "position_id": idx_split[2],
                "actual": safe_cast(details.get("actual"), int),
                "actual_minutes": safe_cast(details.get("actualMinutes"), int),
                "no_show": safe_cast(details.get("noShow"), int),
                "scheduled": safe_cast(details.get("scheduled"), int),
                "scheduled_minutes": safe_cast(details.get("scheduledMinutes"), int),
            }
            no_show_records.append(record)

        singer.write_records(stream_id, no_show_records)

        query_start_date = query_end_date + datetime.timedelta(days=1)
        time.sleep(1)  # avoid 70 rpm rate limit

    state['bookmarks'][stream_id] = (
        {}
        if not state['bookmarks'].get(stream_id)
        else state['bookmarks'][stream_id]
    )
    state['bookmarks'][stream_id]['start_date'] = (
        end_date + datetime.timedelta(days=1)  # today
    ).strftime(DATETIME_PARSE)
    singer.write_state(state)

    return state


def sync_shifts(config, state):
    stream_id = 'shifts'
    api_key = config['api_key']
    sc = SlingClient(api_key)

    start_date = strptime(
        state['bookmarks'].get(stream_id, {}).get('start_date', config['start_date'])
    ).date()
    end_date = (  # yesterday
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).date()
    if start_date > end_date:
        LOGGER.info('Start date %s after yesterday; will try again later.', start_date)
        return state  # only run once per day

    # /labor/cost only allows 124 days per query, do 30 at a time to be safe
    query_start_date = start_date + datetime.timedelta(days=0)
    while query_start_date <= end_date:
        query_end_date = min(
            query_start_date + datetime.timedelta(days=30),
            end_date
        )
        params = {
            'dates' : '%s/%s' % (query_start_date.strftime(SLING_DATE_FMT),
                                 query_end_date.strftime(SLING_DATE_FMT))
        }
        raw_timesheets = sc.make_request('reports/timesheets', params=params)
        raw_labor_costs = sc.make_request('labor/cost', params=params)
        LOGGER.info('query_start_date: %s, query_end_date: %s', query_start_date, query_end_date)

        shift_costs = {
            shift_id: costs
            for shift_id, costs
            in raw_labor_costs.get('costs', {}).items()
        }

        shift_records = []
        for timesheet in raw_timesheets:
            shift_id = timesheet.get("id")
            record = {
                "id": shift_id,
                "summary": timesheet.get("summary"),
                "status": timesheet.get("status"),
                "type": timesheet.get("type"),
                "full_day": timesheet.get("fullDay"),
                "open_end": timesheet.get("openEnd"),
                "start_datetime": timesheet.get("dtstart"),
                "end_datetime": timesheet.get("dtend"),
                "approved": timesheet.get("approved"),
                "assignee_notes": timesheet.get("assigneeNotes"),
                "user_id": safe_cast(timesheet.get("user", {}).get("id"), str),
                "location_id": safe_cast(timesheet.get("location", {}).get("id"), str),
                "position_id": safe_cast(timesheet.get("position", {}).get("id"), str),
                "break_duration": timesheet.get("breakDuration"),
                "available": timesheet.get("available"),
                "slots": timesheet.get("slots"),
                "tags": [{"id": safe_cast(t.get("id"), str)} for t in timesheet.get("tags")],
                "event_day": shift_costs.get(shift_id, {}).get("eventDay"),
                "paid_minutes": shift_costs.get(shift_id, {}).get("paidMinutes"),
                "regular_minutes": shift_costs.get(shift_id, {}).get("regularMinutes"),
                "regular_cost": shift_costs.get(shift_id, {}).get("regularCost"),
                "overtime_minutes": shift_costs.get(shift_id, {}).get("overtimeMinutes"),
                "overtime_cost": shift_costs.get(shift_id, {}).get("overtimeCost"),
                "holiday_regular_minutes": shift_costs.get(shift_id, {}).get("holidayRegularMinutes"),
                "holiday_regular_cost": shift_costs.get(shift_id, {}).get("holidayRegularCost"),
                "holiday_overtime_minutes": shift_costs.get(shift_id, {}).get("holidayOvertimeMinutes"),
                "holiday_overtime_cost": shift_costs.get(shift_id, {}).get("holidayOvertimeCost"),
                "spread_of_hours_cost": shift_costs.get(shift_id, {}).get("spreadOfHoursCost"),
            }
            shift_records.append(record)

        singer.write_records(stream_id, shift_records)

        query_start_date = query_end_date + datetime.timedelta(days=1)
        time.sleep(1)  # avoid 70 rpm rate limit

    state['bookmarks'][stream_id] = (
        {}
        if not state['bookmarks'].get(stream_id)
        else state['bookmarks'][stream_id]
    )
    state['bookmarks'][stream_id]['start_date'] = (
        end_date + datetime.timedelta(days=1)  # today
    ).strftime(DATETIME_PARSE)
    singer.write_state(state)

    return state


def sync_users(config, state):
    stream_id = 'users'
    api_key = config['api_key']
    sc = SlingClient(api_key)

    raw_users = sc.make_request('users')

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
