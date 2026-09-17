# ADR-008 — The normalized channel carries an offset map, in m0's convention

- **Status:** PROPOSED by engineering (2026-09-17); used by m2 and m1 from this date; the owner
  ratifies or amends. Nothing in the frozen contract changes.
- **Scope:** `modules/m2_deobf/module.py`, `modules/m1_lexicon/module.py`, `modules/m2_deobf/spec.md`
  (contract paragraph), `modules/m3_encoder/spec.md` §5 (truncation alignment, later)
- **Open question closed on the engineering side:** OPEN_QUESTIONS Q5 (the *carrier*). The policy
  half of Q5 — whether a hit found only on the normalized channel may fire a code — is not touched:
  it stays with `fusion.strategy: max` over both channels exactly as configured today.

## Context

Every content score and guard must carry the span of the exact substring of the **original**
text (ADR-001). m1 scans the normalized channel (m1 spec §3) but had no way to map a match in
`normalized_text` back to the original: it emitted spanned scores only when the two texts had
equal length and assumed position-for-position alignment (`m1/module.py`, U-M1-2). Any repair
that changes length — repeat folding, separator removal, leet mapping with multi-character
output — made every normalized-channel hit flag-only, so the parallel channel could never fire a
code. m3's spec §5 needs the same map to truncate both channels at the same character offset.

m0 already solved the identical problem for its own output: it publishes the internal signal
`_offsets` — the original index of every character of `charsafe_text` — and m1 maps raw-channel
spans through it. ADR-001 ("Consequences") records that convention as the way guard producers
compute original offsets. `_`-prefixed signal keys are internal by HANDOVER #21: passed to later
modules through `ctx.signals`, stripped from the response.

## Decision (proposed)

1. **m2 publishes `signals["_offsets"]`**: a list with one entry per character of
   `normalized_text`, holding the index in `ctx.text` (the ORIGINAL text, not `charsafe_text`) of
   the character it came from. For a character produced by a repair (for example a Turkish letter
   restored by DEASCII, or the single character left after folding a run), the index is that of the
   first original character it replaces. Deleted characters have no entry. Inserted characters that
   correspond to no original character (none in v1: every m2 repair keeps or shrinks) would carry
   the index of the preceding kept character.
2. **m2 publishes `signals["offsets_identity"]`**: true iff every character kept its original
   index (i.e. the channel equals the original text).
3. **Invariants** (pinned by `tests/test_signal_interfaces.py`): `len(_offsets) == len(normalized_text)`;
   every entry is an `int` in `[0, len(text))`; entries are non-decreasing; the map composes m0's:
   m2 reads `charsafe_text` and m0's `_offsets`, so an m2 offset is an original-text index, never a
   charsafe index.
4. **m1 reads it** for the normalized channel exactly as it reads m0's for the raw channel: when
   `signals["m2_deobf"]["_offsets"]` is present and its length equals `len(normalized_text)`, every
   normalized-channel match and collision is mapped through it; the same-length fallback stays only
   for a channel with no map. `_to_original` extends the end of a span over trailing combining
   marks as it does today.
5. **Span semantics for a repaired token.** A root matched on the normalized channel inside a
   repaired token maps to the original span covering the original characters of that root's
   characters — for `s.a.l.a.k` normalized to `salak`, the `A1` span is the whole `s.a.l.a.k`
   (first to last mapped character, end-exclusive), so `text[start:end]` is the obfuscated
   surface the reader sees. This is the ADR-001 requirement ("exact substring of the original
   text that triggered it") applied to a channel that exists precisely because the surface was
   altered.
6. **Not decided here:** thresholds for normalized-channel scores, fusion strategy, whether a
   normalized-only hit may fire (policy). Today `fusion.strategy: max` over `[raw, normalized]` is
   configured and applies unchanged.

## Consequences

- m1's `lexicon_hit_norm` can now be accompanied by a spanned `A1@normalized` score for
  length-changing repairs; the flag-only path remains for a channel without a map.
- The cross-channel deduplication of collision guards by original span (U-M1-6, Q8) is unchanged
  by this ADR and stays an open question for the m1 owner.
- m3 spec §5's "truncate both channels at the same character offset" becomes implementable; not
  done in this ADR.
- The contract example changes when m2 starts publishing a normalized channel (m1's signals,
  form patterns, `per_module_ms` keys are unaffected in shape) and is regenerated on explicit
  instruction as before.
