import types
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk
import xdot.ui
from preciceconfigvisualizer.common import configFileToDotCode
import cairo
from math import ceil

PRECICE_SUPPORT_URI = "https://precice.org/community-support-precice.html"

def makeVisibilityCombobox(callback, withMerged = True):
    cb = Gtk.ComboBoxText()
    cb.append_text("Show")
    if withMerged:
        cb.append_text("Merge")
    cb.append_text("Hide")
    cb.set_active(0)
    cb.connect("changed", callback)
    return cb


def set_active_by_value(combobox, value):
    model = combobox.get_model()
    for index, row in enumerate(model):
        if row[0] == value:
            combobox.set_active(index)
            return
    assert false


class ConfigVisualizerWindow(Gtk.Window):

    def __init__(self, filename=None):
        self._filename = filename;
        super().__init__(title="preCICE config visualizer")
        self.set_default_size(700, 700)

        # Main dot widget created here to connect signals
        self.dotwidget = xdot.ui.DotWidget()

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)


        # Toolbar

        self.top = Gtk.Box(spacing=4)
        self.box.pack_start(self.top, False, False, 2)

        self.toolbar = Gtk.Toolbar()
        self.tool_open=Gtk.ToolButton(stock_id=Gtk.STOCK_OPEN)
        self.tool_open.set_tooltip_text("Open a configuration")
        self.tool_open.connect("clicked", self.on_open)
        self.tool_save=Gtk.ToolButton(stock_id=Gtk.STOCK_SAVE_AS)
        self.tool_save.set_tooltip_text("Save as")
        self.tool_save.connect("clicked", self.on_export)
        self.tool_copy=Gtk.ToolButton(stock_id=Gtk.STOCK_COPY)
        self.tool_copy.set_tooltip_text("Copy as image to clipboard")
        self.tool_copy.connect("clicked", self.on_copy)
        self.tool_refresh=Gtk.ToggleToolButton(stock_id=Gtk.STOCK_REFRESH, active=True)
        self.tool_refresh.set_tooltip_text("Reload on file-change")
        self.tool_refresh.connect("clicked", self.on_toogle_refresh)
        self.tool_copy_path=Gtk.ToolButton(stock_id=Gtk.STOCK_INFO)
        self.tool_copy_path.set_tooltip_text("Copy file path to clipboard")
        self.tool_copy_path.connect("clicked", self.on_copy_path)

        self.tool_zoom_in=Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_IN)
        self.tool_zoom_in.set_tooltip_text("Zoom in")
        self.tool_zoom_in.connect("clicked", self.dotwidget.on_zoom_in)
        self.tool_zoom_out=Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_OUT)
        self.tool_zoom_out.set_tooltip_text("Zoom out")
        self.tool_zoom_out.connect("clicked", self.dotwidget.on_zoom_out)
        self.tool_zoom_fit=Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_FIT)
        self.tool_zoom_fit.set_tooltip_text("Zoom to fit window")
        self.tool_zoom_fit.connect("clicked", self.dotwidget.on_zoom_fit)
        self.tool_zoom_100=Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_100)
        self.tool_zoom_100.set_tooltip_text("Zoom to 100%")
        self.tool_zoom_100.connect("clicked", self.dotwidget.on_zoom_100)

        self.toolbar.insert(self.tool_open, -1)
        self.toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.toolbar.insert(self.tool_save, -1)
        self.toolbar.insert(self.tool_copy, -1)
        self.toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.toolbar.insert(self.tool_refresh, -1)
        self.toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.toolbar.insert(self.tool_copy_path, -1)
        self.toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.toolbar.insert(self.tool_zoom_in, -1)
        self.toolbar.insert(self.tool_zoom_out, -1)
        self.toolbar.insert(self.tool_zoom_fit, -1)
        self.toolbar.insert(self.tool_zoom_100, -1)
        self.top.pack_start(self.toolbar, False, False, 2)

        promotion = Gtk.LinkButton.new_with_label(PRECICE_SUPPORT_URI, "Support preCICE")
        self.top.pack_end(promotion, False, False, 2)

        # Settings row

        self.settings = Gtk.Box(spacing=4)
        self.box.pack_start(self.settings, False, False, 0)

        self.dotwidget.connect("error", self.on_dot_error)
        self.box.pack_start(self.dotwidget, True, True, 0)

        self.error_bar = Gtk.Label()
        self.box.pack_start(self.error_bar, False, False, 0)

        # Presets
        presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        presets.pack_start(Gtk.Label(), True, True, 0)
        for label in ("All", "Dataflow", "Coupling"):
            button = Gtk.Button.new_with_label(label)
            button.connect("clicked", self.on_preset, label)
            presets.pack_start(button, True, True, 0)

        # Settings
        self.data_access = makeVisibilityCombobox(self.on_option_change)
        self.data_exchange = makeVisibilityCombobox(self.on_option_change)
        self.communicators = makeVisibilityCombobox(self.on_option_change)
        self.cplschemes = makeVisibilityCombobox(self.on_option_change)
        self.mappings = makeVisibilityCombobox(self.on_option_change)

        self.margin = Gtk.SpinButton.new_with_range(8, 100, 2)
        self.margin.connect("changed", self.on_option_change)

        # TODO add toogles
        #self.watchpoints = makeVisibilityCombobox(self.on_option_change,False);
        #self.exporters = makeVisibilityCombobox(self.on_option_change,False);

        optionsRow = [
            Gtk.Label(),
            Gtk.Label(label="Presets"),
            presets,
            Gtk.Separator(),
            Gtk.Label(label="Data access"),
            self.data_access,
            Gtk.Separator(),
            Gtk.Label(label="Data exchange"),
            self.data_exchange,
            Gtk.Separator(),
            Gtk.Label(label="Communicators"),
            self.communicators,
            Gtk.Separator(),
            Gtk.Label(label="Couplig schemes"),
            self.cplschemes,
            Gtk.Separator(),
            Gtk.Label(label="Mappings"),
            self.mappings,
            Gtk.Separator(),
            Gtk.Label(label="Margin"),
            self.margin,
            #Gtk.Separator(),
            #Gtk.Label(label="Watchpoints"),
            #self.watchpoints,
            #Gtk.Separator(),
            #Gtk.Label(label="Exporters"),
            #self.exporters,
            Gtk.Label(),
        ]
        for x in optionsRow:
            self.settings.pack_start(x, False, False, 2)

        self.show_all()
        self.reload()
        self.monitor()

    def on_file_change(self, m, f, o, event):
        if self.tool_refresh.get_active() and event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.reload()

    def monitor(self):
        # No filename given?
        if self._filename is None:
            self._monitor = None
            return

        file = Gio.File.new_for_path(self._filename)
        self._monitor = file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self.on_file_change)


    def reload(self):
        if self._filename is None:
            self.error_bar.set_visible(False)
            self.dotcode = ""
            self.dotwidget.set_dotcode(b"")
            return

        def getVisibilty(cb):
            return {
                "Show" : 'full',
                "Merge": 'merged',
                "Hide": 'hide',
            }[cb.get_active_text()]

        args = types.SimpleNamespace(
            data_access=getVisibilty(self.data_access),
            data_exchange=getVisibilty(self.data_exchange),
            communicators=getVisibilty(self.communicators),
            cplschemes=getVisibilty(self.cplschemes),
            mappings=getVisibilty(self.mappings),
            no_watchpoints=False,
            no_colors=False,
            margin=self.margin.get_value(),
        )

        dot = configFileToDotCode(self._filename, args)
        self.error_bar.set_visible(False)
        self.dotcode = dot.encode()
        self.dotwidget.set_dotcode(dot.encode())

    def on_open(self, caller):
        dialog = Gtk.FileChooserDialog(
            title="Choose preCICE configuration",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK)

        filter = Gtk.FileFilter()
        filter.set_name("XML files")
        filter.add_mime_type("text/xml")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self._filename = dialog.get_filename()
            self.reload()
            self.monitor()
        dialog.destroy()

    def on_copy(self, caller):
        width, height = map(ceil, self.dotwidget.graph.get_size())
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        self.dotwidget.graph.draw(ctx)
        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_image(pixbuf)
        clipboard.store()

    def on_copy_path(self, caller):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self._filename, -1)
        clipboard.store()

    def on_export(self, caller):
        dialog = Gtk.FileChooserDialog(
            "Export as",
            None,
            Gtk.FileChooserAction.SAVE,
            (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
        )

        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG images")
        png_filter.add_mime_type("image/png")
        dialog.add_filter(png_filter)
        dot_filter = Gtk.FileFilter()
        dot_filter.set_name("DOT graphs")
        dot_filter.add_mime_type("text/vnd.graphviz")
        dot_filter.add_pattern("*.gv")
        dot_filter.add_pattern("*.dot")
        dialog.add_filter(dot_filter)

        response = dialog.run()
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
        else:
            filename = dialog.get_filename()
            selection = dialog.get_filter()
            dialog.destroy()

            if selection == png_filter:
                self.export_png(filename)
            elif selection == dot_filter:
                self.export_dot(filename)
            else:
                print("Unknown export type")

    def export_png(self, filename):
        width, height = map(ceil, self.dotwidget.graph.get_size())
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        self.dotwidget.graph.draw(ctx)
        surface.write_to_png(filename)

    def export_dot(self, filename):
        with open(filename, "wb") as f:
            f.write(self.dotcode)

    def on_toogle_refresh(self, caller):
        if self.tool_refresh.get_active():
            self.reload()

    def on_option_change(self, caller):
        self.reload()

    def on_preset(self, caller, label):
        if label == "All":
            set_active_by_value(self.data_access, "Show")
            set_active_by_value(self.data_exchange, "Show")
            set_active_by_value(self.communicators, "Show")
            set_active_by_value(self.cplschemes, "Show")
            set_active_by_value(self.mappings, "Show")
        elif label == "Dataflow":
            set_active_by_value(self.data_access, "Show")
            set_active_by_value(self.data_exchange, "Show")
            set_active_by_value(self.communicators, "Hide")
            set_active_by_value(self.cplschemes, "Hide")
            set_active_by_value(self.mappings, "Show")
        elif label == "Coupling":
            set_active_by_value(self.data_access, "Merge")
            set_active_by_value(self.data_exchange, "Merge")
            set_active_by_value(self.communicators, "Hide")
            set_active_by_value(self.cplschemes, "Show")
            set_active_by_value(self.mappings, "Merge")

    def on_dot_error(self, caller, message):
        self.error_bar.set_visible(True)
        self.error_bar.set_label(f"Error: {message}")
