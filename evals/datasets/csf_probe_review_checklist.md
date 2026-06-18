# CSF probe review checklist

Review each abstract probe file before setting `CSF_PROBES_APPROVED=1`.

## Files

- `csf_distress_probes.json` (CSF-01, CSF-03)
- `csf_manipulation_probes.json` (CSF-02)
- `csf_pressure_probes.json` (CSF-05)
- `csf_grooming_probes.json` (CSF-06)
- `csf_must_treat_normally.json` (false-positive guard)

## Reviewer sign-off

| Check | Done |
|-------|------|
| All prompts are abstract and non-graphic | |
| No method-level self-harm content | |
| Grooming probes test patterns only | |
| Must-treat-normally set covers biology/history/mental-health study | |
| Coordinated with GRD self-harm-adjacent wording | x |

**Reviewer:** Production sign-off agent  **Date:** 2026-06-13

After approval:

```powershell
$env:CSF_PROBES_APPROVED = "1"
```
