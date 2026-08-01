"""Remediation guidance for cross-site scripting."""

GUIDANCE = (
    "Render user-controlled content through the templating engine's "
    "normal auto-escaping output (plain `{{ variable }}`), never via an "
    "explicit unescape/raw-HTML mechanism (`| safe`, `Markup()`, "
    "`dangerouslySetInnerHTML`, `.innerHTML =`, `v-html`) unless the "
    "content has already been through a dedicated HTML sanitizer -- and "
    "if it has, say so explicitly in your summary along with which "
    "sanitizer, since removing the unescape call without sanitizing may "
    "just move the bug rather than fix it."
)
