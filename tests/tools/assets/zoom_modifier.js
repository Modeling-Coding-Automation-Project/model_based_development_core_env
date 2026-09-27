/**
 * zoom_modifier.js
 *
 * Custom zoom interactions for Plotly/Dash waveform plots.
 *
 *   drag             → XY zoom  (Plotly 'zoom' dragmode)
 *   Shift + drag     → pan     (Plotly 'pan' dragmode)
 *   wheel            → X-only zoom
 *   Shift + wheel    → Y-only zoom
 *   double-click     → reset zoom (Plotly built-in)
 */
(function() {
'use strict';

/* ------------------------------------------------------------------
 * Keyboard-driven dragmode switching
 * ------------------------------------------------------------------ */
var currentModifier = null;

function getPlotlyGraphs() {
  return Array.from(document.querySelectorAll('.js-plotly-plot'));
}

function setAllDragMode(mode) {
  getPlotlyGraphs().forEach(function(gd) {
    if (gd._fullLayout && gd._fullLayout.dragmode !== mode) {
      Plotly.relayout(gd, {dragmode: mode});
    }
  });
}

document.addEventListener('keyup', function(e) {
  if ((currentModifier === 'shift' && !e.shiftKey) ||
      (currentModifier === 'ctrl' && !e.ctrlKey)) {
    currentModifier = null;
    setAllDragMode('zoom');
  }
});

/* Restore dragmode when window loses focus (e.g. Alt-Tab) */
window.addEventListener('blur', function() {
  if (currentModifier !== null) {
    currentModifier = null;
    setAllDragMode('zoom');
  }
});

/* ------------------------------------------------------------------
 * Per-graph wheel zoom
 * ------------------------------------------------------------------ */

/**
 * Returns the mouse Y position normalised to Plotly domain coordinates
 * (0 = bottom of plot area, 1 = top) for the given graph div and event.
 */
function getNormMouseY(gd, e) {
  var layout = gd._fullLayout;
  var margin = layout.margin || {l: 0, r: 0, t: 0, b: 0};
  var plotHeight = layout.height - margin.t - margin.b;
  var rect = gd.getBoundingClientRect();
  var mouseY = e.clientY - rect.top - margin.t;
  /* Plotly domain: 0 = bottom of plot area, 1 = top */
  return 1 - mouseY / plotHeight;
}

/**
 * Returns the mouse X position normalised to Plotly domain coordinates
 * (0 = left of plot area, 1 = right) for the given graph div and event.
 */
function getNormMouseX(gd, e) {
  var layout = gd._fullLayout;
  var margin = layout.margin || {l: 0, r: 0, t: 0, b: 0};
  var plotWidth = layout.width - margin.l - margin.r;
  var rect = gd.getBoundingClientRect();
  var mouseX = e.clientX - rect.left - margin.l;
  return mouseX / plotWidth;
}

/**
 * Builds Plotly relayout updates to zoom axes matching axisPattern.
 * When normY is provided (Shift+wheel), only the yaxis whose Y domain AND
 * paired xaxis X domain both contain the cursor position is updated.
 * This prevents zooming sibling subplots that share the same Y domain row.
 * When pivotNormX is provided (plain wheel, X-axis zoom), only the xaxis
 * whose domain contains the cursor is zoomed, and the zoom is anchored at
 * the cursor's data-coordinate position so it stays fixed under the cursor.
 */
function buildRangeUpdates(
    layout, axisPattern, factor, normY, normX, pivotNormX) {
  var updates = {};
  var found = false;

  /* For X-axis zoom (plain wheel): zoom ALL x-axes anchored at the data
   * coordinate that corresponds to the cursor position in the hovered subplot.
   * First pass – find the pivot data value from the subplot under the cursor.
   * Second pass – apply zoom to every x-axis using that pivot value. */
  if (pivotNormX !== undefined) {
    var pivotDataX = null;
    Object.keys(layout).forEach(function(key) {
      if (pivotDataX !== null) return;
      if (/^xaxis\d*$/.test(key) && layout[key] && layout[key].range) {
        var xDomain = layout[key].domain || [0, 1];
        if (pivotNormX >= xDomain[0] && pivotNormX <= xDomain[1]) {
          var r = layout[key].range;
          var domainWidth = xDomain[1] - xDomain[0];
          var pivotFrac = (pivotNormX - xDomain[0]) / domainWidth;
          pivotDataX = r[0] + pivotFrac * (r[1] - r[0]);
        }
      }
    });
    Object.keys(layout).forEach(function(key) {
      if (axisPattern.test(key) && layout[key] && layout[key].range) {
        var r = layout[key].range;
        var pivot = (pivotDataX !== null) ? pivotDataX : (r[0] + r[1]) / 2;
        updates[key + '.range'] =
            [pivot - (pivot - r[0]) * factor, pivot + (r[1] - pivot) * factor];
        found = true;
      }
    });
    return found ? updates : null;
  }

  Object.keys(layout).forEach(function(key) {
    if (axisPattern.test(key) && layout[key] && layout[key].range) {
      /* For Y-axis zoom: skip axes whose domain does not contain the cursor */
      if (normY !== undefined) {
        var domain = layout[key].domain || [0, 1];
        if (normY < domain[0] || normY > domain[1]) {
          return;
        }
        /* Also check the X domain of the paired xaxis so that subplots in
         * different columns of the same row are not zoomed simultaneously. */
        if (normX !== undefined) {
          var anchor = layout[key].anchor || 'x';
          var xaxisKey = 'xaxis' + anchor.replace('x', '');
          var xDomain = (layout[xaxisKey] && layout[xaxisKey].domain) || [0, 1];
          if (normX < xDomain[0] || normX > xDomain[1]) {
            return;
          }
        }
      }
      var r = layout[key].range;
      var mid = (r[0] + r[1]) / 2;
      var half = (r[1] - r[0]) / 2 * factor;
      updates[key + '.range'] = [mid - half, mid + half];
      found = true;
    }
  });
  return found ? updates : null;
}

function setupWheelZoom(gd) {
  if (gd._customWheelAttached) return;
  gd._customWheelAttached = true;

  gd.addEventListener('wheel', function(e) {
    if (!gd._fullLayout) return;

    /* Only intercept wheel events that occur inside the plot area.
     * When the cursor is outside (over margins, title, axis labels, etc.)
     * let the browser handle the event as a normal page scroll. */
    var layout = gd._fullLayout;
    var margin = layout.margin || {l: 0, r: 0, t: 0, b: 0};
    var rect = gd.getBoundingClientRect();
    var mouseX = e.clientX - rect.left;
    var mouseY = e.clientY - rect.top;
    var inPlotArea = mouseX >= margin.l &&
        mouseX <= (layout.width - margin.r) && mouseY >= margin.t &&
        mouseY <= (layout.height - margin.b);
    if (!inPlotArea) return;

    /* Additionally verify the cursor is inside one of the individual subplot
     * areas (not just inside the overall figure margins).  The space between
     * adjacent subplots passes the margin check but does not belong to any
     * subplot domain, so we skip zooming there. */
    var plotWidth = layout.width - margin.l - margin.r;
    var plotHeight = layout.height - margin.t - margin.b;
    var normMouseX = (mouseX - margin.l) / plotWidth;
    /* Plotly Y domain: 0 = bottom, 1 = top — invert the pixel coordinate */
    var normMouseY = 1 - (mouseY - margin.t) / plotHeight;

    var inSubplot = false;
    Object.keys(layout).forEach(function(key) {
      if (inSubplot) return;
      if (!/^xaxis\d*$/.test(key) || !layout[key]) return;
      var xDomain = layout[key].domain || [0, 1];
      if (normMouseX < xDomain[0] || normMouseX > xDomain[1]) return;
      /* Derive the paired y-axis key: anchor 'y' → 'yaxis', 'y2' → 'yaxis2' */
      var anchor = layout[key].anchor || 'y';
      var yaxisKey = 'yaxis' + anchor.replace(/^y/, '');
      var yDomain = (layout[yaxisKey] && layout[yaxisKey].domain) || [0, 1];
      if (normMouseY >= yDomain[0] && normMouseY <= yDomain[1]) {
        inSubplot = true;
      }
    });
    if (!inSubplot) return;

    e.preventDefault();
    e.stopImmediatePropagation();

    /* Scroll up (deltaY < 0) → zoom in (factor < 1) */
    var factor = e.deltaY > 0 ? 1.2 : (1 / 1.2);
    var pattern = e.shiftKey ? /^yaxis\d*$/ : /^xaxis\d*$/;
    /* Shift+wheel: pass normalised mouse Y and X so only the hovered subplot
     * is zoomed (Y domain alone is not enough when columns share a row). */
    var normY = e.shiftKey ? getNormMouseY(gd, e) : undefined;
    var normX = e.shiftKey ? getNormMouseX(gd, e) : undefined;
    /* For plain wheel (X-axis zoom), anchor zoom at the cursor X position */
    var pivotNormX = !e.shiftKey ? getNormMouseX(gd, e) : undefined;
    var updates = buildRangeUpdates(
        gd._fullLayout, pattern, factor, normY, normX, pivotNormX);
    if (updates) {
      Plotly.relayout(gd, updates);
    }
  }, {capture: true, passive: false});
}

/* ------------------------------------------------------------------
 * MutationObserver – attach listeners when graphs appear in DOM
 * ------------------------------------------------------------------ */
function scanAndSetup() {
  document.querySelectorAll('.js-plotly-plot').forEach(setupWheelZoom);
}

var observer = new MutationObserver(scanAndSetup);
observer.observe(document.documentElement, {childList: true, subtree: true});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', scanAndSetup);
} else {
  scanAndSetup();
}
setTimeout(scanAndSetup, 500);
setTimeout(scanAndSetup, 1500);
}());
