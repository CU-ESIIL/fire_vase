"""Shared HTML/JS helpers for drift centering the cube viewer."""

from __future__ import annotations


def drift_centering_script(viewer_id: str | None = None) -> str:
    """Return the drift-centering script tag for cube viewers."""

    viewer_id_js = f'"{viewer_id}"' if viewer_id else "null"
    return f"""
  <script id="cd-drift-center-v1-js">
    (function() {{
      // Drift centering defaults (DYNAMIC DRIFT CENTERING V1):
      // MAX_DRIFT_PX=220, ROT_RANGE_DEG=55, SCALE_IN=1.25, SCALE_OUT=0.85, SMOOTHING=0.18
      const viewerId = {viewer_id_js};
      const defaults = {{
        maxDriftPx: 220,
        rotRangeDeg: 55,
        scaleIn: 1.25,
        scaleOut: 0.85,
        smoothing: 0.18,
      }};

      const registry = window.__cdDriftCenterV1 || {{
        viewers: new Set(),
        rafId: null,
      }};
      window.__cdDriftCenterV1 = registry;
      window.__cdDriftCenterInstalled = true;

      function readNumber(styles, name, fallback) {{
        const value = parseFloat(styles.getPropertyValue(name));
        return Number.isFinite(value) ? value : fallback;
      }}

      function resolveConfig(root) {{
        const styles = getComputedStyle(root);
        return {{
          maxDriftPx: readNumber(styles, "--cd-drift-max-px", defaults.maxDriftPx),
          rotRangeDeg: readNumber(styles, "--cd-drift-rot-range-deg", defaults.rotRangeDeg),
          scaleIn: readNumber(styles, "--cd-drift-scale-in", defaults.scaleIn),
          scaleOut: readNumber(styles, "--cd-drift-scale-out", defaults.scaleOut),
          smoothing: readNumber(styles, "--cd-drift-smoothing", defaults.smoothing),
        }};
      }}

      function getViewerRoots() {{
        if (viewerId) {{
          const root = document.getElementById("cube-figure-" + viewerId);
          return root ? [root] : Array.from(document.querySelectorAll(".cube-figure"));
        }}
        return Array.from(document.querySelectorAll(".cube-figure"));
      }}

      function applyDrift(state, x) {{
        if (state.supportsTranslate) {{
          state.scene.style.translate = `${{x}}px 0px`;
          return;
        }}
        if (!state.fallbackReady) {{
          const baseTransform = getComputedStyle(state.scene).transform;
          state.scene.style.setProperty(
            "--cd-drift-base-transform",
            baseTransform && baseTransform !== "none" ? baseTransform : "none",
          );
          state.scene.classList.add("cd-drift-center-fallback");
          state.fallbackReady = true;
        }}
        state.scene.style.setProperty("--cd-drift-x", `${{x}}px`);
      }}

      function updateViewer(state) {{
        const transform = getComputedStyle(state.rotation).transform;
        const matrix = new DOMMatrixReadOnly(transform === "none" ? undefined : transform);
        const scale = Math.hypot(matrix.m11, matrix.m12, matrix.m13) || 1;
        const rotY = Math.atan2(matrix.m13, matrix.m11);
        const rotDeg = rotY * 180 / Math.PI;
        const normRot = Math.max(-1, Math.min(1, rotDeg / state.config.rotRangeDeg));
        const z = Math.max(
          0,
          Math.min(
            1,
            (scale - state.config.scaleOut) / (state.config.scaleIn - state.config.scaleOut),
          ),
        );
        const strength = 1 - z;
        state.targetX = -normRot * state.config.maxDriftPx * strength;
        state.currentX = state.currentX + (state.targetX - state.currentX) * state.config.smoothing;
        applyDrift(state, state.currentX);
      }}

      function tick() {{
        registry.viewers.forEach((state) => {{
          if (!state.root.isConnected) {{
            registry.viewers.delete(state);
            return;
          }}
          updateViewer(state);
        }});
        if (registry.viewers.size > 0) {{
          registry.rafId = window.requestAnimationFrame(tick);
        }} else {{
          registry.rafId = null;
        }}
      }}

      function registerViewer(root) {{
        if (!root || root.dataset.cdDriftCenterInstalled === "true") return;
        const rotation = root.querySelector(".cube-rotation");
        const scene =
          root.querySelector(".cube-scene")
          || root.querySelector(".cube-wrapper");
        if (!rotation || !scene) return;
        root.dataset.cdDriftCenterInstalled = "true";
        const state = {{
          root,
          rotation,
          scene,
          config: resolveConfig(root),
          currentX: 0,
          targetX: 0,
          supportsTranslate: "translate" in document.documentElement.style,
          fallbackReady: false,
        }};
        registry.viewers.add(state);
        if (!registry.rafId) {{
          registry.rafId = window.requestAnimationFrame(tick);
        }}
      }}

      getViewerRoots().forEach(registerViewer);
    }})();
  </script>
    """


__all__ = ["drift_centering_script"]
