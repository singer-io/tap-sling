# tap-sling

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Sling](https://getsling.com/)
- Extracts the following resources:
  - [Daily Labor Report](https://support.getsling.com/en/articles/1098941-what-are-reports)
  - [Daily Payroll Report](https://support.getsling.com/en/articles/1098941-what-are-reports)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

---

Copyright &copy; 2018 Stitch
