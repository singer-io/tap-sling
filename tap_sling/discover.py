import json
import os
import singer
from singer import metadata
from singer.catalog import Catalog, CatalogEntry
from singer.schema import Schema


LOGGER = singer.get_logger()
STREAMS = {
    'leave_types': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE'
    },
    'leaves': {
        'key_properties': [],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['date']
    },
    'no_shows': {
        'key_properties': [],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['date']
    },
    'shifts': {
        'key_properties': ['id'],
        'replication_method': 'INCREMENTAL',
        'replication_keys': ['start_datetime']
    },
    'users': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE'
    }
}


def discover():
    """
    Run discovery mode
    """
    schemas, schemas_metadata = get_schemas()
    streams = []
    for stream_id, schema in schemas.items():
        schema_meta = schemas_metadata[stream_id]

        streams.append(
            CatalogEntry(
                tap_stream_id=stream_id,
                stream=stream_id,
                schema=schema,
                key_properties=STREAMS[stream_id]['key_properties'],
                metadata=schema_meta,
                replication_key=None,
                is_view=None,
                database=None,
                table=None,
                row_count=None,
                stream_alias=None,
                replication_method=None,
            )
        )

    return Catalog(streams)


def get_schemas():
    schemas = {}
    schemas_metadata = {}

    for stream_name, stream_metadata in STREAMS.items():
        schema = None
        schema_path = get_abs_path('schemas/{}.json'.format(stream_name))
        with open(schema_path) as file:
            schema = json.load(file)
        meta = metadata.get_standard_metadata(
            schema=schema,
            key_properties=stream_metadata.get('key_properties', None),
            valid_replication_keys=stream_metadata.get('replication_keys', None),
            replication_method=stream_metadata.get('replication_method', None)
        )
        schemas[stream_name] = Schema.from_dict(schema)
        schemas_metadata[stream_name] = meta

    return schemas, schemas_metadata


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)
    