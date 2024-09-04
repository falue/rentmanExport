# EXPORT DATA FROM RENTMAN

Because rentman does not allow to export your equipment data in a smart way, this script exports them smart as `json`, `md` and `PDF` to save locally or use it in your own frontend. 

Specifically, the export formats provided by rentman frontend is .xls and .csv - those are missing one important aspect: The Files associated with an equipment (Images, PDFs, additional files).

The categories with which any equipment is associated is also added to the output.

The images are saved in best possible quality.

You'll need a JWT_TOKEN, accessible via rentman interface (Configuration > Extensions > API > Connect and then Show Token).
Put the token in a File named `JWT_TOKEN` (without file extension), put it in the same folder as the python script.

> ⚠️ ***By default this script only outputs the first 10 objects in your equipment collection.***
If you want to export more or everything change line `18` in `collectEverything.py` appropriately.

## Test your connection to rentman
```
python3 checkAuth.py
```
will output `API call successful, yeah!` if it worked, or `API call failed` and some details about why.

## Use it
For exporting everything:
```
python3 collectEverything.py
```

For exporting 10 articles, starting from article nr. 30:
```
python3 collectEverything.py --start 30 --num 10
```

For exporting one specific article, use arg `id`:
```
python3 collectEverything.py --id 200
```
This exports only the article with "Code" 200 ("Code" is what rentman calls their unique identifier).

## Output
This script saves all your equipment and their files in a folder named "equipmentDump".
In there, for each piece of equipment will be a folder  created, named like this:

```
code_qrcodes_equipment name
```
eg.
```
33_10000666_Wardrobe - red
```
Its name is the "code" and the "qrcode" combined with the hjuman readable title with umlaute and spaces. So don't name equipment with file system conflicting characters (i.e. don't use `&`, `/` or `'`)

> 📝 *Notice*: that the folder name does not include the `ID` of the item, as this is pretty much unusable for search in the rentman frontend and only used internally by them.

Additional files will be created within that folder. An example output:
```
equipmentDump/
    _archived/
    33_10000666_Wardrobe - red/
        data.md
        data.json
        33_10000666_Wardrobe - red.pdf
        78374rm4_photo-1.jpg
        78374rm4_photo-2.jpg
        78374rm4_photo-3.jpg
        78374rm4_photo-4.jpg
        78374rm4_photo-5.jpg
        78374rm4_photo-6.jpg
    34_10000789_Wardrobe - blue/
    35_10000963_Hat stand ugly/
```

- The `data.json` contains all the data in a computer-friendly way for further programming and shenanigans. This includes, additionally to the rentman specs, data about all the images/files associated with the euqipment as well as a human readable category-path.
- The `data.md` contains all the data in a human readable and editable way.
- The `PDF` contains all the data in a human readable, printable and non-editable way. Also includes a link to the original file location stored on an amazonS3 server by rentman.

Also, an "equipmentDump/_archived" is created which contains all archived equipment.

> 📝 *Notice*: The speed is slowed to 10 calls a second to not trigger the safety feature by rentman API ("Not more than 20 calls / second"). So it takes a while to export everything.

## Caveats
- After querying 300 equipment its cut off, needs work for that <https://api.rentman.net/#section/Introduction/Response-data-limitation>
- "Tasks", "Notes" are not downloaded
- Label-PDFs associated with equipment is removed from the download. You can change that if you need!
- Cannot be imported again to rentman
- It is not saved which Image is the main image
- No special treatment for "sets" of other equipment
- "Custom fields" are not queryable, you'll need to change the list in the code to your liking if you want to output them properly.

## Prerequisite for PDF conversion:
  `brew install basictex`

  `brew install pandoc`