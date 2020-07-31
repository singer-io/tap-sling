#!/usr/bin/env python3
import singer
from singer import utils
from tap_sling.discover import discover
from tap_sling.sync import sync


LOGGER = singer.get_logger()
REQUIRED_CONFIG_KEYS = ["api_key"]


@utils.handle_top_exception(LOGGER)
def main():
    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover()
        catalog.dump()
    # Otherwise run in sync mode
    else:
        if args.catalog:
            catalog = args.catalog
        else:
            catalog = discover()

        state = args.state or {
            'bookmarks': {}
        }

        sync(args.config, state, catalog)


if __name__ == "__main__":
    main()
