---
MAEP: XXXX
Title: [Concise title — keep it under 60 characters]
Author: [Your Name] <your@email.com>
Status: Draft
Created: YYYY-MM-DD
Spec-Version-Target: [e.g. 1.0, 1.1, 2.0]
---

## Summary

One or two sentences.  What are you adding, changing, or removing?  A reader who
only reads this section should know exactly what the proposal does.

## Motivation

Why is this change needed?  What problem does it solve, and for whom?  Be specific
about the use case.  If an existing behavior is broken or missing, show the gap --
an example request/response pair that illustrates the problem is worth a paragraph
of prose.

## Specification

*This section is normative.  Use RFC 2119 keywords (MUST, SHOULD, MAY, etc.) in
ALL CAPS.  Reference `SPEC.md` for existing primitive definitions rather than
restating them.*

Describe the change to the protocol:

- New fields, types, or primitives and their exact shape (JSON Schema or prose).
- New MUST/SHOULD/MAY rules for servers and clients.
- Error codes and conditions (e.g., when a server MUST return 422).
- Interactions with existing primitives, if any.

## Rationale and Alternatives

Why this approach over the alternatives you considered?  Be direct about the
trade-offs.  If there is an obvious alternative that you are not taking, explain
why -- the record matters for future readers.

## Backwards Compatibility

Is this a breaking change?  State it plainly.

- If additive: describe what existing clients see when they do not send the new
  field, and what servers MUST do in that case.
- If breaking: state which semver component bumps and what migration path exists
  for existing implementations.

## Reference Implementation

Link to or describe the reference implementation, if one exists.  If not yet
started, note the planned language/framework and any known gotchas for
implementers.

## Open Questions

List the specific feedback you are requesting from reviewers.  Unanswered design
questions belong here, not buried in the Specification section.

## References

- [SPEC.md](../spec/SPEC.md) -- full primitive definitions
- [Related MAEP](./NNNN-related.md) -- if applicable
- [GitHub issue](https://github.com/org/mcp-a-spec/issues/N) -- discussion thread
