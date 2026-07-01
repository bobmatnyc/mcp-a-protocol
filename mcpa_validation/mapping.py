"""
Explicit example→schema manifest.

Source of truth: examples/README.md (the step-by-step narrative).
Each tuple is (relative_example_path, relative_schema_path) where both paths
are relative to the repo root.

Exceptions noted inline:
- 07-error-aggregation.response → error.json  (error-case response)
- 08-poll.* → follow_up.*  (polling reuses follow_up primitive)
- schemas/examples/query.response.structured.example.json → query.response.json
"""
from __future__ import annotations

# Each entry: (example_path_relative_to_repo_root, schema_filename_in_schemas/)
# schema_filename is just the basename; callers resolve against schemas_dir.
MANIFEST: list[tuple[str, str]] = [
    ("examples/01-discover.request.json", "discover.request.json"),
    ("examples/01-discover.response.json", "discover.response.json"),
    ("examples/02-schema.request.json", "schema.request.json"),
    ("examples/02-schema.response.json", "schema.response.json"),
    ("examples/03-query-prose.request.json", "query.request.json"),
    ("examples/03-query-prose.response.json", "query.response.json"),
    ("examples/04-query-structured.request.json", "query.request.json"),
    ("examples/04-query-structured.response.json", "query.response.json"),
    ("examples/05-follow_up.request.json", "follow_up.request.json"),
    ("examples/05-follow_up.response.json", "follow_up.response.json"),
    ("examples/06-explain.request.json", "explain.request.json"),
    ("examples/06-explain.response.json", "explain.response.json"),
    ("examples/07-error-aggregation.request.json", "query.request.json"),
    ("examples/07-error-aggregation.response.json", "error.json"),  # ERROR case
    ("examples/08-query-draft.request.json", "query.request.json"),
    ("examples/08-query-draft.response.json", "query.response.json"),
    ("examples/08-poll.request.json", "follow_up.request.json"),  # poll = follow_up
    ("examples/08-poll.response.json", "follow_up.response.json"),
    ("examples/09-action.request.json", "action.request.json"),
    ("examples/09-action.response.json", "action.response.json"),
    ("examples/10-action-clarify.request.json", "action.request.json"),
    ("examples/10-action-clarify.response.json", "action.response.json"),
    ("examples/11-action-resume.request.json", "action.request.json"),
    ("examples/11-action-resume.response.json", "action.response.json"),
    ("examples/12-schema-drill.request.json", "schema.request.json"),
    ("examples/12-schema-drill.response.json", "schema.response.json"),
    ("examples/12b-schema-drill.request.json", "schema.request.json"),
    ("examples/12b-schema-drill.response.json", "schema.response.json"),
    ("examples/13-schema-action.request.json", "schema.request.json"),
    ("examples/13-schema-action.response.json", "schema.response.json"),
    # GraphQL-backed storefront domain (guides/ companion examples)
    ("examples/14-discover-graphql.request.json", "discover.request.json"),
    ("examples/14-discover-graphql.response.json", "discover.response.json"),
    ("examples/15-schema-graphql.request.json", "schema.request.json"),
    ("examples/15-schema-graphql.response.json", "schema.response.json"),
    ("examples/16-query-graphql-structured.request.json", "query.request.json"),
    ("examples/16-query-graphql-structured.response.json", "query.response.json"),
    ("examples/17-action-graphql.request.json", "action.request.json"),
    ("examples/17-action-graphql.response.json", "action.response.json"),
    ("examples/18-explain-graphql.request.json", "explain.request.json"),
    ("examples/18-explain-graphql.response.json", "explain.response.json"),
    # REST-backed support-desk domain (guides/rest-api-mapping.md companion)
    ("examples/19-discover-rest.request.json", "discover.request.json"),
    ("examples/19-discover-rest.response.json", "discover.response.json"),
    ("examples/20-schema-rest.request.json", "schema.request.json"),
    ("examples/20-schema-rest.response.json", "schema.response.json"),
    ("examples/21-query-rest.request.json", "query.request.json"),
    ("examples/21-query-rest.response.json", "query.response.json"),
    ("examples/22-action-rest.request.json", "action.request.json"),
    ("examples/22-action-rest.response.json", "action.response.json"),
    # SQL-backed analytics-warehouse domain (guides/sql-query-builder.md companion)
    ("examples/23-discover-sql.request.json", "discover.request.json"),
    ("examples/23-discover-sql.response.json", "discover.response.json"),
    ("examples/24-schema-sql.request.json", "schema.request.json"),
    ("examples/24-schema-sql.response.json", "schema.response.json"),
    ("examples/25-query-sql.request.json", "query.request.json"),
    ("examples/25-query-sql.response.json", "query.response.json"),
    # Query clarification round (MAEP-0005)
    ("examples/26-query-clarify.request.json", "query.request.json"),
    ("examples/26-query-clarify.response.json", "query.response.json"),
    (
        "schemas/examples/query.response.structured.example.json",
        "query.response.json",
    ),
]
