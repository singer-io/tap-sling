# tap-sling

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Sling](https://getsling.com/) (API documentation [here](https://api.sling.is/#/))
- Extracts the following resources:
  - Shifts
  - No Shows
  - Leaves
  - Leave Types
  - Users
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

`api_key` must be provided in config and `start_date` must be provided either in config or state.

`shifts`, `no_shows`, and `leaves` are pulled from the provided `start_date` through 1 day before run date. *There is no benefit to running this tap more than daily.*

`leave_types` and `users` are fully replicated on every run.

# Quick Start

1.  Get a Sling API key

    Instructions [here](https://api.sling.is/#/)

2.  Install

    Clone this repo

    ```
    git clone ...
    ```

    We recommend using a virtualenv:

    ```
    virtualenv -p python3 venv
    source venv/bin/activate
    pip3 install -e .
    ```

3.  Set up your config file.

    An example config file is provided in `sample_config.json`

4.  Run the tap in discovery mode to get catalog.json file.

    ```
    tap-sling --config config.json --discover > catalog.json
    ```

5.  In the generated `catalog.json` file, select the streams to sync.

    Each stream in the `catalog.json` file has a `schema` entry. To select a stream to sync, add **"selected": true** to that stream's `schema` entry. For example, to sync the `shifts` stream:

    ```
    "tap_stream_id": "shifts",
        "schema": {
            "selected": true,
            "properties": {
                ...
            }
        }
    ...
    ```

6.  Run the application

    tap-sling can be run with:

    ```
    tap-sling --config config.json --catalog catalog.json
    ```

7.  To run with [Stitch Import API](https://www.stitchdata.com/docs/integrations/import-api/) with dry run:

    ```
    tap-sling --config config.json --catalog catalog.json | target-stitch --config target_config.json --dry-run > state.json
    ```

## Developing

While developing the tap, run pylint to improve better code quality which is recommended by [Singer.io best practices](https://github.com/singer-io/getting-started/blob/master/docs/BEST_PRACTICES.md).

```
pylint tap_sling -d missing-docstring -d logging-format-interpolation -d too-many-locals -d too-many-arguments
```

To check the tap and verify working, install [singer-tools](https://github.com/singer-io/singer-tools).

```
tap-sling --config tap_config.json --catalog catalog.json | singer-check-tap
```

---

Copyright &copy; 2020 Stitch
