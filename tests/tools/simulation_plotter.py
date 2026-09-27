"""
This module provides the SimulationPlotter class,
which facilitates the collection, organization,
and visualization of simulation signal data
using Plotly for interactive web-based visualization.

It implements the same interface as SimulationPlotter
but replaces matplotlib with Plotly for charts,
enabling interactive features such as zoom, pan,
hover tooltips, and dual cursor mode.
Results are saved as standalone HTML files and opened in the default browser.

Classes:
    SimulationPlotter:
        A class for managing and visualizing simulation signals
        using Plotly.
        It provides methods to append signals, assign them to subplots,
        and generate plots with customizable appearance and layout.
"""
import os
import json
import pickle
import inspect
import webbrowser
import numpy as np
from pathlib import Path
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go

_CACHE_FOLDER = Path.cwd() / "cache"
DUMP_FOLDER_PATH = _CACHE_FOLDER / "simulation_plotter_dumps"

_LINE_STYLE_MAP = {
    "-": "solid",
    "--": "dash",
    ":": "dot",
    "-.": "dashdot",
}

_PLOTLY_COLORS = [
    '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
    '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
]

_MARKER_MAP = {
    ".": "circle",
    "o": "circle",
    "^": "triangle-up",
    "v": "triangle-down",
    "s": "square",
    "*": "star",
    "+": "cross",
    "x": "x",
    "D": "diamond",
    "d": "diamond-thin",
    "p": "pentagon",
    "h": "hexagon",
}


def _convert_line_style(mpl_style):
    """Convert a matplotlib line style string to a Plotly dash string."""
    return _LINE_STYLE_MAP.get(mpl_style, "solid")


def _convert_marker(mpl_marker):
    """Convert a matplotlib marker string to a Plotly marker symbol string."""
    return _MARKER_MAP.get(mpl_marker, "circle")


class SubplotsInfo:
    def __init__(self, signal_name, shape,
                 column, row, x_sequence,
                 x_sequence_name, line_style,
                 marker, label):

        self.signal_name = signal_name
        self.shape = shape
        self.column = column
        self.row = row

        self.x_sequence = x_sequence
        self.x_sequence_name = x_sequence_name

        self.line_style = line_style
        self.label = label
        self.marker = marker


class Configuration:
    def __init__(self):
        self.subplots_shape = np.zeros((2, 1), dtype=int)
        self.subplots_signals_list = []
        self.dual_cursor_mode = False


class SimulationPlotter:

    def __init__(self, activate_dump=False):
        self.configuration = Configuration()
        self.name_to_object_dictionary = {}
        self.activate_dump = activate_dump
        self._pre_plot_figures = []

    def append(self, signal_object):
        """
        Appends a signal object to the internal name-to-object dictionary
         using the variable name from the caller's local scope as the key.

        Args:
            signal_object: The signal object to be appended and tracked.

        Raises:
            ValueError: If the variable name for signal_object
             cannot be determined from the caller's local scope.
        """
        frame = inspect.currentframe().f_back
        caller_locals = frame.f_locals
        object_name = None
        for name, value in caller_locals.items():
            if value is signal_object:
                object_name = name
                break
        del frame

        signal_copy = np.copy(signal_object)
        if object_name in self.name_to_object_dictionary:
            self.name_to_object_dictionary[object_name].append(signal_copy)
        else:
            self.name_to_object_dictionary[object_name] = [signal_copy]

    def append_name(self, signal_object, object_name):
        """
        Appends a signal object to the list associated with the given
        object name in the name_to_object_dictionary.

        Args:
            signal_object: The signal object to be associated with the object name.
            object_name (str): The key representing the name to which
             the signal object should be appended.
        """
        signal_copy = np.copy(signal_object)
        if object_name in self.name_to_object_dictionary:
            self.name_to_object_dictionary[object_name].append(signal_copy)
        else:
            self.name_to_object_dictionary[object_name] = [signal_copy]

    def append_sequence(self, signal_sequence_object):
        """
        Appends a sequence of signal objects to the internal
        name-to-object dictionary.

        Args:
            signal_sequence_object (iterable): An iterable of signal objects
             (e.g., numpy arrays) to be appended. Each element is reshaped
             to a column vector before appending.
        """
        frame = inspect.currentframe().f_back
        caller_locals = frame.f_locals
        object_name = None
        for name, value in caller_locals.items():
            if value is signal_sequence_object:
                object_name = name
                break
        del frame

        for i in range(len(signal_sequence_object)):
            signal_copy = np.copy(signal_sequence_object[i])
            if object_name in self.name_to_object_dictionary:
                self.name_to_object_dictionary[object_name].append(
                    signal_copy.reshape(-1, 1))
            else:
                self.name_to_object_dictionary[object_name] = [
                    signal_copy.reshape(-1, 1)]

    def append_sequence_name(self, signal_sequence_object, object_name):
        """
        Appends reshaped elements from a signal sequence to a dictionary
        entry keyed by object_name.

        Args:
            signal_sequence_object (iterable): An iterable of signal data
             (e.g., numpy arrays) to be reshaped and stored.
            object_name (str): The key under which the reshaped signal data
             will be stored in the dictionary.
        """
        for i in range(len(signal_sequence_object)):
            signal_copy = np.copy(signal_sequence_object[i])
            if object_name in self.name_to_object_dictionary:
                self.name_to_object_dictionary[object_name].append(
                    signal_copy.reshape(-1, 1))
            else:
                self.name_to_object_dictionary[object_name] = [
                    signal_copy.reshape(-1, 1)]

    def assign(self, signal_name, position,
               column=0, row=0, x_sequence=None, x_sequence_name=None,
               line_style="-", marker="", label=""):
        """
        Assigns a signal to a subplot configuration for visualization.

        Parameters:
            signal_name (str): The name of the signal to assign.
            position (tuple or list): The (row_position, column_position) of the subplot in the grid.
            row (int, optional): The row-direction index of the signal array.
             Defaults to 0.
            column (int, optional): The column-direction index of the signal array.
             Defaults to 0.
            x_sequence (array-like or str, optional): The x-axis data sequence
             or its name.
            x_sequence_name (str, optional): The name of the x_sequence.
            line_style (str, optional): The line style for plotting.
             Defaults to "-".
            marker (str, optional): The marker style for plotting.
             Defaults to "".
            label (str, optional): The label for the plot legend.
             Defaults to "".
        """
        this_x_sequence_name = ""
        if (x_sequence is not None) and (x_sequence_name is None):
            frame = inspect.currentframe().f_back
            caller_locals = frame.f_locals
            this_x_sequence_name = None
            for name, value in caller_locals.items():
                if value is x_sequence:
                    this_x_sequence_name = name
                    break
            del frame
        else:
            this_x_sequence_name = x_sequence_name

        if (x_sequence is not None) and isinstance(x_sequence, str):
            this_x_sequence_name = x_sequence
            x_sequence = self.name_to_object_dictionary[x_sequence]

        shape = np.array([[position[0]], [position[1]]], dtype=int)

        self.configuration.subplots_signals_list.append(
            SubplotsInfo(signal_name, shape,
                         column, row, x_sequence,
                         this_x_sequence_name, line_style,
                         marker, label))

    def assign_all(self, signal_name, position,
                   x_sequence=None, x_sequence_name=None,
                   line_style="-", marker="", label=""):
        """
        Assigns all elements of a signal (by name) to be plotted,
        iterating over its rows and columns.

        Parameters:
            signal_name (str): The name of the signal to assign for plotting.
            position (tuple or list): The (row_position, column_position) of the subplot in the grid.
            x_sequence (array-like, optional): The x-axis data sequence
             for the plot.
            x_sequence_name (str, optional): The name of the x_sequence
             variable.
            line_style (str, optional): The line style for the plot
             (default is "-").
            marker (str, optional): The marker style for the plot
             (default is "").
            label (str, optional): The base label for the plot.
             If not provided, uses signal_name.
        """
        this_x_sequence_name = ""
        if (x_sequence is not None) and (x_sequence_name is None):
            frame = inspect.currentframe().f_back
            caller_locals = frame.f_locals
            this_x_sequence_name = None
            for name, value in caller_locals.items():
                if value is x_sequence:
                    this_x_sequence_name = name
                    break
            del frame
        else:
            this_x_sequence_name = x_sequence_name

        row_size = self.name_to_object_dictionary[signal_name][0].shape[0]
        col_size = self.name_to_object_dictionary[signal_name][0].shape[1]

        if label == "":
            label = signal_name

        for i in range(row_size):
            for j in range(col_size):
                label_text = label + "_" + str(i) + "_" + str(j)
                self.assign(signal_name, position=position,
                            row=i, column=j,
                            x_sequence=x_sequence,
                            x_sequence_name=this_x_sequence_name,
                            line_style=line_style, marker=marker,
                            label=label_text)

    def pre_plot(self, suptitle=""):
        """
        Prepares a figure from the current subplot configuration
        and stores it internally for later display.

        This is the Dash equivalent of SimulationPlotter.pre_plot().
        Each call builds a Plotly figure from the currently assigned
        signals, stores it as a new tab page, and then resets the
        subplot assignment list so that subsequent assign / assign_all
        calls populate a new page.

        Call plot() after one or more pre_plot() calls to launch the
        Dash server and display all pages as browser tabs.

        Args:
            suptitle (str, optional): The title for this figure page.
                Defaults to an empty string.
        """
        if self.activate_dump:
            self._dump_simulation_plotter()

        fig, shape = self._build_figure(suptitle)
        if fig is None:
            return

        tab_label = suptitle if suptitle else f"Page {len(self._pre_plot_figures) + 1}"
        self._pre_plot_figures.append({
            'label': tab_label,
            'figure': fig,
            'shape': shape,
        })

        # Reset subplot assignments for the next page
        self.configuration.subplots_signals_list = []
        self.configuration.subplots_shape = np.zeros((2, 1), dtype=int)

    def _dump_simulation_plotter(self, filename=None):
        """
        Internal helper to dump the SimulationPlotter instance into
        a timestamped .npz file.
        """
        try:
            pickled = pickle.dumps(self)
        except Exception:
            snapshot = {}
            for k, v in self.__dict__.items():
                try:
                    pickle.dumps(v)
                    snapshot[k] = v
                except Exception:
                    snapshot[k] = None

            pickled = pickle.dumps(snapshot)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if filename is None:
            filename = f"SimulationPlotterData_{timestamp}.npz"

        save_file_path = os.path.join(DUMP_FOLDER_PATH, filename)
        os.makedirs(DUMP_FOLDER_PATH, exist_ok=True)

        try:
            np.savez(save_file_path, simulation_plotter=pickled)
        except Exception as e:
            print(f"Failed to save SimulationPlotter dump: {e}")

    def _build_figure(self, suptitle=""):
        """
        Build the Plotly figure from the current configuration.

        Args:
            suptitle (str): The title for the entire figure.

        Returns:
            tuple: (fig, shape) where fig is the Plotly Figure object
             and shape is a (2,1) numpy array with [n_rows, n_cols].
             Returns (None, None) if no subplots are configured.
        """
        subplots_signals_list = self.configuration.subplots_signals_list

        if len(subplots_signals_list) == 0:
            print("No subplots to show.")
            return None, None

        shape = np.zeros((2, 1), dtype=int)
        for signal_info in subplots_signals_list:
            if shape[0, 0] < signal_info.shape[0, 0] + 1:
                shape[0, 0] = signal_info.shape[0, 0] + 1
            if shape[1, 0] < signal_info.shape[1, 0] + 1:
                shape[1, 0] = signal_info.shape[1, 0] + 1

        self.configuration.subplots_shape = shape

        n_rows = int(shape[0, 0])
        n_cols = int(shape[1, 0])

        subplot_titles = [""] * (n_rows * n_cols)
        fig = make_subplots(
            rows=n_rows,
            cols=n_cols,
            subplot_titles=subplot_titles,
            shared_xaxes=False,
            shared_yaxes=False,
        )

        # Track legend entries per subplot: {(plot_row, plot_col): [(label, color), ...]}
        subplot_legends = {}
        trace_color_idx = 0

        for signal_info in subplots_signals_list:
            signal_object_list = self.name_to_object_dictionary[
                signal_info.signal_name]
            steps = len(signal_object_list)

            if signal_info.x_sequence is not None:
                x_arr = np.asarray(signal_info.x_sequence).reshape(-1)
                if x_arr.shape[0] < steps:
                    if x_arr.shape[0] == 0:
                        x_arr = np.zeros(steps)
                    else:
                        pad = np.empty(steps)
                        pad[:] = x_arr[-1]
                        pad[: x_arr.shape[0]] = x_arr
                        x_arr = pad
                x_sequence_signal = x_arr[:steps]
            else:
                x_sequence_signal = np.arange(steps, dtype=float)

            signal = np.zeros(steps)
            if isinstance(signal_object_list[0], np.ndarray):
                for i in range(steps):
                    arr = signal_object_list[i]
                    if arr.ndim == 0:
                        signal[i] = arr.item()
                    elif arr.ndim == 1:
                        signal[i] = arr[signal_info.row]
                    else:
                        signal[i] = arr[signal_info.row, signal_info.column]
            else:
                for i in range(steps):
                    signal[i] = signal_object_list[i]

            if signal_info.label == "":
                label_name = (signal_info.signal_name
                              + f"[{signal_info.row}, {signal_info.column}]")
            else:
                label_name = signal_info.label

            plot_row = int(signal_info.shape[0, 0]) + 1
            plot_col = int(signal_info.shape[1, 0]) + 1

            dash_style = _convert_line_style(signal_info.line_style)
            mode = "lines+markers" if signal_info.marker else "lines"
            marker_symbol = (_convert_marker(signal_info.marker)
                             if signal_info.marker else "circle")

            color = _PLOTLY_COLORS[trace_color_idx % len(_PLOTLY_COLORS)]
            trace_color_idx += 1

            trace = go.Scatter(
                x=x_sequence_signal.tolist(),
                y=signal.tolist(),
                name=label_name,
                showlegend=False,
                mode=mode,
                line=dict(dash=dash_style, color=color),
                marker=dict(symbol=marker_symbol, color=color),
            )

            fig.add_trace(trace, row=plot_row, col=plot_col)

            legend_key = (plot_row, plot_col)
            if legend_key not in subplot_legends:
                subplot_legends[legend_key] = []
            subplot_legends[legend_key].append((label_name, color))

            fig.update_xaxes(
                title_text=signal_info.x_sequence_name or "",
                showgrid=True,
                gridcolor='black',
                zeroline=True,
                zerolinecolor='black',
                zerolinewidth=1,
                showline=True,
                linecolor='black',
                linewidth=1,
                mirror=True,
                showspikes=True,
                spikemode='across',
                spikecolor='gray',
                spikethickness=1,
                spikedash='dot',
                row=plot_row,
                col=plot_col,
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor='black',
                zeroline=True,
                zerolinecolor='black',
                zerolinewidth=1,
                showline=True,
                linecolor='black',
                linewidth=1,
                mirror=True,
                showspikes=True,
                spikemode='across',
                spikecolor='gray',
                spikethickness=1,
                spikedash='dot',
                row=plot_row,
                col=plot_col,
            )

        # Build annotation-based legends, one block per subplot.
        # Use axis-domain references so each annotation is positioned
        # in the top-right corner of its own subplot area.
        legend_annotations = []
        for (ann_row, ann_col), entries in subplot_legends.items():
            axis_idx = (ann_row - 1) * n_cols + ann_col
            axis_suffix = '' if axis_idx == 1 else str(axis_idx)

            lines = [
                f"<span style='color:{clr}'>●</span> {lbl}"
                for lbl, clr in entries
            ]
            legend_annotations.append(dict(
                x=0.99,
                y=0.99,
                xref=f'x{axis_suffix} domain',
                yref=f'y{axis_suffix} domain',
                text='<br>'.join(lines),
                showarrow=False,
                align='left',
                xanchor='right',
                yanchor='top',
                bordercolor='black',
                borderwidth=1,
                bgcolor='white',
                font=dict(size=11),
            ))

        fig.update_layout(
            title_text=suptitle,
            height=max(400, 300 * n_rows),
            showlegend=False,
            annotations=legend_annotations,
            plot_bgcolor='white',
            paper_bgcolor='white',
            dragmode='zoom',
        )

        return fig, shape

    def _save_and_open_html(self, fig, shape, file_name="result",
                            tab_figures=None):
        """
        Save the plot as a standalone HTML file and open it in the browser.

        Args:
            fig: The Plotly Figure object (used when tab_figures is None).
            shape: A (2,1) numpy array with [n_rows, n_cols] (same).
            file_name (str): Base name for the output file (no extension).
            tab_figures (list[dict] | None): Pages to render; each dict has
                keys 'label', 'figure', 'shape'.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = file_name.strip() if file_name and file_name.strip() else "result"
        output_path = _CACHE_FOLDER / f"{timestamp}_{name}.html"
        _CACHE_FOLDER.mkdir(parents=True, exist_ok=True)

        pages = tab_figures if tab_figures else [
            {'label': name, 'figure': fig, 'shape': shape}
        ]
        output_path.write_text(self._build_html(pages), encoding='utf-8')
        print(f"HTML saved to: {output_path}")

        if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
            print("Headless environment detected. Skipping browser launch.")
            return

        if not webbrowser.open(output_path.as_uri()):
            print(
                f"Warning: Could not open browser. Open manually: {output_path}")

    def _build_html(self, pages):
        """Build a complete standalone HTML string with embedded Plotly figure(s)."""
        use_tabs = len(pages) > 1
        pages_data = [json.loads(p['figure'].to_json()) for p in pages]
        pages_json = json.dumps(pages_data)

        if use_tabs:
            btns = ''.join(
                f'<button class="tab-btn" id="tab-btn-{i}" '
                f'onclick="showTab({i})">{p["label"]}</button>'
                for i, p in enumerate(pages)
            )
            tab_bar = f'<div class="tab-bar">{btns}</div>\n'
        else:
            tab_bar = ''

        page_divs = []
        for i, pdata in enumerate(pages_data):
            graph_h = (pdata.get('layout') or {}).get('height') or 400
            hidden = ' style="display:none"' if i > 0 else ''
            page_divs.append(
                f'<div class="page" id="page-{i}"{hidden}>\n'
                f'  <div class="controls">\n'
                f'    <label><input type="checkbox" id="toggle-{i}">'
                f' Dual cursor mode</label>\n'
                f'    <div id="cc-{i}"'
                f' style="display:none;align-items:center;gap:8px;">\n'
                f'      <span style="font-size:13px">Select cursor: </span>\n'
                f'      <label style="font-size:13px;display:inline-flex;'
                f'align-items:center;gap:4px;"><input type="radio"'
                f' name="cr-{i}" id="r1-{i}" value="1" checked>'
                f' Cursor 1 (red)</label>\n'
                f'      <label style="font-size:13px;display:inline-flex;'
                f'align-items:center;gap:4px;"><input type="radio"'
                f' name="cr-{i}" id="r2-{i}" value="2">'
                f' Cursor 2 (blue)</label>\n'
                f'    </div>\n'
                f'  </div>\n'
                f'  <div id="graph-{i}" style="height:{graph_h}px;"></div>\n'
                f'</div>'
            )
        pages_html = '\n'.join(page_divs)

        zoom_js_path = Path(__file__).parent / 'assets' / 'zoom_modifier.js'
        try:
            zoom_js = zoom_js_path.read_text(encoding='utf-8')
        except Exception:
            zoom_js = ''

        init_tab = 'showTab(0);' if use_tabs else ''

        script = (
            '(function() {\n'
            '  var pagesData = ' + pages_json + ';\n'
            '\n'
            '  window.showTab = function(idx) {\n'
            '    document.querySelectorAll(".page").forEach(function(p, i) {\n'
            '      p.style.display = i === idx ? "block" : "none";\n'
            '    });\n'
            '    document.querySelectorAll(".tab-btn").forEach(function(b, i) {\n'
            '      b.classList.toggle("active", i === idx);\n'
            '    });\n'
            '    var gd = document.getElementById("graph-" + idx);\n'
            '    if (gd && gd.data) Plotly.Plots.resize(gd);\n'
            '  };\n'
            '\n'
            '  pagesData.forEach(function(figData, idx) {\n'
            '    var gd = document.getElementById("graph-" + idx);\n'
            '    var origAnn = JSON.parse(\n'
            '      JSON.stringify(figData.layout.annotations || []));\n'
            '\n'
            '    Plotly.newPlot(gd, figData.data, figData.layout,\n'
            '      {scrollZoom: false, displayModeBar: true});\n'
            '\n'
            '    var dualMode = false, cursorSel = "1";\n'
            '    var store = {"1": {}, "2": {}};\n'
            '    var tog = document.getElementById("toggle-" + idx);\n'
            '    var ctrl = document.getElementById("cc-" + idx);\n'
            '    var r1 = document.getElementById("r1-" + idx);\n'
            '    var r2 = document.getElementById("r2-" + idx);\n'
            '\n'
            '    tog.addEventListener("change", function() {\n'
            '      dualMode = tog.checked;\n'
            '      ctrl.style.display = dualMode ? "flex" : "none";\n'
            '      if (!dualMode) {\n'
            '        store = {"1": {}, "2": {}};\n'
            '        Plotly.relayout(gd, {shapes: [], annotations: origAnn});\n'
            '      }\n'
            '    });\n'
            '    r1.addEventListener("change",\n'
            '      function() { if (r1.checked) cursorSel = "1"; });\n'
            '    r2.addEventListener("change",\n'
            '      function() { if (r2.checked) cursorSel = "2"; });\n'
            '\n'
            '    gd.on("plotly_click", function(ev) {\n'
            '      if (!dualMode || !ev || !ev.points ||\n'
            '          !ev.points.length) return;\n'
            '      var pt = ev.points[0];\n'
            '      var xv = pt.x;\n'
            '      var tr = gd.data[pt.curveNumber];\n'
            '      var xa = tr.xaxis || "x";\n'
            '      var ya = tr.yaxis || "y";\n'
            '      store[cursorSel][xa] = {x: xv, y: pt.y, ya: ya};\n'
            '\n'
            '      var shapes = JSON.parse(\n'
            '        JSON.stringify(gd.layout.shapes || []));\n'
            '      var sn = "cursor_" + cursorSel + "_" + xa;\n'
            '      shapes = shapes.filter(\n'
            '        function(s) { return s.name !== sn; });\n'
            '      shapes.push({\n'
            '        type: "line", x0: xv, x1: xv, y0: 0, y1: 1,\n'
            '        xref: xa, yref: ya + " domain",\n'
            '        line: {color: cursorSel === "1" ? "red" : "blue",\n'
            '               width: 1.5, dash: "dash"},\n'
            '        name: sn\n'
            '      });\n'
            '\n'
            '      var axes = {};\n'
            '      ["1","2"].forEach(function(k) {\n'
            '        Object.keys(store[k]).forEach(\n'
            '          function(ax) { axes[ax] = 1; });\n'
            '      });\n'
            '      var anns = origAnn.slice();\n'
            '      Object.keys(axes).sort().forEach(function(ax) {\n'
            '        var yAx = null;\n'
            '        ["1","2"].forEach(function(k) {\n'
            '          if (!yAx && store[k][ax]) yAx = store[k][ax].ya;\n'
            '        });\n'
            '        if (!yAx) return;\n'
            '        var parts = [];\n'
            '        [["1","C1","red"],["2","C2","blue"]].forEach(function(a) {\n'
            '          var k=a[0], lb=a[1], cl=a[2];\n'
            '          if (store[k][ax]) {\n'
            '            var p = store[k][ax];\n'
            '            var ys = p.y != null\n'
            '              ? ", y=" + p.y.toFixed(4) : "";\n'
            '            parts.push("<span style=\\"color:" + cl + "\\">" +\n'
            '              lb + ": x=" + p.x.toFixed(4) + ys + "</span>");\n'
            '          }\n'
            '        });\n'
            '        if (store["1"][ax] && store["2"][ax]) {\n'
            '          var dx = Math.abs(\n'
            '            store["2"][ax].x - store["1"][ax].x);\n'
            '          parts.push("\u0394x=" + dx.toFixed(4));\n'
            '        }\n'
            '        if (parts.length) {\n'
            '          anns.push({\n'
            '            name: "cursor_info_" + ax,\n'
            '            text: parts.join("<br>"),\n'
            '            xref: ax + " domain", yref: yAx + " domain",\n'
            '            x: 0.01, y: 0.99,\n'
            '            xanchor: "left", yanchor: "top",\n'
            '            showarrow: false,\n'
            '            font: {size: 11, family: "monospace", color: "#333"},\n'
            '            bgcolor: "rgba(255,251,230,0.9)",\n'
            '            bordercolor: "#ccc", borderwidth: 1, borderpad: 4\n'
            '          });\n'
            '        }\n'
            '      });\n'
            '      Plotly.relayout(gd, {shapes: shapes, annotations: anns});\n'
            '    });\n'
            '  });\n'
            '  ' + init_tab + '\n'
            '})();\n'
        )

        css = (
            '* { box-sizing: border-box; }\n'
            'body { margin: 0; font-family: sans-serif; background: white; }\n'
            '.tab-bar { display: flex; border-bottom: 1px solid #ddd;'
            ' background: #f5f5f5; }\n'
            '.tab-btn { padding: 6px 16px; cursor: pointer; border: none;'
            ' border-top: 3px solid transparent;'
            ' background: none; font-size: 14px; }\n'
            '.tab-btn.active { font-weight: bold;'
            ' border-top: 3px solid #1f77b4; background: white; }\n'
            '.controls { display: flex; align-items: center; gap: 20px;'
            ' padding: 3px 12px; background: #f5f5f5;'
            ' border-bottom: 1px solid #ddd; font-size: 14px; }\n'
            'label { display: inline-flex; align-items: center;'
            ' gap: 4px; margin: 0; }\n'
        )

        return (
            '<!DOCTYPE html>\n'
            '<html>\n'
            '<head>\n'
            '  <meta charset="utf-8">\n'
            '  <title>Simulation Results</title>\n'
            '  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js">'
            '</script>\n'
            '  <style>\n' + css + '  </style>\n'
            '</head>\n'
            '<body>\n'
            + ('  ' + tab_bar if tab_bar else '')
            + pages_html + '\n'
            '  <script>\n' + script + '  </script>\n'
            + ('  <script>\n' + zoom_js + '\n  </script>\n' if zoom_js else '')
            + '</body>\n'
            '</html>\n'
        )

    def plot(self, suptitle="", dump_file_path=None, port=8050, debug=False):
        """
        Plots the simulation data using Plotly and Dash.

        Args:
            suptitle (str, optional): The title for the entire figure.
             Defaults to an empty string.
            dump_file_path (str, optional): Path to a dump file or directory
             containing dump files. If None, plots the current instance.
             Defaults to None.
            port (int, optional): Port number for the Dash server.
             Defaults to 8050.
            debug (bool, optional): Run Dash in debug mode.
             Defaults to False.
        """
        if dump_file_path is None:
            # Build a figure from any remaining assigned signals
            remaining_fig, remaining_shape = None, None
            if self.configuration.subplots_signals_list:
                if self.activate_dump:
                    self._dump_simulation_plotter()
                remaining_fig, remaining_shape = self._build_figure(suptitle)

            # Collect all pre_plot pages + the remaining figure
            all_pages = list(self._pre_plot_figures)
            if remaining_fig is not None:
                tab_label = (suptitle if suptitle
                             else f"Page {len(all_pages) + 1}")
                all_pages.append({
                    'label': tab_label,
                    'figure': remaining_fig,
                    'shape': remaining_shape,
                })

            if not all_pages:
                print("No subplots to show.")
                return

            # Use first page as the base fig/shape for backward compat
            fig = all_pages[0]['figure']
            shape = all_pages[0]['shape']

            self._save_and_open_html(fig, shape, file_name=suptitle,
                                     tab_figures=all_pages)
            return

        path = dump_file_path
        if os.path.isdir(path):
            npz_files = [os.path.join(path, f) for f in os.listdir(path)
                         if f.lower().endswith('.npz')]
            if not npz_files:
                print(f"No .npz files found in directory: {path}")
                return
            path = max(npz_files, key=os.path.getmtime)

        if not os.path.exists(path):
            alt = os.path.join(DUMP_FOLDER_PATH, path)
            if os.path.exists(alt):
                path = alt

        try:
            with np.load(path, allow_pickle=True) as npz:
                pickled = npz['simulation_plotter']
                if isinstance(pickled, np.ndarray):
                    pickled = pickled.item()
            loaded = pickle.loads(pickled)
        except Exception as e:
            print(f"Failed to load dump file '{path}': {e}")
            return

        if hasattr(loaded, 'plot') and callable(getattr(loaded, 'plot')):
            try:
                loaded.activate_dump = False
                loaded.plot(suptitle, port=port, debug=debug)
            except Exception as e:
                print(f"Failed to call plot() on loaded object: {e}")
            return

        if isinstance(loaded, dict):
            sp = SimulationPlotter(activate_dump=False)
            for k, v in loaded.items():
                try:
                    setattr(sp, k, v)
                except Exception:
                    pass
            try:
                sp.plot(suptitle, port=port, debug=debug)
            except Exception as e:
                print(
                    f"Failed to plot reconstructed SimulationPlotter: {e}")
            return

        print("Loaded dump does not contain a usable "
              "SimulationPlotter object.")
