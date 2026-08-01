"""Remediation guidance for XXE and insecure deserialization."""

GUIDANCE = (
    "Never deserialize untrusted data with `pickle.load`/`pickle.loads`, "
    "`marshal`, or `yaml.load` without an explicit safe loader -- use "
    "`yaml.safe_load` (or `yaml.load(stream, Loader=yaml.SafeLoader)`), "
    "`json`, or a schema-validated parser instead. For XML parsing, use a "
    "parser that disables external entity resolution by default (e.g. "
    "`defusedxml`) rather than the standard library's XML parsers "
    "configured with their permissive defaults."
)
