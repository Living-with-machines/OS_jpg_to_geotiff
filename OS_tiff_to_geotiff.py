# gdal must match system gdal
# gdainfo --version
# pip install gdal==2.4
#  It seems to work with gdal 3.2.2 (most recent one, pip install gdal==3.2.2)
#  If it is necessary to run another version, example, GDAL 2.4, Python 3.8, Windows x64
#   1) Download the wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal -- GDAL-2.4.1-cp38-cp38-win_amd64.whl
#   2) python -m pip install c:\temp\GDAL-2.4.1-cp38-cp38-win_amd64.whl --user
from osgeo import gdal, osr
import shutil
import os
import json
import pdb
import datetime
import glob
import pathlib
import time

from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter import ttk

# pip install pillow
from PIL import Image, ImageTk, ImageDraw


# bypass error: "PIL.Image.DecompressionBombError: Image size (211225084 pixels) exceeds limit of 178956970 pixels, could be decompression bomb DOS attack."
Image.MAX_IMAGE_PIXELS = None

current_date_and_time_string = time.strftime("%Y-%m-%d_%H-%M")

report_completed = open(
    "report_completed_" + current_date_and_time_string + ".txt", "a"
)
report_not_completed = open(
    "report_not_completed_" + current_date_and_time_string + ".txt", "a"
)


def createDir(path):
    if not os.path.exists(path):
        os.makedirs(path)


# createDir('./OS_gcps/')
# createDir('./OS_tiffs_gcps/')
createDir("./OS_geotiffs/")
createDir("./OS_tiffs_cut/")

# Extract the map area
def extractMap(path):
    event2canvas = lambda e, c: (c.canvasx(e.x), c.canvasy(e.y))
    if __name__ == "__main__":
        root = Tk()
        root.attributes("-fullscreen", True)  # make main window full-screen

        # setting up a tkinter canvas with scrollbars
        frame = Frame(root, width=1850, height=980, bd=2, relief=SUNKEN)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        xscroll = Scrollbar(frame, orient=HORIZONTAL)
        xscroll.grid(row=1, column=0, sticky=E + W)
        yscroll = Scrollbar(frame)
        yscroll.grid(row=0, column=1, sticky=N + S)
        canvas = Canvas(
            frame,
            bd=0,
            width=1850,
            height=980,
            xscrollcommand=xscroll.set,
            yscrollcommand=yscroll.set,
        )

        canvas.grid(row=0, column=0, sticky=N + S + E + W)
        xscroll.config(command=canvas.xview)
        yscroll.config(command=canvas.yview)
        frame.pack(fill=BOTH, expand=True)

        # adding the image
        # File = askopenfilename(parent=root, initialdir="./",title='Choose an image.')
        # print("opening %s" % File)
        print("Opening the image...")
        img = Image.open("./OS_tiffs/" + path)
        imgTk = ImageTk.PhotoImage(img)
        canvas.create_image(
            0, 0, image=imgTk, anchor="nw"
        )  # won't work if anchor is not "nw" -- it will produce a null image -- we need it to be sw (1st point)
        canvas.config(scrollregion=canvas.bbox(ALL))

        global corners_pixels
        corners_pixels = []

        # function to be called when mouse is clicked
        def printcoords(event):
            # outputting x and y coords to console
            cx, cy = event2canvas(event, canvas)
            # print ("(%d, %d) / (%d, %d)" % (event.x,event.y,cx,cy))
            if [cx, cy] not in corners_pixels:
                # print(len(corners_pixels))
                corners_pixels.append([cx, cy])
                # Python 3.8 doesn't support match-case, only 3.10+
                # Fixing the issue with the wrong coordinates: we should one jump to the next corner AFTER storing the value of the current one :) -- what it does the line above.
                if len(corners_pixels) == 1:
                    canvas.yview_moveto("0.035")
                elif len(corners_pixels) == 2:
                    canvas.xview_moveto("0.895")
                elif len(corners_pixels) == 3:
                    canvas.yview_moveto("0.88")
                if len(corners_pixels) > 3:
                    # Cut map from image border
                    mask = Image.new("L", img.size, color=0)
                    draw = ImageDraw.Draw(mask)

                    points = tuple(tuple(sub) for sub in corners_pixels)
                    draw.polygon((points), fill=255)
                    img.putalpha(mask)

                    rgb = Image.new("RGB", img.size, (255, 255, 255))
                    rgb.paste(img, mask=img.split()[3])
                    directory = (
                        "./OS_tiffs_cut/" + str(os.path.dirname(path)) + "/"
                    )
                    createDir(directory)
                    rgb.save(
                        "./OS_tiffs_cut/" + path, "TIFF", resolution=100.0
                    )
                    root.destroy()

    # we need it to be sw (1st point), not nw
    canvas.xview_moveto("0.04")
    canvas.yview_moveto("0.88")

    # mouseclick event
    canvas.bind("<ButtonPress-1>", printcoords)
    # canvas.bind("<ButtonRelease-1>",printcoords)
    ttk.Button(frame, text="Quit", command=root.destroy).grid(column=0, row=0)
    root.mainloop()


OS_coords = json.load(open("./25_inch_GB_geojson.json"))


def createCornerLatLng(sheet_r, county):
    corners = []

    for f in OS_coords["features"]:
        if (
            f["properties"]["SHEET_NO"] == sheet_r
            and f["properties"]["COUNTY"].lower() == county.lower()
        ):
            coords = f["geometry"]["coordinates"][0][0]
            # print(coords)

            # break

            # TODO Sort corners_pixels
            corners = [
                # {'location': [corners_latLng['x_west_edge'], corners_latLng['y_north_edge']], 'pixel': corners_pixels[0]},
                {"location": coords[0], "pixel": corners_pixels[0]},
                {"location": coords[1], "pixel": corners_pixels[1]},
                {"location": coords[2], "pixel": corners_pixels[2]},
                {"location": coords[3], "pixel": corners_pixels[3]},
            ]
            # print(corners)

            # TODO Save corners

    return corners


def createGcps(coords):
    gcps = []
    for coord in coords:
        # 'coord' = {'location': [-3.756732387660781, 50.57983418053561], 'pixel': [2164, 966]}
        col = coord["pixel"][0]
        row = coord["pixel"][1]
        x = coord["location"][0]
        y = coord["location"][1]
        z = 0
        gcp = gdal.GCP(x, y, z, col, row)
        gcps.append(gcp)

    return gcps


# # https://stackoverflow.com/questions/55681995/how-to-georeference-an-unreferenced-aerial-imgage-using-ground-control-points-in
def addGcps(path, gcps):
    src = "./OS_tiffs_cut/" + path
    # createDir('./OS_tiffs_gcps/' + os.path.dirname(path))
    # dst = './OS_tiffs_gcps/'+path
    # Create a copy of the original file and save it as the output filename:
    # shutil.copy(src, dst)
    # Open the output file for writing for writing:
    ds = gdal.Open(src, gdal.GA_Update)
    # Set spatial reference:
    sr = osr.SpatialReference()

    # WGS84 sr.ImportFromEPSG(4326)
    sr.SetWellKnownGeogCS("CRS84")
    # sr.ImportFromEPSG(3857)

    # Apply the GCPs to the open output file:
    ds.SetGCPs(gcps, sr.ExportToWkt())

    # Close the output file in order to be able to work with it in other programs:
    ds = None


def createGeoTiff(path):
    # src = './OS_tiffs_gcps/' + path
    src = "./OS_tiffs_cut/" + path
    createDir("./OS_geotiffs/" + os.path.dirname(path))
    dst = "./OS_geotiffs/" + path
    input_raster = gdal.Open(src)
    # WGS 84 gdal.Warp(dst,input_raster,dstSRS='EPSG:4326',dstNodata=255)
    gdal.Warp(dst, input_raster, dstSRS="EPSG:3857", dstNodata=255)


tiffpaths = []

for filepath in pathlib.Path("./OS_tiffs/").glob("**/*.tif"):
    basename = os.path.basename(filepath)
    dirname = os.path.dirname(filepath).partition("OS_tiffs")[2]
    tiffpaths.append([dirname, basename])

for tiff in tiffpaths:
    file = tiff[1]
    path = tiff[0] + "/" + tiff[1]

    if not path.startswith("."):
        print(path)
        # sheet_ref = path.replace('OS_Yorkshire_25_001_', '').replace('.tif', '')
        series = file.split("_")[2]
        edition = file.split("_")[3].lstrip("0")
        county = file.split("_")[1]
        if (len(file.split("_"))) == 7:  # if it has the Parish in the filename
            sheet_no = [(x.split(".")[0]) for x in file.split("_")[5:]]
        else:
            sheet_no = [(x.split(".")[0]) for x in file.split("_")[4:]]
        if len(sheet_no) == 2:
            sheet_no = (
                str(sheet_no[0]).zfill(3) + "_" + str(sheet_no[1]).zfill(2)
            )
        else:
            sheet_no = "_".join(sheet_no)
        sheet_ref = sheet_no
        print(sheet_ref)
        match = False
        for f in OS_coords["features"]:
            if (
                f["properties"]["SHEET_NO"] == sheet_ref
                and f["properties"]["COUNTY"].lower() == county.lower()
            ):
                extractMap(path)
                corners = createCornerLatLng(sheet_ref, county)
                gcps = createGcps(corners)
                addGcps(path, gcps)
                print("... createGeoTiff")
                createGeoTiff(path)
                report_completed.write(path + "\n")
                match = True
                # Delete the source [these are local copies, right? -- if not, comment the first line bellow] and temp files
                os.remove("./OS_tiffs/" + path)
                # os.remove('./OS_tiffs_gcps/'+ path)
                os.remove("./OS_tiffs_cut/" + path)
                break

        if match == False:
            report_not_completed.write(path + "\n")


# shutil.rmtree('./OS_tiffs_gcps/')
# shutil.rmtree('./OS_gcps/')
shutil.rmtree("./OS_tiffs_cut/")
