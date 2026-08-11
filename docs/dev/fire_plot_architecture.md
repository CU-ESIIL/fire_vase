# Fire plot architecture and migration path

## 1) Purpose

This note documents the current fire-visualization architecture and gives a safe migration path toward shared viewer semantics.

A successful migration will not begin by swapping plotting libraries. It will begin by making the fire-event products renderer-neutral enough that the same event geometry can drive either the existing Plotly hull figure or a future custom cube-viewer scene.

## 2) Current state

- `v.plot()` is the canonical custom HTML/CSS/JS cube viewer for general cube rendering.
- `v.fire_plot()` currently returns a fire-event analysis bundle and uses a Plotly hull figure (`fig_hull`) as the supported interactive fire-specific display.
- Fire geometry and climate sampling logic live in backend-agnostic parts of the fire workflow, while the final figure is currently Plotly-specific.

## 3) Stable separations of concern

Keep these layers distinct when modifying fire visualization:

1. Event or cube data construction
2. Geometry generation
3. Scene/adapter packaging
4. Rendering backend

This separation enables one event product to feed multiple renderers and reduces regression risk.

## 4) Migration strategy

1. Make docs and interfaces honest about current backend status.
2. Factor fire-event outputs into a renderer-neutral scene description or data adapter.
3. Implement a custom-viewer renderer for that adapter.
4. Only then consider changing the default fire viewer backend.

## 5) Anti-patterns to avoid

- Swapping rendering libraries before adapter/data boundaries are stable.
- Duplicating geometry logic independently in multiple renderers.
- Claiming migration is complete while `v.fire_plot()` still returns a Plotly-only interactive path.
- Changing coordinate or axis conventions without updating invariants and tests together.

## 6) Recommended next incremental PRs

- Introduce a thin renderer-neutral adapter object for fire scene payloads (without changing current return keys).
- Add tests that validate adapter payload shape and mapping from hull/summary outputs.
- Implement an experimental custom-viewer renderer behind a non-default option.
- Compare semantic parity (axes, time-depth direction, labels, camera defaults) before any default switch.
