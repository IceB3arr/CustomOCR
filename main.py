import pymysql
import os
import shutil
import re
from PIL import Image, ImageFilter
api_key = 'K87966375588957' #K83437119188957    K87966375588957 real

api_url = 'https://api.ocr.space/parse/image'
def clamp(var, min_val, max_val):
    return max(min_val, min(var, max_val))


def filterImage(image, width, height, threshold_font_color, threshold=8, ):
    filter_matrix = [[0 for _ in range(height)] for _ in range(width)]

    for x in range(width):
        for y in range(height):
            min_x = clamp(x - threshold, 0, width - 1)
            max_x = clamp(x + threshold, 0, width - 1)
            filter_matrix[x][y] = 1
            for new_x in range(min_x, max_x + 1):
                value = image.getpixel((new_x, y))[0]
                if value < threshold_font_color:
                    filter_matrix[x][y] = 0
    return filter_matrix



def histogram(matrix, width, height):
    hcolumn = [0] * width
    hrow = [0] * height

    for column in range(width):
        count = 0
        for row in range(height):
            if matrix[column][row] == 0:
                count += 1
        hcolumn[column] = count

    for row in range(height):
        count = 0
        for column in range(width):
            if matrix[column][row] == 0:
                count += 1
        hrow[row] = count

    return hcolumn, hrow


def optXgrid(hcolumn, width):
    cutX = [0] * 6
    cutX[0] = 0
    cutX[1] = 370
    cutX[2] = 420
    cutX[3] = 480
    cutX[4] = 540
    cutX[5] = width - 1
    optimizationOffset = 20

    for cut in range(1, 5):
        for offset in range(optimizationOffset + 1):
            if hcolumn[cutX[cut] + offset] == 0:
                cutX[cut] += offset
                break
            if hcolumn[cutX[cut] - offset] == 0:
                cutX[cut] -= offset
                break
    return cutX


def optYgrid(hrow, height):
    lookForEmpty = True
    lineCount = 0
    cutY = [0] * 100

    for i in range(height):

        if lookForEmpty and hrow[i] == 0:
            lookForEmpty = False
            cutY[lineCount] = i
            lineCount += 1
        elif not lookForEmpty and hrow[i] != 0:
            lookForEmpty = True

    return cutY[:lineCount]  # nur die Wichtigen Zeilen...


def getSquares(matrix, optimalXCuts, optimalYCuts):
    square = [0] * ((len(optimalXCuts) - 1) * (len(optimalYCuts) - 1))
    currentSquare = 0
    for y in range(1, len(optimalYCuts)):
        for x in range(1, len(optimalXCuts)):
            startX = optimalXCuts[x - 1]
            endX = optimalXCuts[x]
            startY = optimalYCuts[y - 1]
            endY = optimalYCuts[y]
            count = 0
            for m in range(startX, endX):
                for n in range(startY, endY):
                    value = matrix[m][n]
                    if value == 0:
                        count += 1
            square[currentSquare] = count
            currentSquare += 1
    return square


def classify(squares, min):
    squareClass = ["Leer"] * len(squares)

    # Klassifizierung der Einträge
    for i in range(0,len(squares),5):
        if squares[i] > min:
            squareClass[i] = "Name"
        if squares[i+1] > min:
            squareClass[i+1] = "Seillänge"
        squareClass[i+2] = "Schwierigkeit"
        squareClass[i+3] = "Länge"
        squareClass[i+4] = "Beschreibung"

    return squares, squareClass






def handleDescription(image, optXCuts, optYCuts, tempBeschreibungen, newFileName):
    # Berechne die Gesamtbreite und die maximale Höhe der Bilder
    total_width = 0
    max_height = 0
    images = []

    for index in tempBeschreibungen:
        cropped_image = getImageFromIndex(image, optXCuts, optYCuts, index)
        images.append(cropped_image)
        total_width += cropped_image.width
        max_height = max(max_height, cropped_image.height)

    # Erstelle ein neues Bild mit weißem Hintergrund (RGB, weiß)
    new_image = Image.new('RGB', (total_width, max_height), (255, 255, 255))

    # Füge jedes Bild zentriert auf die entsprechende Position ein
    current_width = 0
    for img in images:
        # Berechne die y-Position, um das Bild zu zentrieren
        y_offset = (max_height - img.height) // 2
        new_image.paste(img, (current_width, y_offset))
        current_width += img.width

    # Speichere das resultierende Bild
    new_image.save(f"generatedImages/{newFileName}")
def getImageFromIndex(image, optXCuts, optYCuts, index):
    sqaures = len(optXCuts) - 1
    x_index = index % sqaures
    y_index = index // sqaures

    # Bestimme die Koordinaten des Rechtecks
    x1 = optXCuts[x_index]
    x2 = optXCuts[x_index + 1]
    y1 = optYCuts[y_index]
    y2 = optYCuts[y_index + 1]

    # Schneide das Rechteck aus dem Bild
    cropped_image = image.crop((x1, y1, x2, y2))

    return cropped_image


def saveImage(image, name, x1, x2, y1, y2):
    cropped_image = image.crop((x1, y1, x2, y2))
    cropped_image.save(f'{name}.png')


def stich(squares, squareClass, image, optXCuts, optYCuts):
    code = 0
    route = 0
    beschreibungen = []
    for i in range(0, len(squares), 5):
        if squareClass[i + 1] == "Seillänge":
            continue

        elif squareClass[i] == "Name":
            route += 1
            saveImage(image, f"generatedImages/{route}-Name", optXCuts[0], optXCuts[1], optYCuts[int(i/5)], optYCuts[int(i/5)+1])
            saveImage(image, f"generatedImages/{route}-Schwierigkeit", optXCuts[2], optXCuts[3], optYCuts[int(i/5)], optYCuts[int(i/5) + 1])
            saveImage(image, f"generatedImages/{route}-Länge", optXCuts[3], optXCuts[4], optYCuts[int(i/5)], optYCuts[int(i/5) + 1])
            if code == 1:
                handleDescription(image, optXCuts, optYCuts, beschreibungen, f"{route - 1}-Beschreibung.png")
                beschreibungen.clear()
            code = 1
            beschreibungen.append(i + 4)

        elif code == 1 and squareClass[i] == "Leer":
            beschreibungen.append(i + 4)
    handleDescription(image, optXCuts, optYCuts, beschreibungen, f"{route}-Beschreibung.png")



def extract(file_name, threshold_font_color=126):
    image = Image.open(file_name).convert("RGB")
    width, height = image.size
    matrix = filterImage(image, width, height, threshold_font_color)
    hcolumn, hrow = histogram(matrix, width, height)
    optimalXCuts = optXgrid(hcolumn, width)
    optimalYCuts = optYgrid(hrow, height)
    squares = getSquares(matrix, optimalXCuts, optimalYCuts)
    squares, squareClass = classify(squares, 500)
    stich(squares,squareClass, image, optimalXCuts, optimalYCuts)


import pytesseract


def ocr_image(image_path, diff):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    # Bild öffnen
    image = Image.open(image_path)

    # Angepasste OCR-Konfiguration:
    custom_config = r'--oem 3 --psm 7'  # No whitelist to allow for more flexibility

    # OCR auf dem Bild ausführen
    text = pytesseract.image_to_string(image, config=custom_config, lang='deu')
    if diff:
        text = text.replace("S", "5").replace("s", "5")
        text = text.replace("ö", "6")
    return text

def insert_route(sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung):
    try:
        connection = pymysql.connect(
            host='localhost',
            database='climbingroutes_db',
            user='root',
            password='maRJN6D12bWB'
        )

        if connection:
            cursor = connection.cursor()

            query = """INSERT INTO Routen (sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung)
            VALUES (%s, %s, %s, %s, %s)"""
            values = (sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung)

            cursor.execute(query, values)

            connection.commit()

            print(f"Erfolgreich eingefügt: name: {routen_name} | schwierigkeit: {schwierigkeit} | länge: {routenlaenge} | beschreibung: {routen_beschreibung}")


    except pymysql.MySQLError as e:
        print(f"Fehler beim einfügen: name: {routen_name} | schwierigkeit: {schwierigkeit} | länge: {routenlaenge} | beschreibung: {routen_beschreibung}")


    finally:
        if connection:
            cursor.close()
            connection.close()

def clearDirectory(directoy):
    shutil.rmtree(directoy)
    os.makedirs(directoy)

def extract_number(filename):
    return int(''.join(filter(str.isdigit, filename)))

def processImages(path_to_pages, path_to_generated_Images):
    reerrte = 0
    for filename in os.listdir(path_to_pages):
        if filename.endswith('.png'):
            sektor_id = (int(filename[:3]))
            clearDirectory(path_to_generated_Images)

            file_path = os.path.join(path_to_pages, filename)
            extract(file_path)

            recognized_texts = {}
            # Sortiere die Dateien anhand der extrahierten Zahl
            sorted_filenames = sorted(os.listdir(path_to_generated_Images), key=extract_number)
            for filename in sorted_filenames:
                if filename.lower().endswith(".png"):
                    file_path = os.path.join(path_to_generated_Images, filename)
                    text = ocr_image(file_path, "Schwierigkeit" in filename)

                    if text:
                        recognized_texts[filename] = text
            beschreibung = name = schwierigkeit = ""
            laenge = 0
            for i, (filename, text) in enumerate(recognized_texts.items()):
                if "Schwierigkeit" in filename:
                    schwierigkeit = text
                if "Beschreibung" in filename:
                    beschreibung = text
                if "Länge" in filename:
                    laenge = re.sub(r'\D', '', text)
                if "Name" in filename:
                    name = text[2:]

                if name and laenge != 0 and schwierigkeit and beschreibung:
                    print(f"sektorID: {sektor_id}, name: {name}, schwierigkeit:{schwierigkeit}, länge: {laenge}, beschreibung: {beschreibung}")
                    reerrte+=1
                    print(f"Route: {reerrte}");
                    #insert_route(sektor_id, name, schwierigkeit, laenge, beschreibung)
                    beschreibung = name = schwierigkeit = ""
                    laenge = 0

processImages("C:/Users/fire_/Documents/Schule/SeminarIF/Custom-OCR/images", "C:/Users/fire_/Documents/Schule/SeminarIF/Custom-OCR/generatedImages")





