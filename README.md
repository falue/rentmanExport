# EXPORT DATA FROM RENTMAN

Because rentman does not allow to export your equipment data in a smart way, this script exports them smart as `json`, `md` and `PDF`. 

Specifically, the export formats provided .xls and .csv are missing one important aspect: The Files associated with an equipment (Images, PDFs).

The categories with which any equipment is associated is also added to the output.

The images are saved in best possible quality.

You'll need a JWT_TOKEN, accessible via rentman interface (Configuration > Extensions > API > Connect and then Show Token).
Put the token in a File named "JWT_TOKEN" (without file extension), put it in the same folder as the python script.

## Test your connection to rentman
```
python3 checkAuth.py
```
will output `API call successful, yeah!` if it worked, `API call failed.` and some details about why if not.

## Use it
```
python3 collectEverything.py
```

## Output
This script saves all your equipments and files in a folder named "equipmentDump".
Therein will be created a fodler named like this:

```
itemCode_itemQrcodes_equipment_name
```

*Notice* that the folder name does not include the `ID` of the item, as this is pretty much unusable for search in the rentman frontend.

Additional files will be created within that folder. An example output:
```
equipmentDump/
    _archived/
    33_10000666_Wardrobe - red/
        data.md
        data.json
        78374rm4_photo-1.jpg
        78374rm4_photo-2.jpg
        78374rm4_photo-3.jpg
        78374rm4_photo-4.jpg
        78374rm4_photo-5.jpg
        78374rm4_photo-6.jpg
        33_10000666_Wardrobe - red.pdf
    34_10000789_Wardrobe - blue/
    35_10000963_Hat stand/
```

- The `data.json` contains all the data in a computer-friendly way for further programming and shenanigans.
- The `data.md` contains all the data in a human readable and editable way.
- and the `PDF` contains contains all the data in a human readable and non-editable way.

Also, an "equipmentDump/_archived" is created which contains all archived equipments.

*Notice*: The speed is slowed to 10 calls a second to not trigger the safety feature by rentman API ("Not more than 20 calls / second"). So it takes a while to export everything.

## Caveats
- After querying 300 equipments its cut off, needs work for that <https://api.rentman.net/#section/Introduction/Response-data-limitation>
- "Tasks", "Notes" are not downloaded
- Label-PDFs associated with equipment is removed from the download. You can change that if you need!
- File PDFs are potentially not downloaded
- Cannot be imported again to rentman
- It is not saved which Image is the main image
- "Custom fields" are not queryable, you'll need to change the list in the code to your liking if you want to output them properly.

## Prerequisite for PDF conversion:
  `brew install basictex`

  `brew install pandoc`