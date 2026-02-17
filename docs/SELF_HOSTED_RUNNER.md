# Self-Hosted Runner (Optional Hardware Tests)

You only need this for physical-device regression in `HIL Regression`.

## What this is

A self-hosted runner is a small GitHub Actions agent running on your own machine.
It lets workflows access local USB hardware (your SmartScreen device).

## What runs without this

Nightly software regression already runs on GitHub-hosted Linux (`ubuntu-latest`), no setup needed.

## Setup steps (Windows 11 machine recommended)

1. In GitHub repo, go to:
   `Settings -> Actions -> Runners -> New self-hosted runner`
2. Choose OS matching your machine (Windows/Linux/macOS).
3. Follow the generated install commands exactly.
4. Add label `smartscreen-hil` during runner configuration.
5. Start runner service and keep machine online when you want hardware tests.

## Trigger hardware run

- Open `Actions -> HIL Regression -> Run workflow`
- Enable input: `run_hardware = true`

## Notes

- This runner has access to your local machine. Treat it as trusted infrastructure.
- For stable runs, disable sleep and USB selective suspend on that machine.
- Keep Python and USB serial drivers updated.
