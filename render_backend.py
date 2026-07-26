"""
render_backend — pluggable drawing backends for songformatter.

The song renderer in convertrawtext.py draws through a small canvas API (a subset
of reportlab's pdfgen canvas). This module lets the SAME drawing code target
different outputs:

  * PDF export  -> reportlab canvas (unchanged; used directly, not wrapped)
  * live preview -> TkCanvasBackend, drawing straight onto a Tk Canvas widget

The parallel-canvas preview replaces the old render-to-PDF-then-fitz-to-pixmap
path: one set of drawing calls, drawn to screen directly. Faster, no PyMuPDF
dependency, and point-precise (positions come from the same coordinates the PDF
uses; only glyph rasterization differs from a PDF viewer, which for the
non-embedded standard-14 fonts was never the printer's fonts anyway).

Coordinate model:
  PDF space is POINTS (1pt = 1/72"), origin bottom-left, y up. reportlab draws
  in points; a font "13" means 13pt.

  Tk renders point-based font sizes AND screen distances at `tk scaling` pixels
  per point (= display DPI / 72; ~1.333 at 96 DPI). So we keep fonts in POINTS
  (positive Tk size) and scale all GEOMETRY by the SAME pixels-per-point factor,
  so point coordinates and point fonts stay locked at physical size. A `zoom`
  factor multiplies both (scale the page up for legibility / down to fit).

  geometry: canvas_px = pt * (ppp * zoom)   [ppp = pixels-per-point]
  fonts:    tk_size   = -round(pt * ppp * zoom)   (negative = PIXELS)

  Fonts are sized in pixels, not points, because Tk font sizes must be integers
  ("expected integer but got 8.5"): a point size would be rounded first and then
  converted by Tk's own scaling, quantizing twice. At a fit-to-width zoom of
  0.655 that made 13pt text render as 9pt — 5.7% too large, so lines that fit in
  the PDF overflowed on screen. Sizing in pixels quantizes once, against a
  larger number, and scales with the geometry by construction.

  reportlab places a string by its BASELINE. Tk's create_text has no baseline
  anchor, so text is drawn with anchor="sw" (bottom of the line box, i.e. below
  the baseline by the font's descent) at baseline_y + descent pixels.

  Even at a pixel-exact size, Tk advances glyphs by whole hinted pixels, so a
  long string drifts a few percent from its PDF width. Strings are therefore
  placed word by word, each word at the x its PDF text metrics put it at, so
  line extents and chord/lyric alignment match the export instead of
  accumulating drift.

  (Fitting an oversized render down to the pane, with the attendant aliasing, is
  a separate display concern layered on top of `zoom`.)
"""

# A4 in points (matches reportlab.lib.pagesizes.A4)
PAGE_W = 595.0
PAGE_H = 842.0


def _rgb_to_hex(r, g, b):
    r = max(0, min(255, int(round(r * 255))))
    g = max(0, min(255, int(round(g * 255))))
    b = max(0, min(255, int(round(b * 255))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _color_to_hex(color):
    """Accept a reportlab color object (has .red/.green/.blue in 0..1)."""
    try:
        return _rgb_to_hex(color.red, color.green, color.blue)
    except AttributeError:
        # already a hex string or a name Tk understands
        return color


def pdf_string_width(text, font_name, size_pt):
    """Width of a string in POINTS per the PDF font metrics, or None.

    Uses reportlab's standard-14 metrics when available so the preview can place
    text at the same x positions the PDF export does. Returns None when no
    metrics source is present, in which case the caller falls back to Tk's own
    measurement.
    """
    try:
        from reportlab.pdfbase.pdfmetrics import stringWidth
    except ImportError:
        return None
    try:
        return stringWidth(text, font_name, size_pt)
    except Exception:
        return None


def _as_pil_image(img):
    """Coerce what the renderer passes to drawImage into a PIL image, or None.

    The song renderer hands over a PIL image, a reportlab ImageReader, or a
    filename, depending on the call site.
    """
    if img is None:
        return None
    if hasattr(img, "resize") and hasattr(img, "size"):
        return img                      # already a PIL image
    inner = getattr(img, "_image", None)  # reportlab ImageReader
    if inner is not None and hasattr(inner, "resize"):
        return inner
    try:
        from PIL import Image
    except ImportError:
        return None
    if isinstance(img, str):
        try:
            return Image.open(img)
        except Exception:
            return None
    # ImageReader without a cached PIL image: rebuild from its raw RGB data
    try:
        w, h = img.getSize()
        return Image.frombytes("RGB", (w, h), img.getRGBData())
    except Exception:
        return None


def _apply_color_key(img, mask):
    """Make pixels inside a reportlab colour-key mask transparent.

    reportlab's mask is [rmin, rmax, gmin, gmax, bmin, bmax] in 0..255.
    """
    if not mask or len(mask) < 6:
        return img
    try:
        rmin, rmax, gmin, gmax, bmin, bmax = [int(v) for v in mask[:6]]
    except (TypeError, ValueError):
        return img
    px = img.load()
    w, h = img.size
    for iy in range(h):
        for ix in range(w):
            r, g, b, a = px[ix, iy]
            if rmin <= r <= rmax and gmin <= g <= gmax and bmin <= b <= bmax:
                px[ix, iy] = (r, g, b, 0)
    return img


def _as_tk_photo(pil, w_px, h_px, mask=None):
    """Scaled PIL image -> Tk PhotoImage (PNG data, so alpha survives)."""
    try:
        from PIL import Image
        from io import BytesIO
        import base64
        import tkinter as tk
    except ImportError:
        return None
    try:
        img = pil.convert("RGBA").resize((w_px, h_px), Image.LANCZOS)
        img = _apply_color_key(img, mask)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
    except Exception:
        return None


def _map_font(name, size_pt, geo):
    """reportlab standard-14 font name -> Tk (family, size, *styles).

    size is in PIXELS (negative Tk size) = size_pt * geo, so glyphs scale
    exactly with the geometry and are quantized only once.
    """
    n = (name or "Helvetica")
    lower = n.lower()
    if lower.startswith("times"):
        family = "Times"
    elif lower.startswith("courier"):
        family = "Courier"
    elif lower.startswith("symbol") or lower.startswith("zapf"):
        family = "Helvetica"  # no metric-compatible Tk face; fall back
    else:
        family = "Helvetica"
    styles = []
    if "bold" in lower:
        styles.append("bold")
    if "oblique" in lower or "italic" in lower:
        styles.append("italic")
    px = max(1, int(round(size_pt * geo)))  # NEGATIVE = pixels
    return (family, -px, *styles)


class TkCanvasBackend:
    """Draws the song via the reportlab-canvas subset onto a Tk Canvas.

    Implements exactly the methods convertrawtext.py calls on the canvas:
      setFont, drawString, beginText/drawText (+ text-object textLine/setFont/
      setTextOrigin), line, circle, rect, setStrokeColorRGB, setStrokeColor,
      setFillColorRGB, setFillColor, setLineWidth, setBlendMode, drawImage,
      showPage, save.
    """

    def __init__(self, tk_canvas, page_w=PAGE_W, page_h=PAGE_H, zoom=1.0,
                 page_gap=20.0, fit_width_px=None, max_zoom=2.0):
        self.cv = tk_canvas
        self.page_w = page_w
        self.page_h = page_h
        # pixels per point Tk uses for point-fonts & distances (display DPI / 72)
        try:
            self.ppp = float(tk_canvas.tk.call("tk", "scaling"))
        except Exception:
            self.ppp = 96.0 / 72.0
        if fit_width_px:
            # scale the physical page so its full width fits the given pixel width
            zoom = min(max_zoom, float(fit_width_px) / (page_w * self.ppp))
        self.zoom = max(0.05, zoom)
        self.geo = self.ppp * self.zoom  # canvas pixels per PDF point (GEOMETRY)
        self.page_gap = page_gap
        self.page_index = 0
        self._descents = {}  # font tuple -> descent in canvas pixels
        self._images = []    # PhotoImages, kept alive while they're on the canvas
        # drawing state
        self._fill = "#000000"
        self._stroke = "#000000"
        self._linewidth = 1.0
        self._pdf_font = ("Helvetica", 13.0)
        self._font = _map_font("Helvetica", 13, self.geo)

    # --- coordinate transform (PDF pt, y-up bottom-left -> Tk px, y-down) ---
    def _x(self, x):
        return x * self.geo

    def _y(self, y):
        page_top = self.page_index * (self.page_h + self.page_gap)
        return (page_top + (self.page_h - y)) * self.geo

    def _w(self, w):
        return max(1, w * self.geo)  # a point-width in canvas pixels, >=1

    def _descent(self, font):
        """Descent of a Tk font in canvas pixels (cached)."""
        d = self._descents.get(font)
        if d is None:
            import tkinter.font as tkfont
            try:
                d = tkfont.Font(root=self.cv, font=font).metrics("descent")
            except Exception:
                d = 0
            self._descents[font] = d
        return d

    def _text(self, x, y, text, font, pdf_font):
        """Place a string whose PDF BASELINE is at (x, y).

        Each space-separated word is positioned at the x its PDF metrics give it,
        so Tk's whole-pixel glyph advances can't accumulate across a line.
        """
        py = self._y(y) + self._descent(font)
        if not text:
            return
        name, size_pt = pdf_font
        words = text.split(" ")
        if len(words) < 2 or pdf_string_width(text, name, size_pt) is None:
            self.cv.create_text(self._x(x), py, text=text, anchor="sw",
                                fill=self._fill, font=font)
            return
        prefix = ""
        for word in words:
            if word:
                dx = pdf_string_width(prefix, name, size_pt) or 0.0
                self.cv.create_text(self._x(x + dx), py, text=word, anchor="sw",
                                    fill=self._fill, font=font)
            prefix = prefix + word + " "

    # --- state ---
    def setFont(self, name, size):
        self._pdf_font = (name, size)
        self._font = _map_font(name, size, self.geo)

    def setFillColorRGB(self, r, g, b):
        self._fill = _rgb_to_hex(r, g, b)

    def setFillColor(self, color):
        self._fill = _color_to_hex(color)

    def setStrokeColorRGB(self, r, g, b):
        self._stroke = _rgb_to_hex(r, g, b)

    def setStrokeColor(self, color):
        self._stroke = _color_to_hex(color)

    def setLineWidth(self, w):
        self._linewidth = w

    def setBlendMode(self, mode):
        pass  # not modelled on screen

    # reportlab exposes canvas.blendmode as an attribute namespace; harmless stub
    class _BlendModes:
        NORMAL = "Normal"
        MULTIPLY = "Multiply"
    blendmode = _BlendModes()

    # --- text ---
    def drawString(self, x, y, text):
        self._text(x, y, text, self._font, self._pdf_font)

    def beginText(self, x=0, y=0):
        return _TkTextObject(self, x, y)

    def drawText(self, textobj):
        textobj._flush()

    def endText(self):
        pass

    # --- vector primitives ---
    def line(self, x1, y1, x2, y2):
        self.cv.create_line(self._x(x1), self._y(y1), self._x(x2), self._y(y2),
                            fill=self._stroke, width=self._w(self._linewidth))

    def circle(self, x, y, r, fill=False, stroke=True):
        cx, cy, rr = self._x(x), self._y(y), r * self.geo
        self.cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                            fill=(self._fill if fill else ""),
                            outline=(self._stroke if stroke else ""),
                            width=self._w(self._linewidth))

    def rect(self, x, y, w, h, fill=False, stroke=True):
        # reportlab rect: (x,y) lower-left, width w, height h (h may be negative)
        x1, y1 = self._x(x), self._y(y)
        x2, y2 = self._x(x + w), self._y(y + h)
        self.cv.create_rectangle(x1, y1, x2, y2,
                                fill=(self._fill if fill else ""),
                                outline=(self._stroke if stroke else ""),
                                width=self._w(self._linewidth))

    # --- images ---
    def drawImage(self, img, x, y, width=0, height=0, mask=None, **kw):
        """reportlab drawImage: (x, y) is the LOWER-LEFT corner, size in points.

        The image is resized to its on-screen pixel size and handed to Tk as a
        PNG, which preserves alpha (both the background image's own transparency
        and a reportlab colour-key `mask`). Silently skipped when no imaging
        support is available — an absent background is better than a dead preview.
        """
        pil = _as_pil_image(img)
        if pil is None:
            return
        if not width:
            width = pil.size[0]
        if not height:
            height = pil.size[1]
        w_px = max(1, int(round(width * self.geo)))
        h_px = max(1, int(round(height * self.geo)))
        photo = _as_tk_photo(pil, w_px, h_px, mask)
        if photo is None:
            return
        # keep a reference: Tk drops the pixels when the PhotoImage is collected
        self._images.append(photo)
        self.cv.create_image(self._x(x), self._y(y), image=photo, anchor="sw")

    # --- page / lifecycle ---
    def showPage(self):
        self.page_index += 1

    def save(self):
        # finalize: size the scroll region to all stacked pages
        total_h = (self.page_index + 1) * (self.page_h + self.page_gap)
        x0, y0 = 0.0, 0.0
        x1, y1 = self.page_w * self.geo, total_h * self.geo
        try:
            # preview-only annotations may sit above the page top (negative y);
            # union the item bbox in so they stay reachable by scrolling
            # (x is left at the page width: an over-long annotation line runs off
            # the page in the PDF too, and widening the region would defeat the
            # fit-to-width scaling.)
            bbox = self.cv.bbox("all")
            if bbox:
                y0 = min(y0, bbox[1])
                y1 = max(y1, bbox[3])
            self.cv.configure(scrollregion=(x0, y0, x1, y1))
        except Exception:
            pass


class _TkTextObject:
    """Mimics reportlab's text object (beginText/textLine/drawText)."""

    def __init__(self, backend, x, y):
        self.b = backend
        self.x = x
        self.y = y
        self.font = backend._font
        self.pdf_font = backend._pdf_font
        self.lines = []  # (x, y, text, font, pdf_font)
        self.leading = None

    def setFont(self, name, size, leading=None):
        self.pdf_font = (name, size)
        self.font = _map_font(name, size, self.b.geo)
        self.leading = (leading if leading is not None else size)

    def setTextOrigin(self, x, y):
        self.x, self.y = x, y

    def setLeading(self, leading):
        self.leading = leading

    def textLine(self, text=""):
        lead = self.leading if self.leading is not None else 14
        self.lines.append((self.x, self.y, text, self.font, self.pdf_font))
        self.y -= lead  # PDF points; successive lines move down (y decreases)

    def textOut(self, text=""):
        self.lines.append((self.x, self.y, text, self.font, self.pdf_font))

    def _flush(self):
        for (x, y, text, font, pdf_font) in self.lines:
            self.b._text(x, y, text, font, pdf_font)
        self.lines = []
